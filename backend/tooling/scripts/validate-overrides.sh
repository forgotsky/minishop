#!/usr/bin/env bash
################################################################################
# Validate Overrides - Override YAML Validation and Linting
#
# This script validates all override YAML files in the overrides directory.
# It checks for:
#   - Valid YAML syntax
#   - Required fields
#   - Valid field types
#   - Valid model names
#   - Valid budget ranges
#
# Usage:
#   ./validate-overrides.sh              # Validate all overrides
#   ./validate-overrides.sh dev          # Validate specific agent override
#   ./validate-overrides.sh --fix        # Auto-fix common issues
#   ./validate-overrides.sh --verbose    # Show detailed output
#
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OVERRIDES_DIR="$PROJECT_ROOT/.automation/overrides"
AGENTS_DIR="$PROJECT_ROOT/.automation/agents"

# Valid values
VALID_MODELS=("sonnet" "opus" "haiku")
MIN_BUDGET=0.01
MAX_BUDGET=100.00

# Counters
ERRORS=0
WARNINGS=0
VALIDATED=0

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  OVERRIDE VALIDATOR${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

error() {
    echo -e "${RED}  [X] ERROR:${NC} $1"
    ((ERRORS++))
}

warning() {
    echo -e "${YELLOW}  WARNING:${NC} $1"
    ((WARNINGS++))
}

success() {
    echo -e "${GREEN}  [OK]${NC} $1"
}

info() {
    [[ "$VERBOSE" == "true" ]] && echo -e "${BLUE}  [i]${NC} $1"
}

################################################################################
# YAML Validation Helpers
################################################################################

# Check if file has valid YAML syntax using basic shell parsing
check_yaml_syntax() {
    local file="$1"

    # Check for common YAML syntax issues
    local line_num=0
    local in_list=false
    local prev_indent=0

    while IFS= read -r line || [[ -n "$line" ]]; do
        ((line_num++))

        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

        # Check for tabs (YAML should use spaces)
        if [[ "$line" == *$'\t'* ]]; then
            error "Line $line_num: Contains tabs (use spaces instead)"
            return 1
        fi

        # Check for trailing spaces
        if [[ "$line" =~ [[:space:]]$ ]]; then
            warning "Line $line_num: Trailing whitespace"
        fi

        # Check for unclosed quotes
        local quote_count=$(echo "$line" | grep -o '"' | wc -l | tr -d ' ')
        if [[ $((quote_count % 2)) -ne 0 ]]; then
            error "Line $line_num: Unclosed double quote"
            return 1
        fi

        local single_quote_count=$(echo "$line" | grep -o "'" | wc -l | tr -d ' ')
        if [[ $((single_quote_count % 2)) -ne 0 ]]; then
            error "Line $line_num: Unclosed single quote"
            return 1
        fi

        # Check for proper colon spacing in key-value pairs
        if [[ "$line" =~ ^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*:[^[:space:]] && ! "$line" =~ ^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*:$ ]]; then
            # Allow for URLs and special cases
            if [[ ! "$line" =~ https?: && ! "$line" =~ \".*:.*\" ]]; then
                warning "Line $line_num: Missing space after colon"
            fi
        fi

    done < "$file"

    return 0
}

# Extract value from YAML key
yaml_get() {
    local file="$1"
    local key="$2"
    grep -E "^${key}:" "$file" 2>/dev/null | sed "s/^${key}:[[:space:]]*//" | sed 's/^["'"'"']//' | sed 's/["'"'"']$//' | head -1
}

# Check if a list exists and has items
yaml_has_list() {
    local file="$1"
    local key="$2"
    grep -q "^${key}:" "$file" 2>/dev/null && \
    awk "/^${key}:/{found=1; next} found && /^[[:space:]]*-/{print; exit} found && /^[a-zA-Z]/{exit}" "$file" 2>/dev/null | grep -q .
}

################################################################################
# Override Validation
################################################################################

validate_override_file() {
    local file="$1"
    local filename=$(basename "$file")
    local agent_name="${filename%.override.yaml}"

    echo ""
    echo -e "${BLUE}Validating:${NC} $filename"

    # Check if corresponding agent exists
    local agent_file="$AGENTS_DIR/${agent_name}.md"
    if [[ ! -f "$agent_file" ]]; then
        warning "No corresponding agent file found: ${agent_name}.md"
        warning "This override may not be applied to any agent"
    else
        info "Agent file found: ${agent_name}.md"
    fi

    # Check YAML syntax
    if ! check_yaml_syntax "$file"; then
        error "YAML syntax validation failed"
        return 1
    fi
    success "YAML syntax is valid"

    # Validate model override if present
    local model=$(yaml_get "$file" "model")
    if [[ -n "$model" ]]; then
        local valid=false
        for valid_model in "${VALID_MODELS[@]}"; do
            if [[ "$model" == "$valid_model" ]]; then
                valid=true
                break
            fi
        done

        if [[ "$valid" == "true" ]]; then
            success "Model override is valid: $model"
        else
            error "Invalid model: '$model'. Valid options: ${VALID_MODELS[*]}"
        fi
    fi

    # Validate budget override if present
    local budget=$(yaml_get "$file" "max_budget_usd")
    if [[ -n "$budget" ]]; then
        # Check if it's a valid number
        if [[ "$budget" =~ ^[0-9]+\.?[0-9]*$ ]]; then
            if (( $(echo "$budget < $MIN_BUDGET" | bc -l) )); then
                error "Budget too low: $budget (minimum: $MIN_BUDGET)"
            elif (( $(echo "$budget > $MAX_BUDGET" | bc -l) )); then
                warning "Budget unusually high: $budget (maximum recommended: $MAX_BUDGET)"
            else
                success "Budget override is valid: \$$budget"
            fi
        else
            error "Invalid budget format: '$budget' (must be a number)"
        fi
    fi

    # Check for additional_rules
    if yaml_has_list "$file" "additional_rules"; then
        local rule_count=$(awk '/^additional_rules:/{found=1; next} found && /^[[:space:]]*-/{count++} found && /^[a-zA-Z]/{exit} END{print count}' "$file")
        success "Additional rules defined: ${rule_count:-0} rules"
    fi

    # Check for memories
    if yaml_has_list "$file" "memories"; then
        local memory_count=$(awk '/^memories:/{found=1; next} found && /^[[:space:]]*-/{count++} found && /^[a-zA-Z]/{exit} END{print count}' "$file")
        success "Memories defined: ${memory_count:-0} items"
    fi

    # Check for critical_actions
    if yaml_has_list "$file" "critical_actions"; then
        local action_count=$(awk '/^critical_actions:/{found=1; next} found && /^[[:space:]]*-/{count++} found && /^[a-zA-Z]/{exit} END{print count}' "$file")
        success "Critical actions defined: ${action_count:-0} actions"
    fi

    ((VALIDATED++))
    return 0
}

validate_user_profile() {
    local file="$OVERRIDES_DIR/user-profile.yaml"

    if [[ ! -f "$file" ]]; then
        warning "No user-profile.yaml found"
        return 0
    fi

    echo ""
    echo -e "${BLUE}Validating:${NC} user-profile.yaml"

    # Check YAML syntax
    if ! check_yaml_syntax "$file"; then
        error "YAML syntax validation failed"
        return 1
    fi
    success "YAML syntax is valid"

    # Check for user section
    if grep -q "^user:" "$file"; then
        success "User section found"

        local name=$(grep -A10 "^user:" "$file" | grep "name:" | sed 's/.*name:[[:space:]]*//' | head -1)
        if [[ -n "$name" && "$name" != "User" ]]; then
            success "User name configured: $name"
        fi

        local level=$(grep -A10 "^user:" "$file" | grep "technical_level:" | sed 's/.*technical_level:[[:space:]]*//' | head -1)
        if [[ -n "$level" ]]; then
            local valid_levels=("beginner" "intermediate" "advanced" "expert")
            local valid=false
            for valid_level in "${valid_levels[@]}"; do
                if [[ "${level,,}" == "$valid_level" ]]; then
                    valid=true
                    break
                fi
            done

            if [[ "$valid" == "true" ]]; then
                success "Technical level: $level"
            else
                warning "Unusual technical level: $level"
            fi
        fi
    else
        warning "No user section found in profile"
    fi

    ((VALIDATED++))
    return 0
}

################################################################################
# Auto-Fix Functions
################################################################################

fix_trailing_whitespace() {
    local file="$1"
    # Remove trailing whitespace
    sed -i '' 's/[[:space:]]*$//' "$file" 2>/dev/null || \
    sed -i 's/[[:space:]]*$//' "$file" 2>/dev/null
    success "Fixed trailing whitespace in $(basename "$file")"
}

fix_tabs() {
    local file="$1"
    # Convert tabs to 2 spaces
    sed -i '' 's/\t/  /g' "$file" 2>/dev/null || \
    sed -i 's/\t/  /g' "$file" 2>/dev/null
    success "Converted tabs to spaces in $(basename "$file")"
}

auto_fix_file() {
    local file="$1"
    echo ""
    echo -e "${YELLOW}Auto-fixing:${NC} $(basename "$file")"

    # Backup original
    cp "$file" "${file}.bak"

    fix_trailing_whitespace "$file"
    fix_tabs "$file"

    # Remove backup if no changes
    if diff -q "$file" "${file}.bak" > /dev/null 2>&1; then
        rm "${file}.bak"
        info "No changes needed"
    else
        info "Changes made (backup saved as ${file}.bak)"
    fi
}

################################################################################
# Main
################################################################################

print_usage() {
    echo "Usage: ./validate-overrides.sh [agent-name] [options]"
    echo ""
    echo "Options:"
    echo "  <agent-name>    Validate specific agent override (e.g., 'dev')"
    echo "  --fix           Auto-fix common issues (whitespace, tabs)"
    echo "  --verbose       Show detailed output"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./validate-overrides.sh               # Validate all overrides"
    echo "  ./validate-overrides.sh dev           # Validate dev.override.yaml"
    echo "  ./validate-overrides.sh --fix         # Fix all issues"
    echo ""
}

main() {
    local target=""
    local FIX_MODE=false
    VERBOSE=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --fix)
                FIX_MODE=true
                ;;
            --verbose|-v)
                VERBOSE=true
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            *)
                target="$1"
                ;;
        esac
        shift
    done

    print_header

    if [[ ! -d "$OVERRIDES_DIR" ]]; then
        error "Overrides directory not found: $OVERRIDES_DIR"
        exit 1
    fi

    if [[ -n "$target" ]]; then
        # Validate specific override
        local file="$OVERRIDES_DIR/${target}.override.yaml"
        if [[ ! -f "$file" ]]; then
            error "Override file not found: $file"
            exit 1
        fi

        if [[ "$FIX_MODE" == "true" ]]; then
            auto_fix_file "$file"
        fi
        validate_override_file "$file"
    else
        # Validate all overrides
        echo -e "${BLUE}Scanning:${NC} $OVERRIDES_DIR"

        # Validate user profile first
        if [[ "$FIX_MODE" == "true" && -f "$OVERRIDES_DIR/user-profile.yaml" ]]; then
            auto_fix_file "$OVERRIDES_DIR/user-profile.yaml"
        fi
        validate_user_profile

        # Validate all override files
        for file in "$OVERRIDES_DIR"/*.override.yaml; do
            if [[ -f "$file" ]]; then
                if [[ "$FIX_MODE" == "true" ]]; then
                    auto_fix_file "$file"
                fi
                validate_override_file "$file"
            fi
        done
    fi

    # Summary
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  VALIDATION SUMMARY${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Files validated: ${GREEN}$VALIDATED${NC}"
    echo -e "  Errors:          ${RED}$ERRORS${NC}"
    echo -e "  Warnings:        ${YELLOW}$WARNINGS${NC}"
    echo ""

    if [[ $ERRORS -gt 0 ]]; then
        echo -e "${RED} Validation failed with $ERRORS error(s)${NC}"
        exit 1
    elif [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}  Validation passed with $WARNINGS warning(s)${NC}"
        exit 0
    else
        echo -e "${GREEN} All validations passed!${NC}"
        exit 0
    fi
}

main "$@"
