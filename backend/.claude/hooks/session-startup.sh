#!/bin/bash
# Devflow Session Startup Hook
# Automatically loads plans and context when Claude Code starts

# Read input from Claude Code (contains model info)
INPUT=$(cat)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TRACKER="$PROJECT_DIR/.claude/hooks/session_tracker.py"
PLANS_DIR="$PROJECT_DIR/.claude/plans"
SESSIONS_DIR="$PROJECT_DIR/tooling/.automation/costs/sessions"
MEMORY_DIR="$PROJECT_DIR/tooling/.automation/memory"
CONTEXT_DIR="$PROJECT_DIR/tooling/.automation/context"
COST_CONFIG="$PROJECT_DIR/tooling/.automation/costs/config.json"

# Ensure plans directory exists
mkdir -p "$PLANS_DIR" 2>/dev/null

# Start session tracking
MODEL_NAME=$(echo "$INPUT" | jq -r '.model.name // .model // ""' 2>/dev/null)
if [ -n "$MODEL_NAME" ] && [ "$MODEL_NAME" != "null" ]; then
    python3 "$TRACKER" start --model "$MODEL_NAME" 2>/dev/null
else
    python3 "$TRACKER" start 2>/dev/null
fi

echo "[DEVFLOW SESSION START]"
echo ""

# ============================================================================
# CUMULATIVE USAGE DISPLAY
# ============================================================================

