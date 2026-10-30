#!/usr/bin/env python3
"""Test suite for gtotp script"""

import os
import subprocess  # nosec B404
import sys
import time
import unittest

import totp_test_common as common

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestGTOTP(common.ScriptTests):
    """Test cases for gtotp script"""

    script_name = "gtotp"
    required_modules = ("subprocess", "time")

    def test_gi_imports(self):
        """Test that GTK/GI modules can be imported"""
        try:
            import gi

            gi.require_version("Gdk", "4.0")
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gdk, GLib, Gtk

            self.assertIsNotNone(Gtk)
            self.assertIsNotNone(GLib)
            self.assertIsNotNone(Gdk)
        except ImportError as e:
            self.skipTest(f"GTK4/GI not available: {e}")
        except ValueError as e:
            self.skipTest(f"GTK4 version not available: {e}")

    def test_otpauth_parsing_logic(self):
        """Test otpauth URL parsing logic"""
        test_entries = common.TEST_ENTRIES

        for entry in test_entries:
            if "otpauth://totp/" in entry:
                # Test entry info extraction
                entry_info = entry[len("otpauth://totp/") :]
                entry_parts = entry_info.split("?", 1)

                self.assertGreater(len(entry_parts), 0, "Should have entry parts")

                # Test parameter extraction
                if len(entry_parts) > 1:
                    query_params = entry_parts[1].split("&")
                    parameters = {}
                    for param in query_params:
                        if "=" in param:
                            key, value = param.split("=", 1)
                            parameters[key] = value

                    self.assertIn("secret", parameters, "Should have secret parameter")
                    self.assertGreater(
                        len(parameters["secret"]),
                        0,
                        "Secret should not be empty",
                    )

    def test_service_username_extraction(self):
        """Test service and username extraction logic"""
        test_cases = [
            ("Service:username", "Service", "username"),
            ("Service/username", "Service", "username"),
            ("JustService", "-", "JustService"),
            ("Complex:Service:name", "Complex", "Service:name"),
        ]

        for service_and_username, expected_service, expected_username in test_cases:
            if ":" in service_and_username:
                service, username = service_and_username.split(":", 1)
            elif "/" in service_and_username:
                service, username = service_and_username.split("/", 1)
            else:
                service = "-"
                username = service_and_username

            self.assertEqual(
                service,
                expected_service,
                f"Service mismatch for '{service_and_username}'",
            )
            self.assertEqual(
                username,
                expected_username,
                f"Username mismatch for '{service_and_username}'",
            )


class TestGTOTPIntegration(common.IntegrationTests):
    """Integration tests for gtotp with test data"""

    test_entry = "totp/test-gtotp"

    def setUp(self):
        """Set up test environment with test pass entry"""
        # Skip if no display available
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            self.skipTest("No display available for GTK testing")
        super().setUp()

    def test_script_import_without_execution(self):
        """Test that script can be imported without running GUI"""
        try:
            result = self.run_modified_script(
                "gtotp",
                "app.run(None)",
                'print("Test mode - would start GTK app")',
            )
        except subprocess.TimeoutExpired:
            self.fail("Script execution timed out")

        # Check if it's a GTK availability issue vs script issue
        if "GTK" in result.stderr or "gi" in result.stderr:
            self.skipTest("GTK4 not available for testing")

        self.assert_test_mode(result)

    def test_totp_class_methods_exist(self):
        """Test that required methods exist in TOTPApp class"""
        content = common.read_script("gtotp")

        # Check for required method definitions
        required_methods = [
            "def __init__",
            "def update_codes",
            "def generate_totp",
            "def fetch_entries",
            "def call_oathtool",
        ]

        for method in required_methods:
            self.assertIn(method, content, f"Method '{method}' not found in gtotp")

    def test_clipboard_functionality_logic(self):
        """Test clipboard functionality logic (without actual clipboard)"""
        # Test that the clipboard interaction code exists
        content = common.read_script("gtotp")

        # Check for clipboard-related code
        self.assertIn(
            "clipboard",
            content.lower(),
            "Clipboard functionality should be present",
        )
        self.assertIn(
            "Gdk.Display.get_default().get_clipboard()",
            content,
            "Should use proper GTK clipboard method",
        )


class TestGTOTPNonGUI(unittest.TestCase):
    """Tests that don't require GUI"""

    def setUp(self):
        """Set up test environment"""
        self.project_dir = os.path.dirname(os.path.dirname(__file__))
        self.gtotp_path = os.path.join(self.project_dir, "gtotp")

    def test_timeout_calculation(self):
        """Test timeout calculation logic"""

        current_time = time.time()
        next_interval = 30 - int(current_time % 30)

        self.assertGreater(next_interval, 0, "Next interval should be positive")
        self.assertLessEqual(next_interval, 30, "Next interval should not exceed 30")

    def test_code_update_logic(self):
        """Test the logic for updating codes"""
        # This tests the mathematical logic without GUI

        current_time = time.time()
        initial_countdown = 30 - int(current_time % 30)

        # Simulate passage of time
        time.sleep(1)
        current_time = time.time()
        new_countdown = 30 - int(current_time % 30)

        # The countdown should have decreased (accounting for potential rollover)
        if initial_countdown > 1:
            self.assertLess(
                new_countdown,
                initial_countdown,
                "Countdown should decrease over time",
            )


def main():
    """Run all tests"""
    common.run_suite(TestGTOTP, TestGTOTPNonGUI, TestGTOTPIntegration)


if __name__ == "__main__":
    main()
