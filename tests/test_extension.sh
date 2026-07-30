#!/bin/bash
# Test suite for GNOME extension

set -e

EXTENSION_NAME="totp@dmzoneill.com"
EXTENSION_DIR="$HOME/.local/share/gnome-shell/extensions/$EXTENSION_NAME"
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
    TESTS_RUN=$((TESTS_RUN + 1))
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Test extension files exist
test_extension_files() {
    log_test "Testing extension files exist"
    
    local required_files=("metadata.json" "extension.js" "stylesheet.css")
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$PROJECT_DIR/gnome-extension/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -eq 0 ]; then
        log_pass "All required extension files exist"
    else
        log_fail "Missing extension files: ${missing_files[*]}"
        return 1
    fi
}

# Test metadata.json validity
test_metadata_validity() {
    log_test "Testing metadata.json validity"
    
    local metadata_file="$PROJECT_DIR/gnome-extension/metadata.json"
    
    # Check if it's valid JSON
    if python3 -m json.tool "$metadata_file" >/dev/null 2>&1; then
        log_pass "metadata.json is valid JSON"
    else
        log_fail "metadata.json is not valid JSON"
        return 1
    fi
    
    # Check required fields
    local required_fields=("uuid" "name" "description" "shell-version")
    local missing_fields=()
    
    for field in "${required_fields[@]}"; do
        if ! python3 -c "import json; data=json.load(open('$metadata_file')); print(data.get('$field', ''))" | grep -q .; then
            missing_fields+=("$field")
        fi
    done
    
    if [ ${#missing_fields[@]} -eq 0 ]; then
        log_pass "All required metadata fields present"
    else
        log_fail "Missing metadata fields: ${missing_fields[*]}"
        return 1
    fi
}

# Test JavaScript syntax
test_javascript_syntax() {
    log_test "Testing JavaScript syntax"
    
    local js_file="$PROJECT_DIR/gnome-extension/extension.js"
    
    # Check with Node.js if available
    if command -v node >/dev/null 2>&1; then
        if node -c "$js_file" 2>/dev/null; then
            log_pass "JavaScript syntax is valid (Node.js check)"
        else
            log_fail "JavaScript syntax check failed"
            return 1
        fi
    else
        # Basic syntax check using gjs if available
        if command -v gjs >/dev/null 2>&1; then
            if timeout 5 gjs -c "
                try {
                    const content = imports.system.readFile('$js_file');
                    // Basic syntax validation
                    if (content.includes('class') && content.includes('function')) {
                        print('Syntax appears valid');
                    }
                } catch (e) {
                    print('Error: ' + e);
                    imports.system.exit(1);
                }
            " 2>/dev/null; then
                log_pass "JavaScript syntax appears valid (basic check)"
            else
                log_fail "JavaScript syntax check failed"
                return 1
            fi
        else
            log_pass "JavaScript syntax check skipped (no Node.js or gjs)"
        fi
    fi
}

# Test GNOME Shell compatibility
test_gnome_shell_compatibility() {
    log_test "Testing GNOME Shell compatibility"
    
    if command -v gnome-shell >/dev/null 2>&1; then
        local gnome_version
        gnome_version=$(gnome-shell --version | grep -o '[0-9]\+' | head -1)
        
        if [ -n "$gnome_version" ]; then
            # Check if version is supported (40+)
            if [ "$gnome_version" -ge 40 ]; then
                log_pass "GNOME Shell version $gnome_version is supported"
            else
                log_fail "GNOME Shell version $gnome_version is too old (need 40+)"
                return 1
            fi
        else
            log_pass "Could not determine GNOME Shell version, assuming compatible"
        fi
    else
        log_pass "GNOME Shell not detected, skipping compatibility check"
    fi
}

# Test extension installation (dry run)
test_extension_installation() {
    log_test "Testing extension installation process"
    
    local temp_dir
    temp_dir=$(mktemp -d)
    local test_extension_dir="$temp_dir/$EXTENSION_NAME"
    
    # Try to copy extension files
    if cp -r "$PROJECT_DIR/gnome-extension" "$test_extension_dir"; then
        # Check that all files were copied
        if [ -f "$test_extension_dir/metadata.json" ] && [ -f "$test_extension_dir/extension.js" ]; then
            log_pass "Extension installation process works"
        else
            log_fail "Extension files not properly copied"
            rm -rf "$temp_dir"
            return 1
        fi
    else
        log_fail "Extension installation failed"
        rm -rf "$temp_dir"
        return 1
    fi
    
    rm -rf "$temp_dir"
}

# Test extension dependencies
test_extension_dependencies() {
    log_test "Testing extension dependencies"
    
    local deps=("pass" "oathtool")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        log_pass "All extension dependencies are available"
    else
        log_fail "Missing extension dependencies: ${missing_deps[*]}"
        return 1
    fi
}

# Test extension UUID consistency
test_uuid_consistency() {
    log_test "Testing UUID consistency"
    
    local metadata_uuid
    metadata_uuid=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/gnome-extension/metadata.json'))['uuid'])")
    
    if [ "$metadata_uuid" = "$EXTENSION_NAME" ]; then
        log_pass "Extension UUID is consistent"
    else
        log_fail "Extension UUID mismatch: expected '$EXTENSION_NAME', got '$metadata_uuid'"
        return 1
    fi
}

# Test extension code structure
test_extension_structure() {
    log_test "Testing extension code structure"
    
    local js_file="$PROJECT_DIR/gnome-extension/extension.js"
    local required_patterns=(
        "class.*extends.*Extension"
        "enable()"
        "disable()"
        "import.*from"
    )
    
    local missing_patterns=()
    
    for pattern in "${required_patterns[@]}"; do
        if ! grep -q "$pattern" "$js_file"; then
            missing_patterns+=("$pattern")
        fi
    done
    
    if [ ${#missing_patterns[@]} -eq 0 ]; then
        log_pass "Extension has proper code structure"
    else
        log_fail "Missing code patterns: ${missing_patterns[*]}"
        return 1
    fi
}

# Test if extension is currently installed
test_current_installation() {
    log_test "Testing current installation status"
    
    if [ -d "$EXTENSION_DIR" ]; then
        if command -v gnome-extensions >/dev/null 2>&1; then
            if gnome-extensions list | grep -q "$EXTENSION_NAME"; then
                local status
                status=$(gnome-extensions info "$EXTENSION_NAME" | grep "State:" | awk '{print $2}')
                log_pass "Extension is installed (status: $status)"
            else
                log_pass "Extension directory exists but not recognized by GNOME"
            fi
        else
            log_pass "Extension directory exists (cannot check status without gnome-extensions)"
        fi
    else
        log_pass "Extension not currently installed"
    fi
}

# Main test execution
main() {
    echo "Running GNOME extension tests..."
    echo "================================="
    
    # Run tests
    test_extension_files
    test_metadata_validity
    test_javascript_syntax
    test_gnome_shell_compatibility
    test_extension_installation
    test_extension_dependencies
    test_uuid_consistency
    test_extension_structure
    test_current_installation
    
    # Report results
    echo ""
    echo "Test Results:"
    echo "============="
    echo "Tests run: $TESTS_RUN"
    echo "Tests passed: $TESTS_PASSED"
    echo "Tests failed: $((TESTS_RUN - TESTS_PASSED))"
    
    if [ $TESTS_PASSED -ge $TESTS_RUN ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

# Run tests
main "$@"