calc_cumulative_usage() {
    local billing_period=${1:-30}
    local total_tokens=0
    local total_cost=0
    local session_count=0

    if [ -d "$SESSIONS_DIR" ]; then
        CUTOFF_DATE=$(date -v-${billing_period}d +%Y-%m-%d 2>/dev/null || date -d "-${billing_period} days" +%Y-%m-%d 2>/dev/null)

        for session_file in "$SESSIONS_DIR"/*.json; do
            [ -f "$session_file" ] || continue
            FILE_DATE=$(basename "$session_file" | cut -d'_' -f1)

            if [[ "$FILE_DATE" > "$CUTOFF_DATE" ]] || [[ "$FILE_DATE" == "$CUTOFF_DATE" ]]; then
                SESSION_TOKENS=$(jq -r '.totals.total_tokens // 0' "$session_file" 2>/dev/null)
                SESSION_COST=$(jq -r '.totals.cost_usd // 0' "$session_file" 2>/dev/null)

                total_tokens=$((total_tokens + SESSION_TOKENS))
                total_cost=$(echo "$total_cost + $SESSION_COST" | bc 2>/dev/null || echo "$total_cost")
                session_count=$((session_count + 1))
            fi
        done
    fi

    echo "$total_tokens|$total_cost|$session_count"
}

# Get cumulative usage
CUMULATIVE=$(calc_cumulative_usage 30)
CUM_TOKENS=$(echo "$CUMULATIVE" | cut -d'|' -f1)
CUM_COST=$(echo "$CUMULATIVE" | cut -d'|' -f2)
CUM_SESSIONS=$(echo "$CUMULATIVE" | cut -d'|' -f3)

# Add baseline to cumulative
BASELINE_TOKENS=$(jq -r '.baseline_tokens // 0' "$COST_CONFIG" 2>/dev/null)
BASELINE_COST=$(jq -r '.baseline_cost // 0' "$COST_CONFIG" 2>/dev/null)
CUM_TOKENS=$((CUM_TOKENS + BASELINE_TOKENS))
CUM_COST=$(echo "$CUM_COST + $BASELINE_COST" | bc 2>/dev/null || echo "$CUM_COST")

# Format tokens for display
format_tokens() {
    local tokens=$1
    if [ "$tokens" -ge 1000000 ] 2>/dev/null; then
        echo "$(echo "scale=1; $tokens / 1000000" | bc 2>/dev/null || echo "$tokens")M"
    elif [ "$tokens" -ge 1000 ] 2>/dev/null; then
        echo "$(echo "scale=1; $tokens / 1000" | bc 2>/dev/null || echo "$tokens")K"
    else
        echo "$tokens"
    fi
}

CUM_TOKENS_FMT=$(format_tokens "$CUM_TOKENS")
CUM_COST_FMT=$(printf "%.2f" "$CUM_COST" 2>/dev/null || echo "$CUM_COST")

if [ "$CUM_SESSIONS" -gt 0 ] 2>/dev/null; then
    echo "[CUMULATIVE USAGE] Last 30 days: ${CUM_TOKENS_FMT} tokens | \$${CUM_COST_FMT} | ${CUM_SESSIONS} sessions"
    echo ""
fi

# ============================================================================
# SUBSCRIPTION PLAN DETECTION
# ============================================================================

# Extract model from input
MODEL=$(echo "$INPUT" | jq -r '.model.display_name // .model.name // .model // ""' 2>/dev/null)

# Token limits by plan
get_token_limit() {
    case "$1" in
        free) echo 100000 ;;
        developer) echo 1000000 ;;
        pro) echo 5000000 ;;
        scale) echo 20000000 ;;
        enterprise) echo 100000000 ;;
        *) echo 1000000 ;;
    esac
}

# Detect plan from model
detect_plan_from_model() {
    local model_lower=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    case "$model_lower" in
        *opus*) echo "pro" ;;
        *sonnet*) echo "developer" ;;
        *haiku*) echo "free" ;;
        *) echo "developer" ;;
    esac
}

# Ensure config directory exists
mkdir -p "$(dirname "$COST_CONFIG")" 2>/dev/null

# Check if config exists, create if not
if [ ! -f "$COST_CONFIG" ]; then
    echo '{"display_currency": "USD", "currency_rates": {"USD": 1.0}}' > "$COST_CONFIG"
fi

# Read current plan from config
CURRENT_PLAN=$(jq -r '.subscription_plan // ""' "$COST_CONFIG" 2>/dev/null)

# Detect plan based on model if not already configured
if [ -z "$CURRENT_PLAN" ] && [ -n "$MODEL" ]; then
    DETECTED_PLAN=$(detect_plan_from_model "$MODEL")
    TOKEN_LIMIT=$(get_token_limit "$DETECTED_PLAN")

    # Save to config
    TMP_CONFIG=$(mktemp)
    jq --arg plan "$DETECTED_PLAN" --argjson limit "$TOKEN_LIMIT" \
        '.subscription_plan = $plan | .subscription_token_limit = $limit' \
        "$COST_CONFIG" > "$TMP_CONFIG" 2>/dev/null && \
        mv "$TMP_CONFIG" "$COST_CONFIG" 2>/dev/null || rm -f "$TMP_CONFIG"

    CURRENT_PLAN="$DETECTED_PLAN"
    echo "[SUBSCRIPTION] Auto-detected plan: $DETECTED_PLAN ($(get_token_limit "$DETECTED_PLAN" | numfmt --to=si 2>/dev/null || echo "$(get_token_limit "$DETECTED_PLAN")") tokens/month)"
    echo ""
elif [ -n "$CURRENT_PLAN" ]; then
    TOKEN_LIMIT=$(jq -r '.subscription_token_limit // 0' "$COST_CONFIG" 2>/dev/null)
    if [ "$TOKEN_LIMIT" -gt 0 ] 2>/dev/null; then
        # Calculate current usage
        BILLING_PERIOD=$(jq -r '.subscription_billing_period_days // 30' "$COST_CONFIG" 2>/dev/null)
        CUTOFF_DATE=$(date -v-${BILLING_PERIOD}d +%Y-%m-%d 2>/dev/null || date -d "-${BILLING_PERIOD} days" +%Y-%m-%d 2>/dev/null)

        TOTAL_TOKENS=0
        if [ -d "$SESSIONS_DIR" ]; then
            for session_file in "$SESSIONS_DIR"/*.json; do
                [ -f "$session_file" ] || continue
                FILE_DATE=$(basename "$session_file" | cut -d'_' -f1)
                if [[ "$FILE_DATE" > "$CUTOFF_DATE" ]] || [[ "$FILE_DATE" == "$CUTOFF_DATE" ]]; then
                    SESSION_TOKENS=$(jq -r '.totals.total_tokens // 0' "$session_file" 2>/dev/null)
                    TOTAL_TOKENS=$((TOTAL_TOKENS + SESSION_TOKENS))
                fi
            done
        fi

        USAGE_PERCENT=$(echo "scale=1; ($TOTAL_TOKENS * 100) / $TOKEN_LIMIT" | bc 2>/dev/null || echo "0")
        echo "[SUBSCRIPTION] Plan: $CURRENT_PLAN | Usage: ${USAGE_PERCENT}% of $(echo "$TOKEN_LIMIT" | numfmt --to=si 2>/dev/null || echo "$TOKEN_LIMIT") tokens"
        echo ""
    fi
fi

# ============================================================================
# BASELINE USAGE SETUP (First-time only)
# ============================================================================

setup_baseline() {
    # Check if baseline has been configured
    BASELINE_CONFIGURED=$(jq -r '.baseline_configured // false' "$COST_CONFIG" 2>/dev/null)

    if [ "$BASELINE_CONFIGURED" = "true" ]; then
        return 0
    fi

    # Check if we have a real interactive terminal
    # Hooks run non-interactively, so we auto-configure with defaults
    if [ ! -t 0 ] || [ -z "$(tty 2>/dev/null)" ] || [ "$(tty 2>/dev/null)" = "not a tty" ]; then
        # Non-interactive: auto-configure with defaults
        BASELINE_TOKENS=0
        BASELINE_COST=0

        # Save to config
        TMP_CONFIG=$(mktemp)
        jq --argjson tokens "$BASELINE_TOKENS" \
           --argjson cost "$BASELINE_COST" \
           --argjson configured true \
           '.baseline_tokens = $tokens | .baseline_cost = $cost | .baseline_configured = $configured' \
           "$COST_CONFIG" > "$TMP_CONFIG" 2>/dev/null && \
           mv "$TMP_CONFIG" "$COST_CONFIG" 2>/dev/null || rm -f "$TMP_CONFIG"

        echo "[OK] Baseline auto-configured (starting fresh). Run 'devflow baseline' to adjust."
        return 0
    fi

    echo ""
    echo "============================================================"
    echo "  USAGE TRACKING SETUP"
    echo "============================================================"
    echo ""
    echo "Devflow tracks your Claude Code usage across sessions."
    echo "Since this is your first time, we need to set a baseline."
    echo ""
    echo "Options:"
    echo "  1) Start fresh - Begin tracking from 0 (recommended for new billing periods)"
    echo "  2) Set baseline - Enter your current usage from Claude Console"
    echo ""

    # Read user choice with timeout to prevent hanging
    if read -r -t 5 -p "Choose an option [1/2]: " choice </dev/tty 2>/dev/null; then
        case "$choice" in
            2)
                echo ""
                echo "Enter your current token usage (e.g., 500000 or 500K or 1.5M):"
                read -r -t 30 -p "Tokens: " token_input </dev/tty

                # Parse token input (handle K/M suffixes)
                BASELINE_TOKENS=$(echo "$token_input" | awk '{
                    gsub(/,/, "");
                    if (tolower($0) ~ /m$/) { gsub(/[mM]/, ""); print int($0 * 1000000) }
                    else if (tolower($0) ~ /k$/) { gsub(/[kK]/, ""); print int($0 * 1000) }
                    else { print int($0) }
                }')

                echo "Enter your current cost (e.g., 5.50):"
                read -r -t 30 -p "Cost $: " cost_input </dev/tty
                BASELINE_COST=$(echo "$cost_input" | sed 's/[$,]//g')

                echo ""
                echo "Setting baseline: ${BASELINE_TOKENS} tokens, \$${BASELINE_COST}"
                ;;
            *)
                BASELINE_TOKENS=0
                BASELINE_COST=0
                echo ""
                echo "Starting fresh with 0 baseline."
                ;;
        esac
    else
        # Timeout or no input - use defaults
        BASELINE_TOKENS=0
        BASELINE_COST=0
        echo ""
        echo "Starting fresh with 0 baseline (timeout)."
    fi

    # Save to config
    TMP_CONFIG=$(mktemp)
    jq --argjson tokens "$BASELINE_TOKENS" \
       --argjson cost "$BASELINE_COST" \
       --argjson configured true \
       '.baseline_tokens = $tokens | .baseline_cost = $cost | .baseline_configured = $configured' \
       "$COST_CONFIG" > "$TMP_CONFIG" 2>/dev/null && \
       mv "$TMP_CONFIG" "$COST_CONFIG" 2>/dev/null || rm -f "$TMP_CONFIG"

    echo ""
    echo "[OK] Baseline configured. Your cumulative usage will now include this baseline."
    echo "============================================================"
    echo ""
}

# Always run setup_baseline - it handles non-interactive mode internally
setup_baseline

# Check for active plans (multiple locations)
detect_plans() {
    local found_plans=()
    local plan_details=()

    # Location 1: Devflow plans directory
    if [ -d "$PLANS_DIR" ]; then
        while IFS= read -r -d '' plan; do
            found_plans+=("$plan")
            name=$(basename "$plan" .md)
            # Get first line as description
            desc=$(head -1 "$plan" 2>/dev/null | sed 's/^#* *//' | cut -c1-50)
            plan_details+=("$name: $desc")
        done < <(find "$PLANS_DIR" -name "*.md" -type f -print0 2>/dev/null)
    fi

    # Location 2: Claude Code plan files (look for plan.md or PLAN.md in project)
    for plan_file in "$PROJECT_DIR/plan.md" "$PROJECT_DIR/PLAN.md" "$PROJECT_DIR/.claude/plan.md"; do
        if [ -f "$plan_file" ]; then
            found_plans+=("$plan_file")
            name=$(basename "$plan_file" .md)
            desc=$(head -1 "$plan_file" 2>/dev/null | sed 's/^#* *//' | cut -c1-50)
            plan_details+=("$name: $desc")
        fi
    done

    # Location 3: Check for recent plan mode files (Claude Code creates these)
    if [ -d "$PROJECT_DIR/.claude" ]; then
        while IFS= read -r -d '' plan; do
            # Avoid duplicates
            if [[ ! " ${found_plans[*]} " =~ " ${plan} " ]]; then
                found_plans+=("$plan")
                name=$(basename "$plan" .md)
                modified=$(stat -f "%Sm" -t "%Y-%m-%d" "$plan" 2>/dev/null || stat -c "%y" "$plan" 2>/dev/null | cut -d' ' -f1)
                plan_details+=("$name ($modified)")
            fi
        done < <(find "$PROJECT_DIR/.claude" -maxdepth 2 -name "*plan*.md" -type f -print0 2>/dev/null)
    fi

    # Output results
    local count=${#found_plans[@]}
    if [ "$count" -gt 0 ]; then
        echo "[PLANS] Found $count plan(s):"
        for detail in "${plan_details[@]}"; do
            echo "  - $detail"
        done
        echo ""
    else
        echo "[PLANS] No saved plans found"
        echo ""
    fi
}

detect_plans

# Check for recent sessions
if [ -d "$SESSIONS_DIR" ]; then
    recent=$(ls -t "$SESSIONS_DIR" 2>/dev/null | head -1)
    if [ -n "$recent" ]; then
        echo "[SESSIONS] Most recent session: $recent"
        # Try to extract story key from session file
        if command -v jq >/dev/null 2>&1; then
            if [ -f "$SESSIONS_DIR/$recent" ]; then
                story_key=$(jq -r '.story_key // empty' "$SESSIONS_DIR/$recent" 2>/dev/null)
                if [ -n "$story_key" ]; then
                    echo "  Story: $story_key"
                fi
            fi
        fi
        echo ""
    fi
fi

# Check for shared memory/knowledge
if [ -d "$MEMORY_DIR/shared" ]; then
    count=$(find "$MEMORY_DIR/shared" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
        echo "[MEMORY] $count shared memory file(s) available"
        echo "  Use /memory to view knowledge graph"
        echo ""
    fi
fi

# Check for context state
if [ -d "$CONTEXT_DIR" ]; then
    ctx_count=$(find "$CONTEXT_DIR" -name "context_*.json" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$ctx_count" -gt 0 ]; then
        echo "[CONTEXT] Previous context state available"
        find "$CONTEXT_DIR" -name "context_*.json" -type f 2>/dev/null | while read -r ctx; do
            name=$(basename "$ctx" .json | sed 's/context_//')
            if command -v jq >/dev/null 2>&1; then
                usage=$(jq -r '.estimated_context_tokens // 0' "$ctx" 2>/dev/null)
                if [ "$usage" != "0" ] && [ -n "$usage" ]; then
                    echo "  - $name: ~$usage tokens"
                fi
            else
                echo "  - $name"
            fi
        done
        echo ""
    fi
fi

# ============================================================================
# STATUS BAR PREVIEW
# ============================================================================

# Build status bar preview
STATUS_BAR=""

# Extract model from input
MODEL=$(echo "$INPUT" | jq -r '.model.display_name // .model.name // .model // "Unknown"' 2>/dev/null)

# Get subscription info
if [ -f "$COST_CONFIG" ]; then
    SUB_PLAN=$(jq -r '.subscription_plan // ""' "$COST_CONFIG" 2>/dev/null)
    TOKEN_LIMIT=$(jq -r '.subscription_token_limit // 0' "$COST_CONFIG" 2>/dev/null)

    if [ -n "$SUB_PLAN" ] && [ "$TOKEN_LIMIT" -gt 0 ] 2>/dev/null; then
        USAGE_PCT=$(echo "scale=1; ($CUM_TOKENS * 100) / $TOKEN_LIMIT" | bc 2>/dev/null || echo "0")

        # Color based on usage
        if (( $(echo "$USAGE_PCT >= 90" | bc -l 2>/dev/null || echo 0) )); then
            COLOR="\033[31m"  # Red
        elif (( $(echo "$USAGE_PCT >= 75" | bc -l 2>/dev/null || echo 0) )); then
            COLOR="\033[33m"  # Yellow
        else
            COLOR="\033[32m"  # Green
        fi
        RESET="\033[0m"

        TOKEN_LIMIT_FMT=$(format_tokens "$TOKEN_LIMIT")
        STATUS_BAR="[Devflow] $MODEL | ${COLOR}Usage: ${USAGE_PCT}% (${CUM_TOKENS_FMT}/${TOKEN_LIMIT_FMT})${RESET} | Cost: \$${CUM_COST_FMT}"
    else
        STATUS_BAR="[Devflow] $MODEL | Tokens: ${CUM_TOKENS_FMT} | Cost: \$${CUM_COST_FMT}"
    fi
else
    STATUS_BAR="[Devflow] $MODEL | Tokens: ${CUM_TOKENS_FMT} | Cost: \$${CUM_COST_FMT}"
fi

echo "---"
echo -e "$STATUS_BAR"
echo "---"
echo ""

# Quick tips
echo "[QUICK START]"
echo "  /story <key>  - Run full story pipeline"
echo "  /develop      - Development phase only"
echo "  /review       - Code review only"
echo "  /costs        - View cost dashboard"

# ============================================================================
# AUTO-LAUNCH LIVE DASHBOARD
# ============================================================================

DASHBOARD_SCRIPT="$PROJECT_DIR/tooling/scripts/live_dashboard.py"

if [ -f "$DASHBOARD_SCRIPT" ]; then
    # Launch dashboard in a new terminal window (macOS)
    if [ "$(uname)" = "Darwin" ]; then
        osascript -e "tell application \"Terminal\"
            do script \"cd '$PROJECT_DIR' && python3 '$DASHBOARD_SCRIPT' --compact\"
        end tell" >/dev/null 2>&1 &
    # Linux with common terminal emulators
    elif command -v gnome-terminal >/dev/null 2>&1; then
        gnome-terminal -- bash -c "cd '$PROJECT_DIR' && python3 '$DASHBOARD_SCRIPT'; exec bash" >/dev/null 2>&1 &
    elif command -v xterm >/dev/null 2>&1; then
        xterm -e "cd '$PROJECT_DIR' && python3 '$DASHBOARD_SCRIPT'" >/dev/null 2>&1 &
    fi
fi

exit 0
