#!/usr/bin/env bash
################################################################################
# Checkpoint Integration Library
#
# Functions to integrate context checkpointing into existing automation workflows
################################################################################

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHECKPOINT_SCRIPT="$PROJECT_ROOT/tooling/scripts/context_checkpoint.py"
CHECKPOINT_DIR="$PROJECT_ROOT/tooling/.automation/checkpoints"

################################################################################
# Start checkpoint monitor in background
################################################################################
start_checkpoint_monitor() {
    local log_file="$1"
    local session_id="${2:-auto}"

    if [[ ! -f "$CHECKPOINT_SCRIPT" ]]; then
        echo "  Checkpoint script not found, skipping monitoring"
        return 1
    fi

    echo " Starting context checkpoint monitor..."
    echo "   Watching: $log_file"

    # Start monitor in background
    python3 "$CHECKPOINT_SCRIPT" \
        --watch-log "$log_file" \
        --session-id "$session_id" \
        2>&1 > /dev/null &

    local monitor_pid=$!
    echo "$monitor_pid" > "${log_file}.checkpoint.pid"

    echo " Checkpoint monitor started (PID: $monitor_pid)"
    return 0
}

################################################################################
# Stop checkpoint monitor
################################################################################
stop_checkpoint_monitor() {
    local log_file="$1"
    local pid_file="${log_file}.checkpoint.pid"

    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo " Stopping checkpoint monitor (PID: $pid)"
            kill "$pid" 2>/dev/null || true
            rm -f "$pid_file"
            echo " Checkpoint monitor stopped"
        else
            rm -f "$pid_file"
        fi
    fi
}

################################################################################
# Create manual checkpoint with context
################################################################################
create_story_checkpoint() {
    local story_key="$1"
    local reason="${2:-manual}"

    echo " Creating checkpoint for story: $story_key"

    python3 "$CHECKPOINT_SCRIPT" \
        --checkpoint \
        --session-id "$story_key" \
        2>&1

    return $?
}

################################################################################
# Check if checkpoint exists for story
################################################################################
has_checkpoint() {
    local story_key="$1"

    local checkpoints=$(find "$CHECKPOINT_DIR" -name "*${story_key}*.json" 2>/dev/null)

    if [[ -n "$checkpoints" ]]; then
        return 0
    else
        return 1
    fi
}

################################################################################
# Get latest checkpoint for story
################################################################################
get_latest_checkpoint() {
    local story_key="$1"

    find "$CHECKPOINT_DIR" -name "*${story_key}*.json" 2>/dev/null | \
        sort -r | \
        head -1
}

################################################################################
# Resume from latest checkpoint
################################################################################
resume_from_checkpoint() {
    local story_key="$1"

    local checkpoint_file=$(get_latest_checkpoint "$story_key")

    if [[ -z "$checkpoint_file" ]]; then
        echo " No checkpoint found for story: $story_key"
        return 1
    fi

    local checkpoint_id=$(basename "$checkpoint_file" .json)

    echo " Resuming from checkpoint: $checkpoint_id"

    python3 "$CHECKPOINT_SCRIPT" \
        --resume "$checkpoint_id"

    return $?
}

################################################################################
# Clean up old checkpoints (keep last N)
################################################################################
cleanup_old_checkpoints() {
    local keep_count="${1:-10}"

    echo " Cleaning up old checkpoints (keeping last $keep_count)..."

    local checkpoints=$(find "$CHECKPOINT_DIR" -name "checkpoint_*.json" | sort -r)
    local total=$(echo "$checkpoints" | wc -l | tr -d ' ')

    if [[ $total -le $keep_count ]]; then
        echo " No cleanup needed ($total checkpoints)"
        return 0
    fi

    local to_delete=$(echo "$checkpoints" | tail -n +$((keep_count + 1)))
    local delete_count=$(echo "$to_delete" | wc -l | tr -d ' ')

    echo "$to_delete" | while read -r file; do
        local summary_file="${file%.json}_summary.md"
        rm -f "$file" "$summary_file"
    done

    echo " Deleted $delete_count old checkpoints"
}

################################################################################
# Add checkpoint info to log
################################################################################
log_checkpoint_info() {
    local log_file="$1"

    cat >> "$log_file" <<EOF

═══════════════════════════════════════════════════════════════
  CONTEXT CHECKPOINT MONITORING ACTIVE
═══════════════════════════════════════════════════════════════

Thresholds:
   Warning:   75% - Log notification
    Critical:  85% - Auto-checkpoint created
   Emergency: 95% - Force checkpoint + alert

Checkpoint directory: $CHECKPOINT_DIR

To manually checkpoint: ./tooling/scripts/checkpoint --checkpoint
To list checkpoints:    ./tooling/scripts/checkpoint --list

═══════════════════════════════════════════════════════════════

EOF
}

################################################################################
# Export functions
################################################################################
export -f start_checkpoint_monitor
export -f stop_checkpoint_monitor
export -f create_story_checkpoint
export -f has_checkpoint
export -f get_latest_checkpoint
export -f resume_from_checkpoint
export -f cleanup_old_checkpoints
export -f log_checkpoint_info
