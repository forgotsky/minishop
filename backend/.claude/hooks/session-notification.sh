#!/bin/bash
# Session Notification Hook - Captures token usage from Claude Code notifications

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TRACKER="$PROJECT_DIR/.claude/hooks/session_tracker.py"

# Read notification data from Claude Code
INPUT=$(cat)

# Try to extract token usage from notification
# Claude Code may send usage data in various formats
INPUT_TOKENS=$(echo "$INPUT" | jq -r '
    .usage.input_tokens //
    .data.usage.input_tokens //
    .message.usage.input_tokens //
    .input_tokens //
    0
' 2>/dev/null)

OUTPUT_TOKENS=$(echo "$INPUT" | jq -r '
    .usage.output_tokens //
    .data.usage.output_tokens //
    .message.usage.output_tokens //
    .output_tokens //
    0
' 2>/dev/null)

MODEL=$(echo "$INPUT" | jq -r '
    .model //
    .data.model //
    .message.model //
    ""
' 2>/dev/null)

# Only log if we have actual token data
if [ "$INPUT_TOKENS" -gt 0 ] 2>/dev/null || [ "$OUTPUT_TOKENS" -gt 0 ] 2>/dev/null; then
    if [ -n "$MODEL" ] && [ "$MODEL" != "null" ]; then
        python3 "$TRACKER" log --input "$INPUT_TOKENS" --output "$OUTPUT_TOKENS" --model "$MODEL" 2>/dev/null
    else
        python3 "$TRACKER" log --input "$INPUT_TOKENS" --output "$OUTPUT_TOKENS" 2>/dev/null
    fi
fi

exit 0
