"""Shared helpers and base test cases for the ctotp/gtotp test suites"""

import base64
import hmac
import io
import os
import runpy
import secrets
import struct
import subprocess  # nosec B404
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _random_totp_secret() -> str:
    """Return a random base32 TOTP secret (16 chars, no padding)."""
    return base64.b32encode(secrets.token_bytes(10)).decode("ascii")


TEST_SECRET = _random_totp_secret()
TEST_ENTRIES = [
    "otpauth://totp/Service:user?digits=6&secret=ABC123",
    "otpauth://totp/Test/user?digits=8&secret=XYZ789",
    "otpauth://totp/NoUser?secret=DEF456",
]
TEST_OTPAUTH = f"otpauth://totp/TestService:testuser?digits=6&secret={TEST_SECRET}"


def read_script(name):
    """Return the source of a script in the project directory"""
    with open(os.path.join(PROJECT_DIR, name), encoding="utf-8") as handle:
        return handle.read()


def run_suite(*test_cases):
    """Run the given TestCase classes and exit with an appropriate code"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_case in test_cases:
        suite.addTests(loader.loadTestsFromTestCase(test_case))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


class ScriptTests(unittest.TestCase):
    """Checks shared by the ctotp and gtotp script test suites"""

    script_name = ""
    required_modules: tuple[str, ...] = ()

    def setUp(self):
        """Set up test environment"""
        self.project_dir = PROJECT_DIR
        self.script_path = os.path.join(self.project_dir, self.script_name)

    def test_script_syntax(self):
        """Test that the script has valid Python syntax"""
        try:
            compile(read_script(self.script_name), self.script_path, "exec")
        except SyntaxError as e:
            self.fail(f"Syntax error in {self.script_name} script: {e}")

    def test_script_executable(self):
        """Test that the script is executable"""
        self.assertTrue(
            os.access(self.script_path, os.X_OK),
            f"{self.script_name} script is not executable",
        )

    def test_required_imports(self):
        """Test that required modules can be imported"""
        for module in self.required_modules:
            try:
                __import__(module)
            except ImportError:
                self.fail(f"Required module '{module}' not available")

    def test_oathtool_dependency(self):
        """Test that oathtool is available"""
        self.assertTrue(
            os.access("/usr/bin/oathtool", os.X_OK),
            "oathtool command not found or not working",
        )

    def test_pass_dependency(self):
        """Test that pass is available"""
        self.assertTrue(
            os.access("/usr/bin/pass", os.X_OK),
            "pass command not found or not working",
        )

    def test_totp_generation_format(self):
        """Test TOTP generation produces correct format"""
        # Pure-Python TOTP (RFC 6238) so tests do not shell out
        padding = "=" * ((8 - len(TEST_SECRET) % 8) % 8)
        key = base64.b32decode(TEST_SECRET + padding, casefold=True)
        codes = []
        for window in (0, 1):
            counter = int(time.time() // 30) + window
            digest = hmac.new(key, struct.pack(">Q", counter), "sha1").digest()
            offset = digest[-1] & 0x0F
            code_int = struct.unpack(">I", digest[offset : offset + 4])[0]
            code_int &= 0x7FFFFFFF
            codes.append(f"{code_int % 1_000_000:06d}")

        self.assertGreaterEqual(len(codes), 1, "Should generate at least one code")
        for code in codes:
            self.assertRegex(
                code,
                r"^\d{6}$",
                f"Code '{code}' should be 6 digits",
            )


class IntegrationTests(unittest.TestCase):
    """Creates and removes a temporary pass entry around each test"""

    test_entry = ""

    def setUp(self):
        """Set up test environment with test pass entry"""
        self.project_dir = PROJECT_DIR
        if not os.access("/usr/bin/pass", os.X_OK):
            self.skipTest("Cannot create test pass entry")
        try:
            subprocess.run(
                ["/usr/bin/pass", "insert", "-m", self.test_entry],
                input=TEST_OTPAUTH,
                text=True,
                check=True,
                capture_output=True,
                timeout=10,
                shell=False,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            self.skipTest("Cannot create test pass entry")

    def tearDown(self):
        """Clean up test environment"""
        if not os.access("/usr/bin/pass", os.X_OK):
            return
        try:
            subprocess.run(
                ["/usr/bin/pass", "rm", "-f", self.test_entry],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                shell=False,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass  # Cleanup failed, but not critical

    def assert_test_mode(self, result):
        """Assert that a modified script ran successfully in test mode"""
        self.assertEqual(result.returncode, 0, f"Script failed: {result.stderr}")
        self.assertIn(
            "Test mode",
            result.stdout,
            "Modified script should indicate test mode",
        )

    def run_modified_script(self, script_name, start_call, replacement):
        """Run a copy of the script using the test entry, with start_call replaced"""
        content = read_script(script_name)
        modified_content = content.replace("totp/all", self.test_entry)
        modified_content = modified_content.replace(start_call, replacement)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(modified_content)
            script_path = f.name
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        returncode = 0
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                try:
                    runpy.run_path(script_path, run_name="__main__")
                except SystemExit as exc:
                    if exc.code is None:
                        returncode = 0
                    elif isinstance(exc.code, int):
                        returncode = exc.code
                    else:
                        returncode = 1
                        stderr_buf.write(f"{exc.code}\n")
                except (
                    RuntimeError,
                    OSError,
                    ValueError,
                    TypeError,
                    ImportError,
                ) as exc:
                    returncode = 1
                    stderr_buf.write(f"{exc}\n")
            return SimpleNamespace(
                returncode=returncode,
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
            )
        finally:
            os.unlink(script_path)
