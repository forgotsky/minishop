#!/bin/bash
# Session Stop Hook - Saves session cost data when Claude Code stops

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TRACKER="$PROJECT_DIR/.claude/hooks/session_tracker.py"

# Read input from Claude Code (contains stop reason, transcript summary)
INPUT=$(cat)

# Extract token info if available from the stop event
# The stop event may contain usage statistics
INPUT_TOKENS=$(echo "$INPUT" | jq -r '.usage.input_tokens // .transcript_summary.input_tokens // 0' 2>/dev/null)
OUTPUT_TOKENS=$(echo "$INPUT" | jq -r '.usage.output_tokens // .transcript_summary.output_tokens // 0' 2>/dev/null)
MODEL=$(echo "$INPUT" | jq -r '.model // ""' 2>/dev/null)

# Log final usage if we have token data
if [ "$INPUT_TOKENS" -gt 0 ] 2>/dev/null || [ "$OUTPUT_TOKENS" -gt 0 ] 2>/dev/null; then
    if [ -n "$MODEL" ]; then
        python3 "$TRACKER" log --input "$INPUT_TOKENS" --output "$OUTPUT_TOKENS" --model "$MODEL" 2>/dev/null
    else
        python3 "$TRACKER" log --input "$INPUT_TOKENS" --output "$OUTPUT_TOKENS" 2>/dev/null
    fi
fi

# End the session and save
RESULT=$(python3 "$TRACKER" end 2>/dev/null)

# Output summary if session had activity
SAVED=$(echo "$RESULT" | jq -r '.saved // false' 2>/dev/null)
TOKENS=$(echo "$RESULT" | jq -r '.total_tokens // 0' 2>/dev/null)
COST=$(echo "$RESULT" | jq -r '.cost_usd // 0' 2>/dev/null)

if [ "$SAVED" = "true" ] 2>/dev/null; then
    echo ""
    echo "[SESSION SAVED] Tokens: $TOKENS | Cost: \$$COST"
fi

exit 0
