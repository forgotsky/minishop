#!/usr/bin/env bash
################################################################################
# Create Persona - Custom Agent Persona Builder
#
# This interactive tool helps create custom agent personas for the Devflow
# workflow system. It generates properly formatted agent files.
#
# Usage:
#   ./create-persona.sh                     # Interactive mode
#   ./create-persona.sh --list              # List existing personas
#   ./create-persona.sh --template dev      # Create from template
#
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTS_DIR="$PROJECT_ROOT/.automation/agents"
OVERRIDES_DIR="$PROJECT_ROOT/.automation/overrides"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  CUSTOM PERSONA BUILDER${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

prompt() {
    local message="$1"
    local default="$2"
    local result

    if [[ -n "$default" ]]; then
        echo -n -e "${BLUE}${message}${NC} [${default}]: "
    else
        echo -n -e "${BLUE}${message}${NC}: "
    fi

    read result

    if [[ -z "$result" && -n "$default" ]]; then
        echo "$default"
    else
        echo "$result"
    fi
}

prompt_list() {
    local message="$1"
    local min_items="${2:-0}"
    local items=()
    local count=0

    echo -e "${BLUE}${message}${NC}"
    echo "  (Enter items one per line, empty line to finish)"

    while true; do
        ((count++))
        echo -n "  $count. "
        read item

        if [[ -z "$item" ]]; then
            if [[ ${#items[@]} -ge $min_items ]]; then
                break
            else
                echo -e "${YELLOW}Please enter at least $min_items item(s).${NC}"
                ((count--))
                continue
            fi
        fi

        items+=("$item")
    done

    printf '%s\n' "${items[@]}"
}

################################################################################
# Persona Templates
################################################################################

get_template() {
    local template_name="$1"

    case "$template_name" in
        developer|dev)
            echo "developer|Software Developer|Writing clean, maintainable code|sonnet"
            ;;
        reviewer)
            echo "reviewer|Code Reviewer|Ensuring code quality and best practices|sonnet"
            ;;
        architect)
            echo "architect|Software Architect|System design and technical decisions|opus"
            ;;
        tester|qa)
            echo "tester|QA Engineer|Quality assurance and testing|sonnet"
            ;;
        security)
            echo "security|Security Engineer|Application security and vulnerability prevention|opus"
            ;;
        devops)
            echo "devops|DevOps Engineer|CI/CD, infrastructure, and deployment|sonnet"
            ;;
        documentation|docs|writer)
            echo "documentation|Technical Writer|Clear and comprehensive documentation|sonnet"
            ;;
        *)
            echo ""
            ;;
    esac
}

################################################################################
# Persona Generation
################################################################################

generate_agent_file() {
    local name="$1"
    local role="$2"
    local focus="$3"
    local model="$4"
    shift 4
    local responsibilities=("${@}")

    local file="$AGENTS_DIR/${name}.md"

    cat > "$file" << EOF
# ${role} Agent

You are a ${role}. ${focus}

## Responsibilities

EOF

    local count=0
    for resp in "${responsibilities[@]}"; do
        ((count++))
        echo "$count. $resp" >> "$file"
    done

    cat >> "$file" << 'EOF'

## Principles

1. **Quality First** - Maintain high standards in all work
2. **Clear Communication** - Be precise and explanatory
3. **Continuous Improvement** - Learn and adapt from each task
4. **Collaboration** - Work effectively with other agents and humans

## Communication Style

Professional, clear, and focused on actionable outcomes.

## Context Management

You are running in an automated pipeline with limited context window. To avoid losing work:

1. **Work incrementally** - Complete and save files one at a time
2. **Checkpoint frequently** - After each significant change, ensure the file is written
3. **Monitor your progress** - If you notice you've been working for a while, prioritize critical items
4. **Self-assess context usage** - If you estimate you're past 80% of your context:
   - Finish the current file you're working on
   - Write a summary of remaining work
   - Complete what you can rather than leaving partial work

If you sense context is running low, output a warning:
```
 CONTEXT WARNING: Approaching context limit. Prioritizing completion of current task.
```

EOF

    echo "## Model" >> "$file"
    echo "" >> "$file"
    echo "Recommended model: \`${model}\`" >> "$file"
    echo "" >> "$file"

    echo "$file"
}

generate_override_file() {
    local name="$1"

    local file="$OVERRIDES_DIR/${name}.override.yaml"

    # Don't overwrite existing
    if [[ -f "$file" ]]; then
        return
    fi

    cat > "$file" << EOF
# ${name^^} Agent Override
# Customize this agent's behavior without modifying the core agent file
# These settings survive updates to the core agent

# Additional rules (appended to base agent rules)
additional_rules:
  - "Add your custom rules here"

# Memories - facts this agent should always remember
memories:
  - "Add project-specific context here"

# Critical actions - must be done before completing any task
critical_actions:
  - "Verify work meets requirements"

# Model override (optional)
# model: "sonnet"

# Budget override (optional)
# max_budget_usd: 10.00

EOF

    echo "$file"
}

################################################################################
# Commands
################################################################################

