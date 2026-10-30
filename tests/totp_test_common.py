"""Shared helpers and base test cases for the ctotp/gtotp test suites"""

import os
import subprocess  # nosec B404
import sys
import tempfile
import unittest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_SECRET = "JBSWY3DPEHPK3PXP"  # Standard test secret  # nosec B105
TEST_ENTRIES = [
    "otpauth://totp/Service:user?digits=6&secret=ABC123",
    "otpauth://totp/Test/user?digits=8&secret=XYZ789",
    "otpauth://totp/NoUser?secret=DEF456",
]
TEST_OTPAUTH = f"otpauth://totp/TestService:testuser?digits=6&secret={TEST_SECRET}"


def run_command(args, timeout, **kwargs):
    """Run a command capturing text output, without raising on failure"""
    return subprocess.run(  # nosec B603
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        **kwargs,
    )


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
        try:
            result = run_command(["oathtool", "--version"], timeout=5)
            self.assertEqual(result.returncode, 0, "oathtool not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.fail("oathtool command not found or not working")

    def test_pass_dependency(self):
        """Test that pass is available"""
        try:
            result = run_command(["pass", "--version"], timeout=5)
            self.assertEqual(result.returncode, 0, "pass not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.fail("pass command not found or not working")

    def test_totp_generation_format(self):
        """Test TOTP generation produces correct format"""
        args = [
            "oathtool",
            "-s",
            "30s",
            "-d",
            "6",
            "-b",
            "--totp",
            TEST_SECRET,
            "-w",
            "1",
        ]
        try:
            result = run_command(args, timeout=5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("oathtool not available for testing")

        if result.returncode == 0:
            codes = result.stdout.strip().split("\n")
            self.assertGreaterEqual(
                len(codes),
                1,
                "Should generate at least one code",
            )

            for code in codes:
                if code.strip():  # Skip empty lines
                    self.assertRegex(
                        code.strip(),
                        r"^\d{6}$",
                        f"Code '{code}' should be 6 digits",
                    )


class IntegrationTests(unittest.TestCase):
    """Creates and removes a temporary pass entry around each test"""

    test_entry = ""

    def setUp(self):
        """Set up test environment with test pass entry"""
        self.project_dir = PROJECT_DIR
        try:
            subprocess.run(  # nosec B603 B607
                ["pass", "insert", "-m", self.test_entry],
                input=TEST_OTPAUTH,
                text=True,
                check=True,
                capture_output=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            self.skipTest("Cannot create test pass entry")

    def tearDown(self):
        """Clean up test environment"""
        try:
            run_command(["pass", "rm", "-f", self.test_entry], timeout=5)
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
        try:
            return run_command([sys.executable, f.name], timeout=10)  # nosemgrep
        finally:
            os.unlink(f.name)
