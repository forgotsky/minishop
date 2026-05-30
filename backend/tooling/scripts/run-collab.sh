#!/usr/bin/env bash
#
# Devflow Collaborative Story Runner
# Multi-agent collaboration CLI wrapper for Unix systems
#
# Usage:
#   ./run-collab.sh <story-key> [options]
#
# Examples:
#   ./run-collab.sh 3-5 --swarm
#   ./run-collab.sh 3-5 --pair
#   ./run-collab.sh "fix auth bug" --auto

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/run-collab.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║        DEVFLOW COLLABORATIVE STORY RUNNER                     ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    echo "║  Multi-agent collaboration with swarm, pair, and auto-routing ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_usage() {
    echo "Usage: $0 <story-key> [options]"
    echo ""
    echo "Modes:"
    echo "  --auto          Auto-route to best agents (default)"
    echo "  --swarm         Multi-agent debate/consensus"
    echo "  --pair          DEV + REVIEWER pair programming"
    echo "  --sequential    Traditional sequential pipeline"
    echo ""
    echo "Options:"
    echo "  --agents <list>      Comma-separated agent list (for swarm)"
    echo "  --max-iterations <n> Max iterations (default: 3)"
    echo "  --model <name>       Claude model (opus, sonnet, haiku)"
    echo "  --budget <amount>    Budget limit in USD (default: 20.0)"
    echo "  --memory             Show shared memory"
    echo "  --query <question>   Query knowledge graph"
    echo "  --route-only         Just show routing, don't execute"
    echo "  --quiet              Reduce verbosity"
    echo ""
    echo "Examples:"
    echo "  $0 3-5 --swarm"
    echo "  $0 3-5 --pair"
    echo "  $0 'fix auth bug' --auto"
    echo "  $0 3-5 --swarm --agents ARCHITECT,DEV,REVIEWER"
}

# Check for Python
detect_python() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        # Verify it's Python 3
        if python --version 2>&1 | grep -q "Python 3"; then
            echo "python"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Main
main() {
    # Check for help flag
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        show_usage
        exit 0
    fi

    # Check for Python
    PYTHON_CMD=$(detect_python)
    if [[ -z "$PYTHON_CMD" ]]; then
        echo -e "${RED}Error: Python 3 not found. Please install Python 3.9+${NC}"
        exit 1
    fi

    # Check if Python script exists
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        echo -e "${RED}Error: run-collab.py not found at $PYTHON_SCRIPT${NC}"
        exit 1
    fi

    # Print banner for non-quiet mode
    if [[ "$*" != *"--quiet"* && "$*" != *"-q"* ]]; then
        print_banner
    fi

    # Pass all arguments to Python script
    exec "$PYTHON_CMD" "$PYTHON_SCRIPT" "$@"
}

main "$@"
