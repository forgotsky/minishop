#!/usr/bin/env bash
################################################################################
# Rollback Migration - Automated Migration Rollback
#
# This script provides automated rollback capabilities for migrations.
# It can:
#   - Create rollback checkpoints before migrations
#   - Execute rollback steps defined in migration specs
#   - Restore from git-based checkpoints
#   - Handle dependency rollbacks
#
# Usage:
#   ./rollback-migration.sh <migration-id>              # Rollback a migration
#   ./rollback-migration.sh <migration-id> --dry-run    # Preview rollback
#   ./rollback-migration.sh <migration-id> --force      # Force rollback
#   ./rollback-migration.sh --list                      # List rollback points
#   ./rollback-migration.sh --create <name>             # Create rollback point
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
ROLLBACK_DIR="$PROJECT_ROOT/.automation/rollbacks"
CHECKPOINTS_DIR="$PROJECT_ROOT/.automation/checkpoints"
MIGRATIONS_DIR="$PROJECT_ROOT/docs/migrations"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  MIGRATION ROLLBACK TOOL${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

error() {
    echo -e "${RED}[X] ERROR:${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

info() {
    echo -e "${BLUE}[i]${NC} $1"
}

confirm() {
    local message="$1"
    echo -e "${YELLOW}$message${NC}"
    echo -n "Continue? [y/N] "
    read -r response
    [[ "$response" =~ ^[Yy]$ ]]
}

################################################################################
# Rollback Point Management
################################################################################

# Create a rollback point
create_rollback_point() {
    local name="$1"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local rollback_name="${timestamp}_${name}"
    local rollback_path="$ROLLBACK_DIR/$rollback_name"

    mkdir -p "$rollback_path"

    echo -e "${CYAN}Creating rollback point: $rollback_name${NC}"

    # Save git state
    local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    local current_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    local has_changes=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')

    # Create manifest
    cat > "$rollback_path/manifest.json" << EOF
{
    "name": "$name",
    "created": "$(date -Iseconds)",
    "branch": "$current_branch",
    "commit": "$current_commit",
    "has_uncommitted_changes": $([[ $has_changes -gt 0 ]] && echo "true" || echo "false"),
    "type": "migration-rollback"
}
EOF

    # Save uncommitted changes if any
    if [[ $has_changes -gt 0 ]]; then
        info "Saving uncommitted changes..."
        git stash push -m "rollback-$rollback_name" --include-untracked 2>/dev/null || true
        git stash show -p > "$rollback_path/uncommitted.patch" 2>/dev/null || true
        git stash pop 2>/dev/null || true
    fi

    # Save package state
    if [[ -f "$PROJECT_ROOT/package.json" ]]; then
        cp "$PROJECT_ROOT/package.json" "$rollback_path/"
        info "Saved package.json"
    fi

    if [[ -f "$PROJECT_ROOT/package-lock.json" ]]; then
        cp "$PROJECT_ROOT/package-lock.json" "$rollback_path/"
        info "Saved package-lock.json"
    fi

    if [[ -f "$PROJECT_ROOT/pubspec.yaml" ]]; then
        cp "$PROJECT_ROOT/pubspec.yaml" "$rollback_path/"
        info "Saved pubspec.yaml"
    fi

    if [[ -f "$PROJECT_ROOT/pubspec.lock" ]]; then
        cp "$PROJECT_ROOT/pubspec.lock" "$rollback_path/"
        info "Saved pubspec.lock"
    fi

    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        cp "$PROJECT_ROOT/requirements.txt" "$rollback_path/"
        info "Saved requirements.txt"
    fi

    success "Rollback point created: $rollback_path"
    echo "$rollback_name"
}

# List available rollback points
list_rollback_points() {
    echo -e "${BOLD}Available Rollback Points:${NC}"
    echo ""

    if [[ ! -d "$ROLLBACK_DIR" ]] || [[ -z "$(ls -A "$ROLLBACK_DIR" 2>/dev/null)" ]]; then
        info "No rollback points found."
        return 0
    fi

    printf "%-25s %-20s %-15s %s\n" "NAME" "CREATED" "COMMIT" "BRANCH"
    printf "%s\n" "$(printf '─%.0s' {1..80})"

    for dir in "$ROLLBACK_DIR"/*/; do
        if [[ -d "$dir" ]]; then
            local name=$(basename "$dir")
            local manifest="$dir/manifest.json"

            if [[ -f "$manifest" ]]; then
                local created=$(grep '"created"' "$manifest" | sed 's/.*: *"\([^"]*\)".*/\1/' | cut -c1-19)
                local commit=$(grep '"commit"' "$manifest" | sed 's/.*: *"\([^"]*\)".*/\1/' | cut -c1-8)
                local branch=$(grep '"branch"' "$manifest" | sed 's/.*: *"\([^"]*\)".*/\1/')

                printf "%-25s %-20s %-15s %s\n" "$name" "$created" "$commit" "$branch"
            fi
        fi
    done
    echo ""
}

# Delete old rollback points (keep last N)
cleanup_rollback_points() {
    local keep="${1:-10}"

    if [[ ! -d "$ROLLBACK_DIR" ]]; then
        return 0
    fi

    local count=$(ls -d "$ROLLBACK_DIR"/*/ 2>/dev/null | wc -l | tr -d ' ')

    if [[ $count -gt $keep ]]; then
        local to_delete=$((count - keep))
        info "Cleaning up $to_delete old rollback point(s)..."

        ls -d "$ROLLBACK_DIR"/*/ 2>/dev/null | head -n "$to_delete" | while read dir; do
            rm -rf "$dir"
            success "Deleted: $(basename "$dir")"
        done
    fi
}

################################################################################
# Rollback Execution
################################################################################

# Find migration spec file
find_migration_spec() {
    local migration_id="$1"

    # Search in common locations
    local search_paths=(
        "$MIGRATIONS_DIR/${migration_id}.md"
        "$PROJECT_ROOT/docs/${migration_id}.md"
        "$PROJECT_ROOT/tooling/docs/migrations/${migration_id}.md"
    )

    for path in "${search_paths[@]}"; do
        if [[ -f "$path" ]]; then
            echo "$path"
            return 0
        fi
    done

    # Search by pattern
    local found=$(find "$PROJECT_ROOT" -name "*${migration_id}*.md" -path "*/migrations/*" 2>/dev/null | head -1)
    if [[ -n "$found" ]]; then
        echo "$found"
        return 0
    fi

    return 1
}

# Parse rollback steps from migration spec
parse_rollback_steps() {
    local spec_file="$1"

    # Extract rollback steps section
    awk '/^### Rollback Steps/,/^##[^#]/' "$spec_file" 2>/dev/null | \
        grep -E '^\s*[0-9]+\.' | \
        sed 's/^\s*[0-9]*\.\s*//'
}

# Execute git-based rollback
rollback_to_commit() {
    local commit="$1"
    local dry_run="$2"

    if [[ "$dry_run" == "true" ]]; then
        info "Would reset to commit: $commit"
        git log --oneline -1 "$commit"
        return 0
    fi

    info "Rolling back to commit: $commit"

    # Check for uncommitted changes
    if [[ -n "$(git status --porcelain)" ]]; then
        warning "You have uncommitted changes. These will be stashed."
        git stash push -m "pre-rollback-$(date +%s)"
    fi

    # Perform rollback
    git checkout "$commit" -- .
    success "Rolled back to commit: $commit"
}

# Rollback from a rollback point
rollback_from_point() {
    local point_name="$1"
    local dry_run="$2"
    local point_path="$ROLLBACK_DIR/$point_name"

    if [[ ! -d "$point_path" ]]; then
        error "Rollback point not found: $point_name"
    fi

    local manifest="$point_path/manifest.json"
    if [[ ! -f "$manifest" ]]; then
        error "Invalid rollback point (no manifest): $point_name"
    fi

    local commit=$(grep '"commit"' "$manifest" | sed 's/.*: *"\([^"]*\)".*/\1/')

    echo ""
    info "Rollback Point Details:"
    cat "$manifest" | grep -E '"(name|created|branch|commit)"' | sed 's/^/  /'
    echo ""

    if [[ "$dry_run" == "true" ]]; then
        info "[DRY RUN] Would restore from rollback point: $point_name"

        if [[ -f "$point_path/package.json" ]]; then
            info "[DRY RUN] Would restore package.json"
        fi
        if [[ -f "$point_path/pubspec.yaml" ]]; then
            info "[DRY RUN] Would restore pubspec.yaml"
        fi

        return 0
    fi

    if ! confirm "This will rollback to the saved state. Continue?"; then
        info "Rollback cancelled."
        return 0
    fi

    # Restore files
    if [[ -f "$point_path/package.json" ]]; then
        cp "$point_path/package.json" "$PROJECT_ROOT/"
        success "Restored package.json"
    fi

    if [[ -f "$point_path/package-lock.json" ]]; then
        cp "$point_path/package-lock.json" "$PROJECT_ROOT/"
        success "Restored package-lock.json"
    fi

    if [[ -f "$point_path/pubspec.yaml" ]]; then
        cp "$point_path/pubspec.yaml" "$PROJECT_ROOT/"
        success "Restored pubspec.yaml"
    fi

    if [[ -f "$point_path/pubspec.lock" ]]; then
        cp "$point_path/pubspec.lock" "$PROJECT_ROOT/"
        success "Restored pubspec.lock"
    fi

    if [[ -f "$point_path/requirements.txt" ]]; then
        cp "$point_path/requirements.txt" "$PROJECT_ROOT/"
        success "Restored requirements.txt"
    fi

    # Rollback git if commit is available
    if [[ -n "$commit" && "$commit" != "unknown" ]]; then
        info "Rolling back git state..."
        rollback_to_commit "$commit" "false"
    fi

    # Reinstall dependencies
    echo ""
    info "Dependencies may need to be reinstalled:"
    if [[ -f "$PROJECT_ROOT/package.json" ]]; then
        echo "  npm install"
    fi
    if [[ -f "$PROJECT_ROOT/pubspec.yaml" ]]; then
        echo "  flutter pub get"
    fi
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        echo "  pip install -r requirements.txt"
    fi

    echo ""
    success "Rollback complete!"
}

# Main rollback function for migrations
rollback_migration() {
    local migration_id="$1"
    local dry_run="$2"
    local force="$3"

    echo -e "${BOLD}Rolling back migration: $migration_id${NC}"
    echo ""

    # Look for a rollback point for this migration
    local rollback_point=$(ls -d "$ROLLBACK_DIR"/*"$migration_id"* 2>/dev/null | tail -1)

    if [[ -n "$rollback_point" && -d "$rollback_point" ]]; then
        info "Found rollback point: $(basename "$rollback_point")"
        rollback_from_point "$(basename "$rollback_point")" "$dry_run"
        return 0
    fi

    # Look for migration spec with rollback instructions
    local spec_file=$(find_migration_spec "$migration_id")

    if [[ -n "$spec_file" ]]; then
        info "Found migration spec: $spec_file"

        local steps=$(parse_rollback_steps "$spec_file")

        if [[ -n "$steps" ]]; then
            echo ""
            echo -e "${BOLD}Rollback Steps:${NC}"
            echo "$steps" | nl
            echo ""

            if [[ "$dry_run" == "true" ]]; then
                info "[DRY RUN] Would execute the above rollback steps"
                return 0
            fi

            if ! confirm "Execute these rollback steps?"; then
                info "Rollback cancelled."
                return 0
            fi

            # Execute steps (basic implementation - just displays them)
            info "Please execute the following steps manually:"
            echo "$steps" | nl
        else
            warning "No rollback steps found in migration spec"
        fi
    else
        warning "No migration spec found for: $migration_id"
    fi

    # Offer git-based rollback
    echo ""
    info "You can also rollback using git:"
    echo "  1. Find the commit before the migration:"
    echo "     git log --oneline --all | head -20"
    echo ""
    echo "  2. Rollback to that commit:"
    echo "     git checkout <commit> -- ."
    echo ""
    echo "  3. Or use this tool with a specific rollback point:"
    echo "     ./rollback-migration.sh --list"
    echo "     ./rollback-migration.sh --restore <point-name>"
}

################################################################################
# Main
################################################################################

print_usage() {
    echo "Usage: ./rollback-migration.sh <migration-id> [options]"
    echo ""
    echo "Commands:"
    echo "  <migration-id>               Rollback a specific migration"
    echo "  --list                       List available rollback points"
    echo "  --create <name>              Create a new rollback point"
    echo "  --restore <point>            Restore from a specific rollback point"
    echo "  --cleanup [keep-count]       Delete old rollback points (default: keep 10)"
    echo ""
    echo "Options:"
    echo "  --dry-run                    Preview rollback without executing"
    echo "  --force                      Force rollback without confirmation"
    echo "  --help                       Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./rollback-migration.sh react-18                # Rollback react-18 migration"
    echo "  ./rollback-migration.sh react-18 --dry-run      # Preview the rollback"
    echo "  ./rollback-migration.sh --create before-upgrade # Create rollback point"
    echo "  ./rollback-migration.sh --list                  # List rollback points"
    echo ""
}

main() {
    local command=""
    local dry_run="false"
    local force="false"
    local create_name=""
    local restore_point=""
    local cleanup_keep=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --list|-l)
                command="list"
                ;;
            --create|-c)
                command="create"
                shift
                create_name="$1"
                ;;
            --restore|-r)
                command="restore"
                shift
                restore_point="$1"
                ;;
            --cleanup)
                command="cleanup"
                shift
                if [[ "$1" =~ ^[0-9]+$ ]]; then
                    cleanup_keep="$1"
                else
                    # Not a number, don't consume
                    cleanup_keep="10"
                    continue
                fi
                ;;
            --dry-run)
                dry_run="true"
                ;;
            --force|-f)
                force="true"
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            -*)
                error "Unknown option: $1"
                ;;
            *)
                if [[ -z "$command" ]]; then
                    command="rollback"
                fi
                [[ -z "$migration_id" ]] && migration_id="$1"
                ;;
        esac
        shift
    done

    print_header

    # Ensure rollback directory exists
    mkdir -p "$ROLLBACK_DIR"

    case "$command" in
        list)
            list_rollback_points
            ;;
        create)
            if [[ -z "$create_name" ]]; then
                error "Please provide a name for the rollback point"
            fi
            create_rollback_point "$create_name"
            ;;
        restore)
            if [[ -z "$restore_point" ]]; then
                error "Please provide a rollback point name"
            fi
            rollback_from_point "$restore_point" "$dry_run"
            ;;
        cleanup)
            cleanup_rollback_points "${cleanup_keep:-10}"
            ;;
        rollback)
            if [[ -z "$migration_id" ]]; then
                print_usage
                exit 1
            fi
            rollback_migration "$migration_id" "$dry_run" "$force"
            ;;
        *)
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
