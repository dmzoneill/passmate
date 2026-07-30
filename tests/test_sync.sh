#!/bin/bash
# Test suite for sync script

set -e

TEST_PASS_ENTRY="totp/test-sync"
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
    
    # Create initial test TOTP entry
    echo "otpauth://totp/ExistingService:user1?digits=6&secret=JBSWY3DPEHPK3PXP" | pass insert -m "$TEST_PASS_ENTRY"
    
    # Create mock authy export
    mkdir -p /tmp/go/bin
    cat > /tmp/go/bin/authy-export << 'EOF'
#!/bin/bash
# Mock authy export for testing
echo "otpauth://totp/NewService:user2?digits=6&secret=GEZDGNBVGY3TQOJQ"
echo "otpauth://totp/ExistingService:user1?digits=6&secret=JBSWY3DPEHPK3PXP"
EOF
    chmod +x /tmp/go/bin/authy-export
    
    log_pass "Test data setup complete"
}

# Cleanup test environment
cleanup_test_data() {
    log_test "Cleaning up test data"
    pass rm -f "$TEST_PASS_ENTRY" >/dev/null 2>&1 || true
    pass rm -rf "totp/test-sync-*" >/dev/null 2>&1 || true
    rm -rf /tmp/go >/dev/null 2>&1 || true
    log_pass "Test data cleanup complete"
}

# Test script syntax
test_syntax() {
    log_test "Testing sync script syntax"
    
    if bash -n "$PROJECT_DIR/sync"; then
        log_pass "Script syntax is valid"
    else
        log_fail "Script syntax check failed"
        return 1
    fi
}

# Test script dependencies
test_dependencies() {
    log_test "Testing script dependencies"
    
    local deps=("pass" "grep" "date")
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

# Test backup functionality
test_backup_creation() {
    log_test "Testing backup creation"
    
    # Create test script that uses test entry
    local temp_script=$(mktemp)
    sed -e "s|totp/all|$TEST_PASS_ENTRY|g" \
        -e "s|go/bin/authy-export|/tmp/go/bin/authy-export|g" \
        "$PROJECT_DIR/sync" > "$temp_script"
    chmod +x "$temp_script"
    
    # Run script
    if "$temp_script" >/dev/null 2>&1; then
        # Check if backup was created
        local backup_count
        backup_count=$(pass ls totp/ | grep -c "test-sync-" || echo "0")
        
        if [ "$backup_count" -gt 0 ]; then
            log_pass "Backup creation works"
        else
            log_fail "No backup was created"
            rm -f "$temp_script"
            return 1
        fi
    else
        log_fail "Script execution failed"
        rm -f "$temp_script"
        return 1
    fi
    
    rm -f "$temp_script"
}

# Test duplicate prevention
test_duplicate_prevention() {
    log_test "Testing duplicate entry prevention"
    
    local original_content
    original_content=$(pass show "$TEST_PASS_ENTRY")
    
    # Create test script
    local temp_script=$(mktemp)
    sed -e "s|totp/all|$TEST_PASS_ENTRY|g" \
        -e "s|go/bin/authy-export|/tmp/go/bin/authy-export|g" \
        "$PROJECT_DIR/sync" > "$temp_script"
    chmod +x "$temp_script"
    
    # Run script twice
    "$temp_script" >/dev/null 2>&1
    "$temp_script" >/dev/null 2>&1
    
    local final_content
    final_content=$(pass show "$TEST_PASS_ENTRY")
    
    # Count occurrences of the existing secret
    local original_count final_count
    original_count=$(echo "$original_content" | grep -c "JBSWY3DPEHPK3PXP" || echo "0")
    final_count=$(echo "$final_content" | grep -c "JBSWY3DPEHPK3PXP" || echo "0")
    
    if [ "$original_count" -eq "$final_count" ]; then
        log_pass "Duplicate prevention works"
    else
        log_fail "Duplicates were created (original: $original_count, final: $final_count)"
        rm -f "$temp_script"
        return 1
    fi
    
    rm -f "$temp_script"
}

# Test new entry addition
test_new_entry_addition() {
    log_test "Testing new entry addition"
    
    local content_before
    content_before=$(pass show "$TEST_PASS_ENTRY")
    
    # Create test script
    local temp_script=$(mktemp)
    sed -e "s|totp/all|$TEST_PASS_ENTRY|g" \
        -e "s|go/bin/authy-export|/tmp/go/bin/authy-export|g" \
        "$PROJECT_DIR/sync" > "$temp_script"
    chmod +x "$temp_script"
    
    # Run script
    "$temp_script" >/dev/null 2>&1
    
    local content_after
    content_after=$(pass show "$TEST_PASS_ENTRY")
    
    # Check if new entry was added
    if echo "$content_after" | grep -q "NewService:user2"; then
        log_pass "New entries are added correctly"
    else
        log_fail "New entry was not added"
        echo "Content before: $content_before"
        echo "Content after: $content_after"
        rm -f "$temp_script"
        return 1
    fi
    
    rm -f "$temp_script"
}

# Main test execution
main() {
    echo "Running sync script tests..."
    echo "==========================="
    
    # Run tests
    setup_test_data
    test_syntax
    test_dependencies
    test_backup_creation
    test_duplicate_prevention
    test_new_entry_addition
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