#!/usr/bin/env bash
################################################################################
# Setup Checkpoint Service - macOS LaunchAgent
#
# Creates a background service that monitors Claude sessions for context warnings
# and automatically creates checkpoints.
################################################################################

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT_PATH="$PROJECT_ROOT/tooling/scripts/context_checkpoint.py"
PLIST_NAME="com.stronger.checkpoint"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG_DIR="$PROJECT_ROOT/tooling/.automation/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Context Checkpoint Service Setup${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN} $1${NC}"
}

print_error() {
    echo -e "${RED} $1${NC}"
}

print_info() {
    echo -e "${BLUE}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}  $1${NC}"
}

# Check if script exists
check_prerequisites() {
    print_info "Checking prerequisites..."

    if [[ ! -f "$SCRIPT_PATH" ]]; then
        print_error "Checkpoint script not found at: $SCRIPT_PATH"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi

    # Make script executable
    chmod +x "$SCRIPT_PATH"

    print_success "Prerequisites OK"
}

# Create LaunchAgent plist
create_plist() {
    print_info "Creating LaunchAgent plist..."

    mkdir -p "$HOME/Library/LaunchAgents"
    mkdir -p "$LOG_DIR"

    cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${SCRIPT_PATH}</string>
        <string>--watch-log</string>
        <string>${LOG_DIR}/current.log</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/checkpoint-service.log</string>

    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/checkpoint-service-error.log</string>

    <key>WorkingDirectory</key>
    <string>${PROJECT_ROOT}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>

    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

    print_success "Created plist at: $PLIST_PATH"
}

# Load service
load_service() {
    print_info "Loading service..."

    # Unload if already loaded
    launchctl unload "$PLIST_PATH" 2>/dev/null || true

    # Load the service
    if launchctl load "$PLIST_PATH"; then
        print_success "Service loaded successfully"
    else
        print_error "Failed to load service"
        return 1
    fi

    sleep 2

    # Check if running
    if launchctl list | grep -q "$PLIST_NAME"; then
        print_success "Service is running"
    else
        print_warning "Service loaded but not running"
    fi
}

# Create symlink for easy access
create_symlink() {
    print_info "Creating convenience command..."

    local bin_dir="$PROJECT_ROOT/tooling/scripts"
    local symlink="$bin_dir/checkpoint"

    # Create wrapper script
    cat > "$symlink" <<'EOF'
#!/bin/zsh
# Convenience wrapper for context checkpoint manager

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/context_checkpoint.py" "$@"
EOF

    chmod +x "$symlink"
    print_success "Created command: ./tooling/scripts/checkpoint"
}

# Print usage instructions
print_usage() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Setup Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "The context checkpoint service is now running in the background."
    echo ""
    echo -e "${BLUE}Service Management:${NC}"
    echo "  • Start:   launchctl load $PLIST_PATH"
    echo "  • Stop:    launchctl unload $PLIST_PATH"
    echo "  • Restart: launchctl kickstart -k gui/\$(id -u)/$PLIST_NAME"
    echo "  • Status:  launchctl list | grep $PLIST_NAME"
    echo ""
    echo -e "${BLUE}Logs:${NC}"
    echo "  • Service log:  $LOG_DIR/checkpoint-service.log"
    echo "  • Error log:    $LOG_DIR/checkpoint-service-error.log"
    echo "  • Checkpoints:  tooling/.automation/checkpoints/"
    echo ""
    echo -e "${BLUE}Quick Commands:${NC}"
    echo "  • Create checkpoint:  ./tooling/scripts/checkpoint --checkpoint"
    echo "  • List checkpoints:   ./tooling/scripts/checkpoint --list"
    echo "  • Resume session:     ./tooling/scripts/checkpoint --resume <id>"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. The service will monitor: $LOG_DIR/current.log"
    echo "  2. Update your automation to write to this log file"
    echo "  3. Watch for automatic checkpoints when context gets high"
    echo ""
}

# Uninstall function
uninstall() {
    print_info "Uninstalling checkpoint service..."

    # Unload service
    launchctl unload "$PLIST_PATH" 2>/dev/null || true

    # Remove plist
    rm -f "$PLIST_PATH"

    print_success "Service uninstalled"
}

# Main
main() {
    print_header

    case "${1:-install}" in
        install)
            check_prerequisites
            create_plist
            create_symlink
            load_service
            print_usage
            ;;
        uninstall)
            uninstall
            ;;
        *)
            echo "Usage: $0 [install|uninstall]"
            exit 1
            ;;
    esac
}

main "$@"
