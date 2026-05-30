#!/usr/bin/env bash
################################################################################
# Override Loader Library
#
# Loads user profile and agent overrides to personalize agent behavior.
# Overrides are stored in tooling/.automation/overrides/ and survive updates.
#
# Usage:
#   source lib/override-loader.sh
#   load_agent_with_overrides "dev"  # Returns combined agent prompt
################################################################################

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OVERRIDES_DIR="$PROJECT_ROOT/.automation/overrides"
AGENTS_DIR="$PROJECT_ROOT/.automation/agents"
MEMORY_DIR="$PROJECT_ROOT/.automation/memory"

################################################################################
# YAML Parsing Helpers (basic, for simple YAML structures)
################################################################################

# Extract a simple value from YAML (key: value)
yaml_get_value() {
    local file="$1"
    local key="$2"
    grep -E "^${key}:" "$file" 2>/dev/null | sed "s/^${key}:[[:space:]]*//" | sed 's/^["'"'"']//' | sed 's/["'"'"']$//'
}

# Extract a nested value (parent.child: value)
yaml_get_nested() {
    local file="$1"
    local parent="$2"
    local child="$3"
    awk "/^${parent}:/{found=1} found && /^  ${child}:/{print; exit}" "$file" 2>/dev/null | sed "s/^[[:space:]]*${child}:[[:space:]]*//" | sed 's/^["'"'"']//' | sed 's/["'"'"']$//'
}

# Extract a list from YAML (returns newline-separated items)
yaml_get_list() {
    local file="$1"
    local key="$2"
    awk "/^${key}:/{found=1; next} found && /^[[:space:]]*-/{print} found && /^[a-zA-Z]/{exit}" "$file" 2>/dev/null | sed 's/^[[:space:]]*-[[:space:]]*//' | sed 's/^["'"'"']//' | sed 's/["'"'"']$//'
}

################################################################################
# User Profile Loading
################################################################################

# Load user profile and return formatted context
load_user_profile() {
    local profile_file="$OVERRIDES_DIR/user-profile.yaml"

    if [[ ! -f "$profile_file" ]]; then
        return 0
    fi

    local user_name=$(yaml_get_nested "$profile_file" "user" "name")
    local tech_level=$(yaml_get_nested "$profile_file" "user" "technical_level")
    local comm_style=$(yaml_get_nested "$profile_file" "user" "communication_style")

    local output=""

    if [[ -n "$user_name" && "$user_name" != "User" ]]; then
        output+="
## User Context
- User name: $user_name"
    fi

    if [[ -n "$tech_level" ]]; then
        output+="
- Technical level: $tech_level"
    fi

    if [[ -n "$comm_style" ]]; then
        output+="
- Preferred communication: $comm_style"
    fi

    # Load code style preferences
    local code_style=$(yaml_get_list "$profile_file" "  code_style")
    if [[ -n "$code_style" ]]; then
        output+="

## Code Style Preferences"
        while IFS= read -r style; do
            [[ -n "$style" ]] && output+="
- $style"
        done <<< "$code_style"
    fi

    # Load memories
    local memories=$(yaml_get_list "$profile_file" "memories")
    if [[ -n "$memories" ]]; then
        output+="

## Project Memories (Always Remember)"
        while IFS= read -r memory; do
            [[ -n "$memory" ]] && output+="
- $memory"
        done <<< "$memories"
    fi

    echo "$output"
}

################################################################################
# Agent Override Loading
################################################################################