list_personas() {
    echo -e "${BOLD}Available Agent Personas:${NC}"
    echo ""

    if [[ ! -d "$AGENTS_DIR" ]]; then
        echo -e "  ${YELLOW}No agents directory found.${NC}"
        return
    fi

    printf "  %-15s │ %-25s │ Override\n" "NAME" "ROLE"
    printf "  %s\n" "$(printf '─%.0s' {1..50})"

    for agent_file in "$AGENTS_DIR"/*.md; do
        if [[ -f "$agent_file" ]]; then
            local name=$(basename "$agent_file" .md)
            local role=$(head -1 "$agent_file" | sed 's/# //' | sed 's/ Agent$//')

            local has_override=" "
            if [[ -f "$OVERRIDES_DIR/${name}.override.yaml" ]]; then
                has_override="[OK]"
            fi

            printf "  ${GREEN}%-15s${NC} │ %-25s │ %s\n" "$name" "$role" "$has_override"
        fi
    done

    echo ""
}

create_from_template() {
    local template_name="$1"
    local persona_name="$2"

    local template=$(get_template "$template_name")

    if [[ -z "$template" ]]; then
        echo -e "${RED}Unknown template: $template_name${NC}"
        echo "Available templates: developer, reviewer, architect, tester, security, devops, documentation"
        exit 1
    fi

    # Parse template
    IFS='|' read -r tpl_name role focus model <<< "$template"

    # Use provided name or template name
    local name="${persona_name:-$tpl_name}"

    # Default responsibilities
    local responsibilities=(
        "Complete assigned tasks efficiently"
        "Follow project standards and best practices"
        "Document work appropriately"
        "Communicate progress and blockers"
    )

    mkdir -p "$AGENTS_DIR" "$OVERRIDES_DIR"

    local agent_file=$(generate_agent_file "$name" "$role" "$focus" "$model" "${responsibilities[@]}")
    local override_file=$(generate_override_file "$name")

    echo -e "${GREEN}[OK] Persona created from template!${NC}"
    echo ""
    echo "  Agent file:    $agent_file"
    [[ -n "$override_file" ]] && echo "  Override file: $override_file"
    echo ""
}

interactive_create() {
    echo -e "${BOLD}Let's create your custom agent persona!${NC}"
    echo ""

    # Get name
    local name=$(prompt "Persona name (e.g., 'qa', 'frontend-dev')")
    name=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

    if [[ -z "$name" ]]; then
        echo -e "${RED}Name is required.${NC}"
        exit 1
    fi

    # Check if exists
    if [[ -f "$AGENTS_DIR/${name}.md" ]]; then
        echo -e "${YELLOW}Persona '$name' already exists.${NC}"
        local overwrite=$(prompt "Overwrite? (y/n)" "n")
        if [[ "$overwrite" != "y" ]]; then
            exit 0
        fi
    fi

    # Get details
    echo ""
    local role=$(prompt "Role (e.g., 'Senior QA Engineer')")
    local focus=$(prompt "Focus (one-line description)")

    echo ""
    echo "Select model:"
    echo "  1. sonnet (default - balanced)"
    echo "  2. opus (complex tasks)"
    echo "  3. haiku (quick tasks)"
    local model_choice=$(prompt "Choice" "1")

    local model="sonnet"
    case "$model_choice" in
        2|opus) model="opus" ;;
        3|haiku) model="haiku" ;;
    esac

    echo ""
    echo "Enter responsibilities (what this agent does):"
    local responsibilities=()
    local count=0
    while true; do
        ((count++))
        local resp=$(prompt "  $count")
        if [[ -z "$resp" ]]; then
            if [[ ${#responsibilities[@]} -ge 2 ]]; then
                break
            else
                echo -e "${YELLOW}Please enter at least 2 responsibilities.${NC}"
                ((count--))
                continue
            fi
        fi
        responsibilities+=("$resp")
    done

    # Create files
    mkdir -p "$AGENTS_DIR" "$OVERRIDES_DIR"

    local agent_file=$(generate_agent_file "$name" "$role" "$focus" "$model" "${responsibilities[@]}")
    local override_file=$(generate_override_file "$name")

    echo ""
    echo -e "${GREEN}[OK] Persona created successfully!${NC}"
    echo ""
    echo "  Agent file:    $agent_file"
    [[ -n "$override_file" ]] && echo "  Override file: $override_file"
    echo ""
    echo -e "${BOLD}Next steps:${NC}"
    echo "  1. Review and customize: $agent_file"
    echo "  2. Add project-specific memories in the override file"
    echo "  3. Use with: ./run-story.sh <story> --agent $name"
    echo ""
}

################################################################################
# Main
################################################################################

print_usage() {
    echo "Usage: ./create-persona.sh [options]"
    echo ""
    echo "Commands:"
    echo "  (no args)          Interactive persona creation"
    echo "  --list             List existing personas"
    echo "  --template <name>  Create from template"
    echo ""
    echo "Templates available:"
    echo "  developer, reviewer, architect, tester, security, devops, documentation"
    echo ""
    echo "Examples:"
    echo "  ./create-persona.sh                          # Interactive mode"
    echo "  ./create-persona.sh --list                   # List personas"
    echo "  ./create-persona.sh --template tester my-qa  # Create from template"
    echo ""
}

main() {
    print_header

    case "$1" in
        --list|-l)
            list_personas
            ;;
        --template|-t)
            shift
            if [[ -z "$1" ]]; then
                echo -e "${RED}Please specify a template name.${NC}"
                exit 1
            fi
            create_from_template "$1" "$2"
            ;;
        --help|-h)
            print_usage
            ;;
        "")
            interactive_create
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
