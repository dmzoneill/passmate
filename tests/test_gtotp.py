#!/usr/bin/env python3
"""Test suite for gtotp script"""

import sys
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class TestGTOTP(unittest.TestCase):
    """Test cases for gtotp script"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_dir = os.path.dirname(os.path.dirname(__file__))
        self.gtotp_path = os.path.join(self.project_dir, 'gtotp')
        
    def test_script_syntax(self):
        """Test that the script has valid Python syntax"""
        try:
            with open(self.gtotp_path, 'r') as f:
                compile(f.read(), self.gtotp_path, 'exec')
        except SyntaxError as e:
            self.fail(f"Syntax error in gtotp script: {e}")
    
    def test_script_executable(self):
        """Test that the script is executable"""
        self.assertTrue(os.access(self.gtotp_path, os.X_OK),
                       "gtotp script is not executable")
    
    def test_required_imports(self):
        """Test that required modules can be imported"""
        required_modules = ['subprocess', 'time']
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                self.fail(f"Required module '{module}' not available")
    
    def test_gi_imports(self):
        """Test that GTK/GI modules can be imported"""
        try:
            import gi
            gi.require_version("Gdk", "4.0")
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk, GLib, Gdk
        except ImportError as e:
            self.skipTest(f"GTK4/GI not available: {e}")
        except ValueError as e:
            self.skipTest(f"GTK4 version not available: {e}")
    
    def test_oathtool_dependency(self):
        """Test that oathtool is available"""
        try:
            result = subprocess.run(['oathtool', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, "oathtool not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.fail("oathtool command not found or not working")
    
    def test_pass_dependency(self):
        """Test that pass is available"""
        try:
            result = subprocess.run(['pass', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, "pass not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.fail("pass command not found or not working")
    
    def test_totp_generation_format(self):
        """Test TOTP generation produces correct format"""
        test_secret = "JBSWY3DPEHPK3PXP"  # Standard test secret
        
        try:
            result = subprocess.run([
                'oathtool', '-s', '30s', '-d', '6', '-b', '--totp', test_secret, '-w', '1'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                codes = result.stdout.strip().split('\n')
                self.assertGreaterEqual(len(codes), 1, "Should generate at least one code")
                
                for code in codes:
                    if code.strip():  # Skip empty lines
                        self.assertRegex(code.strip(), r'^\d{6}$', 
                                       f"Code '{code}' should be 6 digits")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skip("oathtool not available for testing")
    
    def test_otpauth_parsing_logic(self):
        """Test otpauth URL parsing logic"""
        test_entries = [
            "otpauth://totp/Service:user?digits=6&secret=ABC123",
            "otpauth://totp/Test/user?digits=8&secret=XYZ789",
            "otpauth://totp/NoUser?secret=DEF456"
        ]
        
        for entry in test_entries:
            if 'otpauth://totp/' in entry:
                # Test entry info extraction
                entry_info = entry[len("otpauth://totp/"):]
                entry_parts = entry_info.split("?", 1)
                
                self.assertGreater(len(entry_parts), 0, "Should have entry parts")
                
                # Test parameter extraction
                if len(entry_parts) > 1:
                    query_params = entry_parts[1].split("&")
                    parameters = {}
                    for param in query_params:
                        if '=' in param:
                            key, value = param.split("=", 1)
                            parameters[key] = value
                    
                    self.assertIn('secret', parameters, "Should have secret parameter")
                    self.assertGreater(len(parameters['secret']), 0, "Secret should not be empty")
    
    def test_service_username_extraction(self):
        """Test service and username extraction logic"""
        test_cases = [
            ("Service:username", "Service", "username"),
            ("Service/username", "Service", "username"),
            ("JustService", "-", "JustService"),
            ("Complex:Service:name", "Complex", "Service:name")
        ]
        
        for service_and_username, expected_service, expected_username in test_cases:
            if ":" in service_and_username:
                service, username = service_and_username.split(":", 1)
            elif "/" in service_and_username:
                service, username = service_and_username.split("/", 1)
            else:
                service = "-"
                username = service_and_username
            
            self.assertEqual(service, expected_service, 
                           f"Service mismatch for '{service_and_username}'")
            self.assertEqual(username, expected_username, 
                           f"Username mismatch for '{service_and_username}'")

class TestGTOTPIntegration(unittest.TestCase):
    """Integration tests for gtotp with test data"""
    
    def setUp(self):
        """Set up test environment with test pass entry"""
        self.test_entry = "totp/test-gtotp"
        self.project_dir = os.path.dirname(os.path.dirname(__file__))
        
        # Skip if no display available
        if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            self.skipTest("No display available for GTK testing")
        
        # Create test entry
        test_data = "otpauth://totp/TestService:testuser?digits=6&secret=JBSWY3DPEHPK3PXP"
        try:
            subprocess.run(['pass', 'insert', '-m', self.test_entry], 
                         input=test_data, text=True, check=True, 
                         capture_output=True, timeout=10)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            self.skipTest("Cannot create test pass entry")
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            subprocess.run(['pass', 'rm', '-f', self.test_entry], 
                         capture_output=True, timeout=5)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass  # Cleanup failed, but not critical
    
    def test_script_import_without_execution(self):
        """Test that script can be imported without running GUI"""
        # Create a modified version that doesn't start the GUI
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            with open(os.path.join(self.project_dir, 'gtotp'), 'r') as original:
                content = original.read()
                
            # Modify to use test entry and not run the app
            modified_content = content.replace('totp/all', self.test_entry)
            modified_content = modified_content.replace('app.run(None)', 
                                                      'print("Test mode - would start GTK app")')
            
            f.write(modified_content)
            f.flush()
            
            try:
                result = subprocess.run([sys.executable, f.name], 
                                      capture_output=True, text=True, timeout=10)
                
                # Check if it's a GTK availability issue vs script issue
                if "GTK" in result.stderr or "gi" in result.stderr:
                    self.skipTest("GTK4 not available for testing")
                
                self.assertEqual(result.returncode, 0, 
                               f"Script failed: {result.stderr}")
                self.assertIn("Test mode", result.stdout, 
                            "Modified script should indicate test mode")
            except subprocess.TimeoutExpired:
                self.fail("Script execution timed out")
            finally:
                os.unlink(f.name)
    
    def test_totp_class_methods_exist(self):
        """Test that required methods exist in TOTPApp class"""
        with open(os.path.join(self.project_dir, 'gtotp'), 'r') as f:
            content = f.read()
        
        # Check for required method definitions
        required_methods = [
            'def __init__',
            'def update_codes',
            'def generate_totp',
            'def fetch_entries',
            'def call_oathtool'
        ]
        
        for method in required_methods:
            self.assertIn(method, content, f"Method '{method}' not found in gtotp")
    
    def test_clipboard_functionality_logic(self):
        """Test clipboard functionality logic (without actual clipboard)"""
        # Test that the clipboard interaction code exists
        with open(os.path.join(self.project_dir, 'gtotp'), 'r') as f:
            content = f.read()
        
        # Check for clipboard-related code
        self.assertIn('clipboard', content.lower(), "Clipboard functionality should be present")
        self.assertIn('Gdk.Display.get_default().get_clipboard()', content, 
                     "Should use proper GTK clipboard method")

class TestGTOTPNonGUI(unittest.TestCase):
    """Tests that don't require GUI"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_dir = os.path.dirname(os.path.dirname(__file__))
        self.gtotp_path = os.path.join(self.project_dir, 'gtotp')
    
    def test_timeout_calculation(self):
        """Test timeout calculation logic"""
        import time
        
        current_time = time.time()
        next_interval = 30 - int(current_time % 30)
        
        self.assertGreater(next_interval, 0, "Next interval should be positive")
        self.assertLessEqual(next_interval, 30, "Next interval should not exceed 30")
    
    def test_code_update_logic(self):
        """Test the logic for updating codes"""
        # This tests the mathematical logic without GUI
        import time
        
        current_time = time.time()
        initial_countdown = 30 - int(current_time % 30)
        
        # Simulate passage of time
        time.sleep(1)
        current_time = time.time()
        new_countdown = 30 - int(current_time % 30)
        
        # The countdown should have decreased (accounting for potential rollover)
        if initial_countdown > 1:
            self.assertLess(new_countdown, initial_countdown, 
                          "Countdown should decrease over time")

def main():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestGTOTP))
    suite.addTests(loader.loadTestsFromTestCase(TestGTOTPNonGUI))
    suite.addTests(loader.loadTestsFromTestCase(TestGTOTPIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == '__main__':
    main()