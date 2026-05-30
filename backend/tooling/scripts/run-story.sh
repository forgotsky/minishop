#!/usr/bin/env bash
################################################################################
# RUN-STORY - Simple Automated Story Implementation
#
# This script invokes Claude Code to implement a story automatically.
#
# Usage:
#   ./run-story.sh <story-key>           # Full pipeline (context + dev + review)
#   ./run-story.sh <story-key> --develop # Development only
#   ./run-story.sh <story-key> --review  # Review only
#
# Examples:
#   ./run-story.sh 3-5                   # Run full automation for story 3-5
#   ./run-story.sh 3-5 --develop         # Just run development phase
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
SPRINT_STATUS="$PROJECT_ROOT/docs/sprint-status.yaml"

# Load configuration (with existence check)
CONFIG_FILE="$PROJECT_ROOT/.automation/config.sh"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo -e "${YELLOW}Warning: Configuration file not found at $CONFIG_FILE${NC}"
    echo -e "${YELLOW}Using default settings. Run init-project-workflow.sh to set up configuration.${NC}"
    # Set defaults
    AUTO_COMMIT=${AUTO_COMMIT:-false}
    DEFAULT_MODEL=${DEFAULT_MODEL:-sonnet}
fi

# Load CLI library (with existence check)
CLI_LIB="$SCRIPT_DIR/lib/claude-cli.sh"
if [[ -f "$CLI_LIB" ]]; then
    source "$CLI_LIB"
else
    echo -e "${RED}Error: Required library not found at $CLI_LIB${NC}"
    echo -e "${RED}Please ensure the Devflow installation is complete.${NC}"
    exit 1
fi