# Load agent-specific overrides
load_agent_override() {
    local agent_name="$1"
    local override_file="$OVERRIDES_DIR/${agent_name}.override.yaml"

    if [[ ! -f "$override_file" ]]; then
        return 0
    fi

    local output=""

    # Load additional rules
    local rules=$(yaml_get_list "$override_file" "additional_rules")
    if [[ -n "$rules" ]]; then
        output+="

## Additional Rules"
        while IFS= read -r rule; do
            [[ -n "$rule" ]] && output+="
- $rule"
        done <<< "$rules"
    fi

    # Load memories
    local memories=$(yaml_get_list "$override_file" "memories")
    if [[ -n "$memories" ]]; then
        output+="

## Agent Memories"
        while IFS= read -r memory; do
            [[ -n "$memory" ]] && output+="
- $memory"
        done <<< "$memories"
    fi

    # Load critical actions
    local actions=$(yaml_get_list "$override_file" "critical_actions")
    if [[ -n "$actions" ]]; then
        output+="

## Critical Actions (Must Do)"
        while IFS= read -r action; do
            [[ -n "$action" ]] && output+="
- $action"
        done <<< "$actions"
    fi

    echo "$output"
}

# Get model override for an agent
get_agent_model_override() {
    local agent_name="$1"
    local override_file="$OVERRIDES_DIR/${agent_name}.override.yaml"

    if [[ -f "$override_file" ]]; then
        yaml_get_value "$override_file" "model"
    fi
}

# Get budget override for an agent
get_agent_budget_override() {
    local agent_name="$1"
    local override_file="$OVERRIDES_DIR/${agent_name}.override.yaml"

    if [[ -f "$override_file" ]]; then
        yaml_get_value "$override_file" "max_budget_usd"
    fi
}

################################################################################
# Agent Memory Loading
################################################################################

# Load persistent memory for an agent
load_agent_memory() {
    local agent_name="$1"
    local memory_file="$MEMORY_DIR/${agent_name}.memory.md"

    if [[ -f "$memory_file" ]]; then
        echo "

## Persistent Memory

$(cat "$memory_file")"
    fi
}

# Append to agent memory
append_agent_memory() {
    local agent_name="$1"
    local memory_entry="$2"
    local memory_file="$MEMORY_DIR/${agent_name}.memory.md"

    mkdir -p "$MEMORY_DIR"

    # Add timestamp and entry
    echo "- $(date '+%Y-%m-%d %H:%M'): $memory_entry" >> "$memory_file"
}

################################################################################
# Main Loading Function
################################################################################

# Load agent with all overrides applied
# Returns the complete agent prompt with user profile, overrides, and memory
load_agent_with_overrides() {
    local agent_name="$1"
    local agent_file="$AGENTS_DIR/${agent_name}.md"

    # Start with base agent
    local output=""
    if [[ -f "$agent_file" ]]; then
        output=$(cat "$agent_file")
    else
        echo "Warning: Agent file not found: $agent_file" >&2
        return 1
    fi

    # Add user profile
    local profile=$(load_user_profile)
    if [[ -n "$profile" ]]; then
        output+="
$profile"
    fi

    # Add agent-specific overrides
    local override=$(load_agent_override "$agent_name")
    if [[ -n "$override" ]]; then
        output+="
$override"
    fi

    # Add persistent memory
    local memory=$(load_agent_memory "$agent_name")
    if [[ -n "$memory" ]]; then
        output+="
$memory"
    fi

    echo "$output"
}

# Check if overrides exist for an agent
has_overrides() {
    local agent_name="$1"
    [[ -f "$OVERRIDES_DIR/${agent_name}.override.yaml" ]]
}

# List all available overrides
list_overrides() {
    echo "Available overrides:"
    for file in "$OVERRIDES_DIR"/*.override.yaml; do
        if [[ -f "$file" ]]; then
            local name=$(basename "$file" .override.yaml)
            echo "  - $name"
        fi
    done
}

################################################################################
# Initialization
################################################################################

# Create overrides directory if it doesn't exist
init_overrides() {
    mkdir -p "$OVERRIDES_DIR" "$MEMORY_DIR"

    # Create user profile if it doesn't exist
    if [[ ! -f "$OVERRIDES_DIR/user-profile.yaml" ]]; then
        echo "# User profile not found. Creating default..." >&2
        # Default will be created by the main setup
    fi
}

# Auto-initialize when sourced
init_overrides 2>/dev/null || true
