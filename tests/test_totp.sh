#!/bin/bash
# Test suite for totp script

set -e

TEST_PASS_ENTRY="totp/test"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0

# Helper functions
log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
    ((TESTS_RUN++))
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Setup test environment
setup_test_data() {
    log_test "Setting up test data"
    
    # Create test TOTP entry if it doesn't exist
    if ! pass show "$TEST_PASS_ENTRY" >/dev/null 2>&1; then
        echo "otpauth://totp/TestService:testuser?digits=6&secret=JBSWY3DPEHPK3PXP" | pass insert -m "$TEST_PASS_ENTRY"
    fi
    
    log_pass "Test data setup complete"
}

# Cleanup test environment
cleanup_test_data() {
    log_test "Cleaning up test data"
    pass rm -f "$TEST_PASS_ENTRY" >/dev/null 2>&1 || true
    log_pass "Test data cleanup complete"
}

# Test script syntax
test_syntax() {
    log_test "Testing totp script syntax"
    
    if bash -n "$PROJECT_DIR/totp"; then
        log_pass "Script syntax is valid"
    else
        log_fail "Script syntax check failed"
        return 1
    fi
}

# Test script dependencies
test_dependencies() {
    log_test "Testing script dependencies"
    
    local deps=("pass" "oathtool" "grep" "printf")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        log_pass "All dependencies are available"
    else
        log_fail "Missing dependencies: ${missing_deps[*]}"
        return 1
    fi
}

# Test script execution with test data
test_execution() {
    log_test "Testing script execution with test data"
    
    # Temporarily modify script to use test entry
    local temp_script=$(mktemp)
    sed "s/totp\/all/$TEST_PASS_ENTRY/g" "$PROJECT_DIR/totp" > "$temp_script"
    chmod +x "$temp_script"
    
    if output=$("$temp_script" 2>&1); then
        if echo "$output" | grep -q "TestService"; then
            log_pass "Script executes and produces expected output"
        else
            log_fail "Script executes but output doesn't contain test service"
            echo "Output: $output"
            rm -f "$temp_script"
            return 1
        fi
    else
        log_fail "Script execution failed"
        echo "Error: $output"
        rm -f "$temp_script"
        return 1
    fi
    
    rm -f "$temp_script"
}

# Test TOTP code generation
test_totp_generation() {
    log_test "Testing TOTP code generation"
    
    # Test with known secret
    local test_secret="JBSWY3DPEHPK3PXP"
    local output
    
    if output=$(oathtool -s 30s -d 6 -b --totp "$test_secret" 2>&1); then
        if [[ $output =~ ^[0-9]{6}$ ]]; then
            log_pass "TOTP generation produces valid 6-digit code"
        else
            log_fail "TOTP generation produces invalid code format: $output"
            return 1
        fi
    else
        log_fail "TOTP generation failed: $output"
        return 1
    fi
}

# Main test execution
main() {
    echo "Running TOTP script tests..."
    echo "=========================="
    
    # Run tests
    setup_test_data
    test_syntax
    test_dependencies
    test_totp_generation
    test_execution
    cleanup_test_data
    
    # Report results
    echo ""
    echo "Test Results:"
    echo "============="
    echo "Tests run: $TESTS_RUN"
    echo "Tests passed: $TESTS_PASSED"
    echo "Tests failed: $((TESTS_RUN - TESTS_PASSED))"
    
    if [ $TESTS_PASSED -eq $TESTS_RUN ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

# Trap to ensure cleanup on exit
trap cleanup_test_data EXIT

# Run tests
main "$@"