# Expand abbreviated story key (e.g., "3-5" -> "3-5-build-goal-detail-screen-with-edit-delete")
expand_story_key() {
    local input_key="$1"

    # If already a full key (has more than two dashes), return as-is
    if [[ "$input_key" =~ ^[0-9]+-[0-9]+-[a-z] ]]; then
        echo "$input_key"
        return
    fi

    # If abbreviated (e.g., "3-5"), look up full key
    if [[ "$input_key" =~ ^[0-9]+-[0-9]+$ ]]; then
        local full_key=$(grep -E "^  $input_key-[a-z]" "$SPRINT_STATUS" 2>/dev/null | head -1 | awk '{print $1}' | sed 's/://' || echo "")

        if [[ -n "$full_key" ]]; then
            echo "$full_key"
            return
        fi
    fi

    echo "$input_key"
}

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  AUTOMATED STORY RUNNER${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_usage() {
    echo "Usage: ./run-story.sh <key> [options]"
    echo ""
    echo "GREENFIELD MODES (New Features):"
    echo "  (default)       Run full pipeline (context + dev + review + commit)"
    echo "  --develop       Run development phase only"
    echo "  --review        Run review phase only"
    echo "  --adversarial   Run adversarial review (critical, finds problems)"
    echo "  --context       Create story context only"
    echo ""
    echo "COLLABORATIVE MODES (Multi-Agent):"
    echo "  --swarm         Multi-agent debate/consensus mode"
    echo "  --pair          DEV + REVIEWER pair programming"
    echo "  --auto-route    Auto-select best agents for the task"
    echo ""
    echo "BROWNFIELD MODES (Existing Codebase):"
    echo "  --bugfix        Fix a bug (key = bug ID or description)"
    echo "  --refactor      Refactor code (key = refactor target or ID)"
    echo "  --investigate   Investigate codebase (key = topic to explore)"
    echo "  --quickfix      Quick, minimal change (key = description)"
    echo "  --migrate       Run a migration (key = migration ID)"
    echo "  --tech-debt     Resolve technical debt (key = debt ID)"
    echo ""
    echo "OPTIONS:"
    echo "  --no-commit     Disable auto-commit after changes"
    echo "  --with-pr       Enable auto-PR creation (requires gh CLI)"
    echo "  --model <name>  Use specific Claude model (sonnet|opus|haiku)"
    echo "  --agents <list> Comma-separated agent list (for swarm mode)"
    echo "  --max-iter <n>  Max iterations for swarm/pair modes (default: 3)"
    echo ""
    echo "Environment Variables:"
    echo "  AUTO_COMMIT=true|false    Enable/disable auto-commit (default: true)"
    echo "  AUTO_PR=true|false        Enable/disable auto-PR (default: false)"
    echo "  CLAUDE_MODEL=<name>       Set Claude model (default: sonnet)"
    echo ""
    echo "GREENFIELD EXAMPLES:"
    echo "  ./run-story.sh 3-5                    # Full story pipeline"
    echo "  ./run-story.sh 3-5 --develop          # Development only"
    echo "  ./run-story.sh 3-5 --model opus       # Use Claude Opus"
    echo ""
    echo "COLLABORATIVE EXAMPLES:"
    echo "  ./run-story.sh 3-5 --swarm                         # Multi-agent debate"
    echo "  ./run-story.sh 3-5 --pair                          # DEV+REVIEWER pair"
    echo "  ./run-story.sh 3-5 --swarm --agents DEV,REVIEWER   # Custom agents"
    echo "  ./run-story.sh 'fix auth bug' --auto-route         # Auto-select agents"
    echo ""
    echo "BROWNFIELD EXAMPLES:"
    echo "  ./run-story.sh login-crash --bugfix           # Fix bug"
    echo "  ./run-story.sh auth-service --refactor        # Refactor code"
    echo "  ./run-story.sh payment-flow --investigate     # Investigate code"
    echo "  ./run-story.sh 'fix typo in header' --quickfix # Quick fix"
    echo "  ./run-story.sh react-18 --migrate             # Run migration"
    echo "  ./run-story.sh legacy-api --tech-debt         # Fix tech debt"
    echo ""
}

main() {
    if [[ $# -eq 0 ]]; then
        print_usage
        exit 1
    fi

    # Expand abbreviated story key
    local story_key=$(expand_story_key "$1")
    shift

    # Parse options
    local mode="full"
    local collab_agents=""
    local max_iterations=3
    export AUTO_COMMIT="${AUTO_COMMIT:-true}"
    export AUTO_PR="${AUTO_PR:-false}"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            # Greenfield modes
            "--develop"|"--dev")
                mode="develop"
                ;;
            "--review")
                mode="review"
                ;;
            "--context")
                mode="context"
                ;;
            "--adversarial"|"--adv")
                mode="adversarial"
                ;;
            # Collaborative modes
            "--swarm")
                mode="swarm"
                ;;
            "--pair")
                mode="pair"
                ;;
            "--auto-route"|"--auto")
                mode="auto-route"
                ;;
            "--agents")
                shift
                if [[ $# -eq 0 ]]; then
                    echo "Error: --agents requires an argument"
                    print_usage
                    exit 1
                fi
                collab_agents="$1"
                ;;
            "--max-iter"|"--max-iterations")
                shift
                if [[ $# -eq 0 ]]; then
                    echo "Error: --max-iter requires an argument"
                    print_usage
                    exit 1
                fi
                max_iterations="$1"
                ;;
            # Brownfield modes
            "--bugfix"|"--bug")
                mode="bugfix"
                ;;
            "--refactor")
                mode="refactor"
                ;;
            "--investigate"|"--explore")
                mode="investigate"
                ;;
            "--quickfix"|"--quick")
                mode="quickfix"
                ;;
            "--migrate"|"--migration")
                mode="migrate"
                ;;
            "--tech-debt"|"--debt")
                mode="tech-debt"
                ;;
            # Options
            "--no-commit")
                AUTO_COMMIT="false"
                ;;
            "--with-pr")
                AUTO_PR="true"
                ;;
            "--model")
                shift
                if [[ $# -eq 0 ]]; then
                    echo "Error: --model requires an argument (sonnet|opus|haiku)"
                    print_usage
                    exit 1
                fi
                export CLAUDE_MODEL="$1"
                ;;
            *)
                echo "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
        shift
    done

    print_header
    echo -e "${BLUE}Story:${NC} $story_key"
    echo -e "${BLUE}Mode:${NC} $mode"
    echo -e "${BLUE}Model:${NC} $CLAUDE_MODEL"
    echo -e "${BLUE}Auto-commit:${NC} $AUTO_COMMIT"
    echo -e "${BLUE}Auto-PR:${NC} $AUTO_PR"
    echo ""

    # Check for existing checkpoint and offer to resume
    if type has_checkpoint &>/dev/null && has_checkpoint "$story_key"; then
        echo -e "${CYAN} Found existing checkpoint for story: $story_key${NC}"
        echo -e "${YELLOW}Would you like to resume from the checkpoint? (y/n)${NC}"
        read -r RESUME_CHOICE

        if [[ "$RESUME_CHOICE" =~ ^[Yy]$ ]]; then
            if type resume_from_checkpoint &>/dev/null; then
                resume_from_checkpoint "$story_key"
                return 0
            fi
        else
            echo -e "${GREEN}Starting fresh implementation...${NC}"
            echo ""
        fi
    fi

    # Create pre-start checkpoint
    if type create_story_checkpoint &>/dev/null; then
        echo -e "${CYAN} Creating pre-start checkpoint...${NC}"
        create_story_checkpoint "$story_key" "pre-start" 2>&1 | grep -v "Could not export"
        echo ""
    fi

    case "$mode" in
        # ═══════════════════════════════════════════════════════════════
        # COLLABORATIVE MODES - Multi-agent collaboration
        # ═══════════════════════════════════════════════════════════════
        "swarm")
            echo -e "${YELLOW}> Running swarm mode (multi-agent debate)...${NC}"
            echo ""
            local swarm_args="$story_key --swarm"
            if [[ -n "$collab_agents" ]]; then
                swarm_args="$swarm_args --agents $collab_agents"
            fi
            swarm_args="$swarm_args --max-iterations $max_iterations"
            python3 "$SCRIPT_DIR/run-collab.py" $swarm_args
            local exit_code=$?

            if [[ $exit_code -eq 0 && "$AUTO_COMMIT" == "true" ]]; then
                auto_commit_changes "$story_key"
            fi
            ;;
        "pair")
            echo -e "${YELLOW}> Running pair programming mode (DEV + REVIEWER)...${NC}"
            echo ""
            python3 "$SCRIPT_DIR/run-collab.py" "$story_key" --pair --max-revisions "$max_iterations"
            local exit_code=$?

            if [[ $exit_code -eq 0 && "$AUTO_COMMIT" == "true" ]]; then
                auto_commit_changes "$story_key"
            fi
            ;;
        "auto-route")
            echo -e "${YELLOW}> Running auto-route mode (intelligent agent selection)...${NC}"
            echo ""
            python3 "$SCRIPT_DIR/run-collab.py" "$story_key" --auto
            local exit_code=$?

            if [[ $exit_code -eq 0 && "$AUTO_COMMIT" == "true" ]]; then
                auto_commit_changes "$story_key"
            fi
            ;;

        # ═══════════════════════════════════════════════════════════════
        # GREENFIELD MODES - New feature development
        # ═══════════════════════════════════════════════════════════════
        "develop")
            echo -e "${YELLOW}> Running development phase...${NC}"
            echo ""
            invoke_dev_story "$story_key"
            local exit_code=$?

            # Update status to 'review' if successful
            if [[ $exit_code -eq 0 ]]; then
                update_story_status "$story_key" "review"
            fi

            # Auto-commit after dev if enabled
            if [[ $exit_code -eq 0 && "$AUTO_COMMIT" == "true" ]]; then
                auto_commit_changes "$story_key"
            fi

            # Auto-PR if enabled
            if [[ $exit_code -eq 0 && "$AUTO_PR" == "true" ]]; then
                auto_create_pr "$story_key"
            fi
            ;;
        "review")
            echo -e "${YELLOW}> Running review phase...${NC}"
            echo ""
            invoke_sm_code_review "$story_key"
            exit_code=$?
            ;;
        "adversarial")
            echo -e "${YELLOW}> Running adversarial review (Opus)...${NC}"
            echo ""
            invoke_adversarial_review "$story_key"
            exit_code=$?
            ;;
        "context")
            echo -e "${YELLOW}> Creating story context...${NC}"
            echo ""
            invoke_sm_story_context "$story_key"
            exit_code=$?
            ;;

        # ═══════════════════════════════════════════════════════════════
        # BROWNFIELD MODES - Existing codebase maintenance
        # ═══════════════════════════════════════════════════════════════
        "bugfix")
            echo -e "${YELLOW}> Running bug fix workflow...${NC}"
            echo ""
            invoke_bugfix "$story_key"
            exit_code=$?

            # Auto-commit after bugfix if enabled
            if [[ $exit_code -eq 0 && "$AUTO_COMMIT" == "true" ]]; then
                auto_commit_changes "$story_key"
            fi
            ;;
        "refactor")
            echo -e "${YELLOW}> Running refactoring workflow...${NC}"
            echo ""
            invoke_refactor "$story_key"
            exit_code=$?

            # Auto-commit after refactor if enabled
            if [[ $exit_code -eq 0 && "$AUTO_COMMIT" == "true" ]]; then
                auto_commit_changes "$story_key"
            fi
            ;;
        "investigate")
            echo -e "${YELLOW}> Running investigation workflow...${NC}"
            echo ""
            invoke_investigate "$story_key"
            exit_code=$?
            # No auto-commit for investigation (read-only)
            ;;
        "quickfix")
            echo -e "${YELLOW}> Running quick fix...${NC}"
            echo ""
            invoke_quickfix "$story_key"
            exit_code=$?

            # Auto-commit after quickfix if enabled
            if [[ $exit_code -eq 0 && "$AUTO_COMMIT" == "true" ]]; then
                auto_commit_changes "$story_key"
            fi
            ;;
        "migrate")
            echo -e "${YELLOW}> Running migration workflow...${NC}"
            echo ""
            invoke_migrate "$story_key"
            exit_code=$?

            # Auto-commit after migration if enabled
            if [[ $exit_code -eq 0 && "$AUTO_COMMIT" == "true" ]]; then
                auto_commit_changes "$story_key"
            fi
            ;;
        "tech-debt")
            echo -e "${YELLOW}> Running technical debt resolution...${NC}"
            echo ""
            invoke_tech_debt "$story_key"
            exit_code=$?

            # Auto-commit after tech-debt resolution if enabled
            if [[ $exit_code -eq 0 && "$AUTO_COMMIT" == "true" ]]; then
                auto_commit_changes "$story_key"
            fi
            ;;

        # ═══════════════════════════════════════════════════════════════
        # DEFAULT - Full greenfield pipeline
        # ═══════════════════════════════════════════════════════════════
        *)
            echo -e "${YELLOW}> Running full pipeline...${NC}"
            echo ""
            run_full_pipeline "$story_key"
            exit_code=$?
            ;;
    esac

    # Create completion checkpoint if successful
    if [[ $exit_code -eq 0 && "$mode" != "context" ]]; then
        if type create_story_checkpoint &>/dev/null; then
            echo -e "${CYAN} Creating completion checkpoint...${NC}"
            create_story_checkpoint "$story_key" "complete" 2>&1 | grep -v "Could not export"
            echo ""
        fi
    fi

    # Cleanup old checkpoints (keep last 10)
    if type cleanup_old_checkpoints &>/dev/null; then
        cleanup_old_checkpoints 10 2>&1 | grep -E "^(||Deleted)"
        echo ""
    fi

    echo ""
    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN} Complete!${NC}"
    else
        echo -e "${RED} Failed with exit code: $exit_code${NC}"
    fi

    echo ""
    echo -e "${BLUE}Log files:${NC} $PROJECT_ROOT/.automation/logs/"
    echo -e "${BLUE}Checkpoints:${NC} $PROJECT_ROOT/.automation/checkpoints/"
    echo ""

    return $exit_code
}

main "$@"
