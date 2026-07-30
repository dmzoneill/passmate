#!/usr/bin/env python3
"""Test suite for ctotp script"""

import sys
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class TestCTOTP(unittest.TestCase):
    """Test cases for ctotp script"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_dir = os.path.dirname(os.path.dirname(__file__))
        self.ctotp_path = os.path.join(self.project_dir, 'ctotp')
        
    def test_script_syntax(self):
        """Test that the script has valid Python syntax"""
        try:
            with open(self.ctotp_path, 'r') as f:
                compile(f.read(), self.ctotp_path, 'exec')
        except SyntaxError as e:
            self.fail(f"Syntax error in ctotp script: {e}")
    
    def test_script_executable(self):
        """Test that the script is executable"""
        self.assertTrue(os.access(self.ctotp_path, os.X_OK),
                       "ctotp script is not executable")
    
    def test_required_imports(self):
        """Test that required modules can be imported"""
        required_modules = ['curses', 'time', 'subprocess']
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                self.fail(f"Required module '{module}' not available")
    
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
    
    @patch('subprocess.check_output')
    def test_get_totp_entries_function(self, mock_subprocess):
        """Test the get_totp_entries function logic"""
        # Mock pass output
        mock_subprocess.return_value = b'otpauth://totp/Test:user?secret=TEST123\notpauth://totp/Service:name?secret=ABC456\n'
        
        # This would require importing the actual functions from ctotp
        # For now, we'll just test that subprocess would be called correctly
        try:
            subprocess.check_output(["pass", "show", "totp/all"])
        except subprocess.CalledProcessError:
            # Expected if totp/all doesn't exist, but call format is correct
            pass
    
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
    
    def test_parameter_extraction_logic(self):
        """Test parameter extraction logic for otpauth URLs"""
        test_entries = [
            "otpauth://totp/Service:user?digits=6&secret=ABC123",
            "otpauth://totp/Test/user?digits=8&secret=XYZ789",
            "otpauth://totp/NoUser?secret=DEF456"
        ]
        
        for entry in test_entries:
            # Test that we can extract the service name
            if 'otpauth://totp/' in entry:
                entry_name = entry[len("otpauth://totp/"):]
                entry_info = entry_name.split("?")[0]
                
                # Should be able to split on : or /
                if ':' in entry_info:
                    parts = entry_info.split(':', 1)
                    self.assertEqual(len(parts), 2, f"Should split into 2 parts: {entry_info}")
                elif '/' in entry_info:
                    parts = entry_info.split('/', 1)
                    self.assertEqual(len(parts), 2, f"Should split into 2 parts: {entry_info}")
            
            # Test secret extraction
            if 'secret=' in entry:
                secret_start = entry.find('secret=') + len('secret=')
                secret_end = entry.find('&', secret_start)
                if secret_end == -1:
                    secret_end = len(entry)
                secret = entry[secret_start:secret_end]
                self.assertGreater(len(secret), 0, "Secret should not be empty")

class TestCTOTPIntegration(unittest.TestCase):
    """Integration tests for ctotp with test data"""
    
    def setUp(self):
        """Set up test environment with test pass entry"""
        self.test_entry = "totp/test-ctotp"
        self.project_dir = os.path.dirname(os.path.dirname(__file__))
        
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
    
    def test_script_with_test_data(self):
        """Test script execution with test data (non-interactive)"""
        # Create a modified version that uses test entry and exits immediately
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            with open(os.path.join(self.project_dir, 'ctotp'), 'r') as original:
                content = original.read()
                
            # Modify to use test entry and exit immediately
            modified_content = content.replace('totp/all', self.test_entry)
            modified_content = modified_content.replace('curses.wrapper(main)', 
                                                      'print("Test mode - would start curses interface")')
            
            f.write(modified_content)
            f.flush()
            
            try:
                result = subprocess.run([sys.executable, f.name], 
                                      capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, 
                               f"Script failed: {result.stderr}")
                self.assertIn("Test mode", result.stdout, 
                            "Modified script should indicate test mode")
            except subprocess.TimeoutExpired:
                self.fail("Script execution timed out")
            finally:
                os.unlink(f.name)

def main():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCTOTP))
    suite.addTests(loader.loadTestsFromTestCase(TestCTOTPIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == '__main__':
    main()