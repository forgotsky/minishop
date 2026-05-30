#!/usr/bin/env bash
################################################################################
# Claude CLI Integration Library
#
# Wrapper functions for invoking Claude Code CLI to execute workflows
# Uses the actual Claude Code CLI syntax
################################################################################

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AUTOMATION_DIR="$PROJECT_ROOT/.automation"
AGENTS_DIR="$AUTOMATION_DIR/agents"
LOGS_DIR="$AUTOMATION_DIR/logs"
STORIES_DIR="$PROJECT_ROOT/docs"

# Source dependencies
source "$SCRIPT_DIR/session-manager.sh" 2>/dev/null || true
source "$SCRIPT_DIR/track-tokens.sh" 2>/dev/null || true
source "$SCRIPT_DIR/context-monitor.sh" 2>/dev/null || true
source "$SCRIPT_DIR/checkpoint-integration.sh" 2>/dev/null || true
source "$SCRIPT_DIR/override-loader.sh" 2>/dev/null || true

# Claude CLI path
CLAUDE_CLI="${CLAUDE_CLI:-claude}"

# Default model (can be overridden)
CLAUDE_MODEL="${CLAUDE_MODEL:-sonnet}"

# Permission mode for automation (bypasses interactive permission prompts)
# Options: "default", "acceptEdits", "bypassPermissions", "plan", "dangerouslySkipPermissions"
PERMISSION_MODE="${PERMISSION_MODE:-dangerouslySkipPermissions}"

# Build permission flags based on mode
get_permission_flags() {
    case "$PERMISSION_MODE" in
        "dangerouslySkipPermissions"|"skip")
            echo "--dangerously-skip-permissions"
            ;;
        *)
            echo "--permission-mode $PERMISSION_MODE"
            ;;
    esac
}

################################################################################
# Helper Functions
################################################################################

# Read file content for prompt
read_file_content() {
    local file="$1"
    if [[ -f "$file" ]]; then
        cat "$file"
    else
        echo "[File not found: $file]"
    fi
}

# Create a combined prompt from agent and workflow
build_prompt() {
    local agent_file="$1"
    local task_description="$2"

    local agent_prompt=""
    if [[ -f "$agent_file" ]]; then
        agent_prompt=$(cat "$agent_file")
    fi

    echo "$agent_prompt

---

## Current Task

$task_description"
}

# Get agent prompt with overrides applied
# Usage: get_agent_prompt "dev" -> returns agent + user profile + overrides + memory
get_agent_prompt() {
    local agent_name="$1"

    # Try to use override loader if available
    if type load_agent_with_overrides &>/dev/null; then
        load_agent_with_overrides "$agent_name"
    else
        # Fallback to basic agent loading
        cat "$AGENTS_DIR/${agent_name}.md" 2>/dev/null
    fi
}

# Get model for agent (with override support)
# Usage: get_agent_model "dev" "opus" -> returns override model or fallback
get_agent_model() {
    local agent_name="$1"
    local default_model="$2"

    # Check for override
    if type get_agent_model_override &>/dev/null; then
        local override=$(get_agent_model_override "$agent_name")
        if [[ -n "$override" ]]; then
            echo "$override"
            return
        fi
    fi

    # Use default or global CLAUDE_MODEL
    echo "${default_model:-$CLAUDE_MODEL}"
}

# Get budget for agent (with override support)
get_agent_budget() {
    local agent_name="$1"
    local default_budget="$2"

    # Check for override
    if type get_agent_budget_override &>/dev/null; then
        local override=$(get_agent_budget_override "$agent_name")
        if [[ -n "$override" ]]; then
            echo "$override"
            return
        fi
    fi

    echo "$default_budget"
}

################################################################################
# Persona Banner Functions
################################################################################

print_persona_banner() {
    local persona="$1"
    local role="$2"
    local color="${3:-\033[1;36m}"  # Default: bright cyan
    local model="${4:-}"  # Optional model parameter
    local reset='\033[0m'

    echo ""
    echo -e "${color}╔═══════════════════════════════════════════════════════════════╗${reset}"
    echo -e "${color}║                    PERSONA SWITCH                             ║${reset}"
    echo -e "${color}╠═══════════════════════════════════════════════════════════════╣${reset}"
    echo -e "${color}║  Agent:${reset} $persona"
    echo -e "${color}║  Role:${reset} $role"
    if [[ -n "$model" ]]; then
        echo -e "${color}║  Model:${reset} $model"
    fi
    echo -e "${color}╚═══════════════════════════════════════════════════════════════╝${reset}"
    echo ""
}

################################################################################
# Workflow Invocation Functions
################################################################################

invoke_sm_story_context() {
    local story_key="$1"
    local story_file="$STORIES_DIR/${story_key}.md"
    local context_file="$STORIES_DIR/${story_key}.context.xml"
    local log_file="$LOGS_DIR/${story_key}-context.log"
    local model="sonnet"  # Use Sonnet for planning/context tasks

    # Show persona switch
    print_persona_banner "SM (Scrum Master)" "Story Context Creation & Planning" "\033[1;33m" "$model"

    echo "> Creating story context for: $story_key"

    # Check if story file exists
    if [[ ! -f "$story_file" ]]; then
        echo " Story file not found: $story_file"
        return 1
    fi

    local story_content=$(cat "$story_file")

    local prompt="Create a technical context file for implementing this story.

## Story Specification
$story_content

## Instructions
1. Read the story requirements carefully
2. Explore the codebase to find relevant patterns and existing code
3. Identify files that need to be created or modified
4. Create the context file at: $context_file

The context.xml should include:
- story-key, title, status
- files-to-create list
- files-to-modify list
- dependencies
- testing-requirements
- project-paths (app-root: app, lib-path: app/lib, test-path: app/test)

After creating the context file, update sprint-status.yaml to set this story to 'ready-for-dev'."

    # Invoke Claude CLI from project root
    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$(get_agent_model "sm" "$model")" \
            $(get_permission_flags) \
            --append-system-prompt "$(get_agent_prompt "sm")" \
            --tools "Read,Write,Edit,Grep,Glob,Bash" \
            --max-budget-usd "$(get_agent_budget "sm" "3.00")"
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_dev_story() {
    local story_key="$1"
    local story_file="$STORIES_DIR/${story_key}.md"
    local context_file="$STORIES_DIR/${story_key}.context.xml"
    local log_file="$LOGS_DIR/${story_key}-develop.log"
    local model="opus"  # Use Opus for code development

    # Show persona switch
    print_persona_banner "DEV (Developer)" "Story Implementation & Coding" "\033[1;32m" "$model"

    echo "> Implementing story: $story_key"

    # Check required files
    if [[ ! -f "$story_file" ]]; then
        echo " Story file not found: $story_file"
        return 1
    fi

    if [[ ! -f "$context_file" ]]; then
        echo " Context file not found: $context_file"
        return 1
    fi

    # Pre-flight context check
    echo " Checking context feasibility..."
    check_context_feasibility "$story_file" "$context_file"
    echo ""

    local story_content=$(cat "$story_file")
    local context_content=$(cat "$context_file")

    local prompt="IMPLEMENT THIS STORY NOW. Create all required files and code.

$story_content

---

CONTEXT (files to create/modify):
$context_content

---

START IMMEDIATELY:
1. Read existing code in app/lib/features/ to understand patterns
2. Create ALL files listed in files-to-create using the Write tool
3. Modify files listed in files-to-modify using the Edit tool
4. Write tests in app/test/
5. Run: cd app && flutter test

DO NOT explain or ask questions. Just implement the code."

    # Start context monitor in background
    local monitor_pid=""
    if type start_context_monitor &>/dev/null; then
        monitor_pid=$(start_context_monitor "$log_file" "$story_key")
    fi

    # Start checkpoint monitor in background
    if type start_checkpoint_monitor &>/dev/null; then
        start_checkpoint_monitor "$log_file" "$story_key"
        log_checkpoint_info "$log_file"
    fi

    # Create symlink to current.log for service monitoring
    ln -sf "$log_file" "$LOGS_DIR/current.log"

    # Invoke Claude CLI with full toolset from project root
    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$(get_agent_model "dev" "$model")" \
            $(get_permission_flags) \
            --append-system-prompt "$(get_agent_prompt "dev")" \
            --tools "Read,Write,Edit,Grep,Glob,Bash" \
            --max-budget-usd "$(get_agent_budget "dev" "15.00")"
    ) 2>&1 | tee "$log_file"

    local exit_code=${PIPESTATUS[0]}

    # Stop context monitor
    if [[ -n "$monitor_pid" ]]; then
        stop_context_monitor "$monitor_pid"
    fi

    # Stop checkpoint monitor
    if type stop_checkpoint_monitor &>/dev/null; then
        stop_checkpoint_monitor "$log_file"
    fi

    return $exit_code
}

invoke_sm_code_review() {
    local story_key="$1"
    local story_file="$STORIES_DIR/${story_key}.md"
    local review_file="$STORIES_DIR/${story_key}.code-review.md"
    local log_file="$LOGS_DIR/${story_key}-review.log"
    local model="opus"  # Use Opus for code review

    # Show persona switch
    print_persona_banner "SM (Scrum Master)" "Code Review & Quality Assurance" "\033[1;35m" "$model"

    echo "> Reviewing implementation: $story_key"

    if [[ ! -f "$story_file" ]]; then
        echo " Story file not found: $story_file"
        return 1
    fi

    local story_content=$(cat "$story_file")

    local prompt="Perform a code review for this implemented story.

## Story Specification
$story_content

## Instructions
1. Read all acceptance criteria in the story
2. For each AC, verify it has been implemented correctly
3. Check code quality and patterns
4. Run 'cd app && flutter test' to verify tests pass
5. Create a review report at: $review_file

The review file should include:
- Overall verdict: APPROVED or CHANGES REQUESTED
- Score out of 100
- AC verification checklist (each AC marked as met/not met)
- Code quality notes
- Any issues found

If APPROVED, update sprint-status.yaml to 'done'.
If CHANGES REQUESTED, update sprint-status.yaml to 'in-progress' and list required changes."

    # Start context monitor in background
    local monitor_pid=""
    if type start_context_monitor &>/dev/null; then
        monitor_pid=$(start_context_monitor "$log_file" "$story_key")
    fi

    # Start checkpoint monitor in background
    if type start_checkpoint_monitor &>/dev/null; then
        start_checkpoint_monitor "$log_file" "$story_key"
        log_checkpoint_info "$log_file"
    fi

    # Create symlink to current.log for service monitoring
    ln -sf "$log_file" "$LOGS_DIR/current.log"

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$(get_agent_model "sm" "$model")" \
            $(get_permission_flags) \
            --append-system-prompt "$(get_agent_prompt "sm")" \
            --tools "Read,Write,Edit,Grep,Glob,Bash" \
            --max-budget-usd "$(get_agent_budget "sm" "5.00")"
    ) 2>&1 | tee "$log_file"

    local exit_code=${PIPESTATUS[0]}

    # Stop context monitor
    if [[ -n "$monitor_pid" ]]; then
        stop_context_monitor "$monitor_pid"
    fi

    # Stop checkpoint monitor
    if type stop_checkpoint_monitor &>/dev/null; then
        stop_checkpoint_monitor "$log_file"
    fi

    return $exit_code
}

# Adversarial code review - uses the critical reviewer agent
invoke_adversarial_review() {
    local story_key="$1"
    local story_file="$STORIES_DIR/${story_key}.md"
    local review_file="$STORIES_DIR/${story_key}.adversarial-review.md"
    local log_file="$LOGS_DIR/${story_key}-adversarial-review.log"
    local model="opus"  # Adversarial reviews use Opus for deeper analysis

    # Show persona switch
    print_persona_banner "REVIEWER (Adversarial)" "Critical Code Analysis" "\033[1;31m" "$model"

    echo "> Running adversarial review: $story_key"

    if [[ ! -f "$story_file" ]]; then
        echo " Story file not found: $story_file"
        return 1
    fi

    local story_content=$(cat "$story_file")

    local prompt="CRITICALLY REVIEW this implementation. Your job is to FIND PROBLEMS.

## Story Specification
$story_content

## Instructions
1. Read all acceptance criteria carefully
2. For EACH criterion, verify it is ACTUALLY met (not just superficially)
3. Look for edge cases that aren't handled
4. Check for security vulnerabilities
5. Verify error handling is comprehensive
6. Look for race conditions in async code
7. Check that tests cover failure paths, not just happy paths
8. Run 'cd app && flutter test' to verify tests pass

Create your adversarial review at: $review_file

BE CRITICAL. If you can't find issues, look harder. Every implementation has room for improvement.

Verdict options:
- APPROVED (rare - only for truly solid implementations)
- CHANGES REQUIRED (most common - list specific issues)
- BLOCKED (serious issues that must be addressed)"

    # Create symlink to current.log for monitoring
    ln -sf "$log_file" "$LOGS_DIR/current.log"

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$(get_agent_model "reviewer" "$model")" \
            $(get_permission_flags) \
            --append-system-prompt "$(get_agent_prompt "reviewer")" \
            --tools "Read,Write,Edit,Grep,Glob,Bash" \
            --max-budget-usd "$(get_agent_budget "reviewer" "8.00")"
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_sm_draft_story() {
    local story_key="$1"
    local story_file="$STORIES_DIR/${story_key}.md"
    local epics_file="$PROJECT_ROOT/docs/epics.md"
    local log_file="$LOGS_DIR/${story_key}-draft.log"
    local model="sonnet"  # Use Sonnet for story drafting

    # Show persona switch
    print_persona_banner "SM (Scrum Master)" "Story Drafting & Specification" "\033[1;33m" "$model"

    echo "> Drafting story: $story_key"

    # Extract epic number from story key (e.g., 3-5 -> 3)
    local epic_num=$(echo "$story_key" | cut -d'-' -f1)

    local prompt="Draft a detailed story specification.

Story Key: $story_key
Epic: $epic_num

## Instructions
1. Read the epics file at $epics_file to understand the epic context
2. Find the story entry for $story_key in the epic
3. Create a detailed story specification at: $story_file

The story file should include:
- # Title
- ## Summary
- ## Acceptance Criteria (numbered as AC X.Y.Z)
- ## Technical Notes
- ## Dependencies (if any)
- ## Testing Requirements

After creating the story, update sprint-status.yaml to set this story to 'drafted'."

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/sm.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob" \
            --max-budget-usd 2.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

################################################################################
# Additional Agent Workflows
################################################################################

invoke_ba_requirements() {
    local feature_name="$1"
    local output_file="$PROJECT_ROOT/docs/requirements/${feature_name}.md"
    local log_file="$LOGS_DIR/${feature_name}-requirements.log"
    local model="sonnet"  # Use Sonnet for requirements analysis

    # Show persona switch
    print_persona_banner "BA (Business Analyst)" "Requirements Analysis & User Stories" "\033[1;34m" "$model"

    echo "> Analyzing requirements for: $feature_name"

    mkdir -p "$PROJECT_ROOT/docs/requirements"

    local prompt="Analyze and document requirements for the feature: $feature_name

## Instructions
1. Read the PRD at tooling/docs/prd.md for product context
2. Read the epics at tooling/docs/epics.md for feature context
3. Create a detailed requirements document at: $output_file

The requirements document should include:
- User stories with acceptance criteria
- Business rules
- Data requirements
- Edge cases and error scenarios
- Dependencies

Use the INVEST criteria for user stories."

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/ba.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob" \
            --max-budget-usd 3.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_architect_design() {
    local feature_name="$1"
    local output_file="$STORIES_DIR/tech-spec-${feature_name}.md"
    local log_file="$LOGS_DIR/${feature_name}-architecture.log"
    local model="sonnet"  # Use Sonnet for technical design

    # Show persona switch
    print_persona_banner "ARCHITECT" "Technical Design & Architecture" "\033[1;36m" "$model"

    echo "> Creating technical specification for: $feature_name"

    local prompt="Create a technical specification for: $feature_name

## Instructions
1. Read the architecture documentation at tooling/docs/architecture.md
2. Explore the existing codebase to understand current patterns
3. Read any related story or epic files
4. Create a technical specification at: $output_file

The tech spec should include:
- Component architecture
- Data model and database schema
- API design (if applicable)
- Non-functional requirements
- Implementation notes
- Risks and mitigations

Follow the existing project structure and patterns."

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/architect.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob" \
            --max-budget-usd 5.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_pm_epic() {
    local epic_num="$1"
    local epics_file="$PROJECT_ROOT/docs/epics.md"
    local log_file="$LOGS_DIR/epic-${epic_num}-planning.log"
    local model="sonnet"  # Use Sonnet for epic planning

    # Show persona switch
    print_persona_banner "PM (Product Manager)" "Epic Planning & Prioritization" "\033[1;31m" "$model"

    echo "> Planning epic: $epic_num"

    local prompt="Plan and refine Epic $epic_num

## Instructions
1. Read the PRD at tooling/docs/prd.md for product context
2. Read the current epics file at $epics_file
3. Analyze Epic $epic_num and refine its definition
4. Break down into well-defined stories
5. Update the epics file with refined content

Ensure each story is:
- Clearly defined with user value
- Appropriately sized (1-3 days of work)
- Properly sequenced with dependencies

Use RICE scoring to prioritize stories within the epic."

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/pm.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob" \
            --max-budget-usd 3.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_writer_docs() {
    local doc_type="$1"
    local subject="$2"
    local output_dir="$PROJECT_ROOT/docs"
    local log_file="$LOGS_DIR/${subject}-docs.log"
    local model="sonnet"  # Use Sonnet for documentation

    # Show persona switch
    print_persona_banner "WRITER (Technical Writer)" "Documentation & Content Creation" "\033[1;37m" "$model"

    echo "> Creating documentation: $doc_type for $subject"

    local prompt="Create $doc_type documentation for: $subject

## Instructions
1. Explore the codebase to understand the implementation
2. Read any existing documentation for context
3. Create appropriate documentation

Documentation type: $doc_type

For user guides: Write step-by-step instructions with examples
For API docs: Document endpoints, parameters, and responses
For release notes: Summarize changes in user-friendly language
For README: Create a comprehensive project overview

Save the documentation to an appropriate location in $output_dir/"

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/writer.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob" \
            --max-budget-usd 3.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

################################################################################
# Background Execution
################################################################################

execute_workflow_background() {
    local workflow_name="$1"
    local story_key="$2"
    shift 2
    local workflow_args=("$@")

    local log_file="$LOGS_DIR/${story_key}-${workflow_name}.log"

    echo "> Starting background workflow: $workflow_name for $story_key"

    # Execute in background
    (
        local exit_code=0

        case "$workflow_name" in
            "story_context")
                invoke_sm_story_context "$story_key" || exit_code=$?
                ;;
            "dev_story")
                invoke_dev_story "$story_key" || exit_code=$?
                ;;
            "code_review")
                invoke_sm_code_review "$story_key" || exit_code=$?
                ;;
            "draft_story")
                invoke_sm_draft_story "$story_key" || exit_code=$?
                ;;
            *)
                echo "Unknown workflow: $workflow_name"
                exit_code=1
                ;;
        esac

        exit $exit_code
    ) > "$log_file" 2>&1 &

    local bg_pid=$!
    echo "Background PID: $bg_pid"
    echo "Log file: $log_file"

    return 0
}

################################################################################
# Full Pipeline
################################################################################

################################################################################
# Sprint Status Management
################################################################################

# Update story status in sprint-status.yaml
update_story_status() {
    local story_key="$1"
    local new_status="$2"
    local sprint_status_file="$PROJECT_ROOT/docs/sprint-status.yaml"

    echo "> Updating sprint status: $story_key -> $new_status"

    if [[ ! -f "$sprint_status_file" ]]; then
        echo "  Sprint status file not found: $sprint_status_file"
        return 1
    fi

    # Check if story exists in file
    if ! grep -q "^  $story_key:" "$sprint_status_file"; then
        echo "  Story $story_key not found in sprint-status.yaml"
        return 1
    fi

    # Update the status using sed
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/^  $story_key:.*$/  $story_key: $new_status/" "$sprint_status_file"
    else
        # Linux
        sed -i "s/^  $story_key:.*$/  $story_key: $new_status/" "$sprint_status_file"
    fi

    if [[ $? -eq 0 ]]; then
        echo " Status updated: $story_key -> $new_status"

        # Update the 'updated' timestamp
        local today=$(date +%Y-%m-%d)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^# updated:.*$/# updated: $today/" "$sprint_status_file"
            sed -i '' "s/^updated:.*$/updated: $today/" "$sprint_status_file"
        else
            sed -i "s/^# updated:.*$/# updated: $today/" "$sprint_status_file"
            sed -i "s/^updated:.*$/updated: $today/" "$sprint_status_file"
        fi

        return 0
    else
        echo " Failed to update status"
        return 1
    fi
}

################################################################################
# Auto-Commit and PR Functions
################################################################################

# Auto-commit changes after development
auto_commit_changes() {
    local story_key="$1"
    local story_file="$STORIES_DIR/${story_key}.md"

    echo "> Auto-committing changes..."

    # Check if there are changes to commit
    cd "$PROJECT_ROOT" || return 1

    if ! git diff --quiet || ! git diff --cached --quiet || [[ -n $(git ls-files --others --exclude-standard) ]]; then
        echo " Detected changes to commit"

        # Extract story title from story file
        local story_title=""
        if [[ -f "$story_file" ]]; then
            story_title=$(grep -m 1 "^# " "$story_file" | sed 's/^# //' || echo "$story_key")
        else
            story_title="$story_key"
        fi

        # Stage all changes
        git add -A

        # Create commit message
        local commit_msg="feat: $story_title

Automated implementation via Claude Code CLI

Story: $story_key

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

        # Commit
        git commit -m "$commit_msg"

        if [[ $? -eq 0 ]]; then
            echo " Changes committed successfully"
            echo " Commit: $(git rev-parse --short HEAD)"
            return 0
        else
            echo "  Commit failed or no changes to commit"
            return 1
        fi
    else
        echo "No changes to commit"
        return 0
    fi
}

# Create pull request after commit
auto_create_pr() {
    local story_key="$1"
    local story_file="$STORIES_DIR/${story_key}.md"
    local branch_name="feature/$story_key"

    echo "> Creating pull request..."

    cd "$PROJECT_ROOT" || return 1

    # Check if gh CLI is available
    if ! command -v gh &> /dev/null; then
        echo "  GitHub CLI (gh) not found. Skipping PR creation."
        echo "   Install with: brew install gh"
        return 1
    fi

    # Get current branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)

    # Extract story title and summary
    local pr_title=""
    local pr_body=""

    if [[ -f "$story_file" ]]; then
        pr_title=$(grep -m 1 "^# " "$story_file" | sed 's/^# //' || echo "$story_key")

        # Build PR body from story file
        pr_body="## Story: $story_key

$(cat "$story_file")

---

Auto-generated via Claude Code CLI automation"
    else
        pr_title="$story_key implementation"
        pr_body="Story: $story_key

Auto-generated via Claude Code CLI automation"
    fi

    # Create PR
    gh pr create \
        --title "$pr_title" \
        --body "$pr_body" \
        --base main \
        --head "$current_branch" 2>&1

    if [[ $? -eq 0 ]]; then
        echo " Pull request created"
        return 0
    else
        echo "  PR creation failed. You can create it manually with:"
        echo "   gh pr create --title \"$pr_title\" --base main"
        return 1
    fi
}

run_full_pipeline() {
    local story_key="$1"
    local auto_commit="${AUTO_COMMIT:-true}"  # Default to true
    local auto_pr="${AUTO_PR:-false}"         # Default to false

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  AUTOMATED STORY PIPELINE: $story_key"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # Phase 1: Create context if needed
    local context_file="$STORIES_DIR/${story_key}.context.xml"
    if [[ ! -f "$context_file" ]]; then
        echo "> Phase 1: Creating story context..."
        invoke_sm_story_context "$story_key"
        if [[ $? -ne 0 ]]; then
            echo " Context creation failed"
            return 1
        fi
        echo " Context created"
        echo ""
    else
        echo "[OK] Context already exists, skipping..."
        echo ""
    fi

    # Phase 2: Development
    echo "> Phase 2: Implementing story..."
    invoke_dev_story "$story_key"
    if [[ $? -ne 0 ]]; then
        echo " Development failed"
        return 1
    fi
    echo " Development complete"
    echo ""

    # Phase 2.5: Update status to 'review'
    update_story_status "$story_key" "review"
    echo ""

    # Phase 2.6: Auto-commit (if enabled)
    if [[ "$auto_commit" == "true" ]]; then
        auto_commit_changes "$story_key"
        echo ""
    fi

    # Phase 2.7: Auto-PR (if enabled)
    if [[ "$auto_pr" == "true" ]]; then
        auto_create_pr "$story_key"
        echo ""
    fi

    # Phase 3: Code review
    echo "> Phase 3: Code review..."
    invoke_sm_code_review "$story_key"
    if [[ $? -ne 0 ]]; then
        echo " Code review failed"
        return 1
    fi
    echo " Code review complete"
    echo ""

    # Phase 4: Update status to 'done' (if review passed)
    update_story_status "$story_key" "done"
    echo ""

    echo "═══════════════════════════════════════════════════════════════"
    echo "  PIPELINE COMPLETE"
    echo "═══════════════════════════════════════════════════════════════"

    return 0
}

################################################################################
# BROWNFIELD WORKFLOWS - Bug fixes, refactoring, investigations, maintenance
################################################################################

invoke_bugfix() {
    local bug_id="$1"
    local bug_file="$STORIES_DIR/bugs/${bug_id}.md"
    local log_file="$LOGS_DIR/${bug_id}-bugfix.log"
    local model="${CLAUDE_MODEL_DEV:-opus}"

    # Show persona switch
    print_persona_banner "MAINTAINER" "Bug Investigation & Fix" "\033[1;31m" "$model"

    echo "> Investigating and fixing bug: $bug_id"

    # Build prompt based on whether bug file exists
    local prompt=""
    if [[ -f "$bug_file" ]]; then
        local bug_content=$(cat "$bug_file")
        prompt="FIX THIS BUG.

## Bug Report
$bug_content

## Instructions
1. First, understand the bug by reading the report carefully
2. Explore the codebase to find the root cause
3. Identify all affected files
4. Implement the fix with minimal changes
5. Add tests to prevent regression
6. Run existing tests to ensure no regressions

DO NOT over-engineer. Make the minimal change needed to fix the bug.
After fixing, create a brief summary at: $STORIES_DIR/bugs/${bug_id}.fix-summary.md"
    else
        prompt="INVESTIGATE AND FIX BUG: $bug_id

## Instructions
1. Search the codebase for code related to: $bug_id
2. Identify potential issues based on the bug description
3. Explore related code paths and error handling
4. Implement a fix with minimal changes
5. Add tests to prevent regression
6. Run existing tests to ensure no regressions

Bug ID/Description: $bug_id

After investigating, create:
- $STORIES_DIR/bugs/${bug_id}.md (bug report if not exists)
- $STORIES_DIR/bugs/${bug_id}.fix-summary.md (fix summary)"
    fi

    # Ensure bugs directory exists
    mkdir -p "$STORIES_DIR/bugs"

    # Create symlink to current.log for monitoring
    ln -sf "$log_file" "$LOGS_DIR/current.log"

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/maintainer.md" 2>/dev/null || cat "$AGENTS_DIR/dev.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob,Bash" \
            --max-budget-usd 10.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_refactor() {
    local refactor_id="$1"
    local refactor_file="$STORIES_DIR/refactors/${refactor_id}.md"
    local log_file="$LOGS_DIR/${refactor_id}-refactor.log"
    local model="${CLAUDE_MODEL_DEV:-opus}"

    # Show persona switch
    print_persona_banner "MAINTAINER" "Code Refactoring & Improvement" "\033[1;35m" "$model"

    echo "> Refactoring: $refactor_id"

    local prompt=""
    if [[ -f "$refactor_file" ]]; then
        local refactor_content=$(cat "$refactor_file")
        prompt="REFACTOR THIS CODE.

## Refactoring Specification
$refactor_content

## Instructions
1. Read and understand the refactoring goals
2. Analyze the current code structure
3. Plan the refactoring steps (smallest possible changes)
4. Implement changes incrementally
5. Run tests after each significant change
6. Ensure all tests pass before completion

IMPORTANT: Make changes incrementally. Ensure tests pass between changes.
Create a summary at: $STORIES_DIR/refactors/${refactor_id}.summary.md"
    else
        prompt="REFACTOR: $refactor_id

## Instructions
1. Search the codebase for code related to: $refactor_id
2. Analyze the current implementation
3. Identify improvement opportunities (readability, performance, maintainability)
4. Plan incremental refactoring steps
5. Implement changes one at a time
6. Run tests after each change

Target: $refactor_id

Create:
- $STORIES_DIR/refactors/${refactor_id}.md (refactoring plan)
- $STORIES_DIR/refactors/${refactor_id}.summary.md (what was changed)"
    fi

    # Ensure refactors directory exists
    mkdir -p "$STORIES_DIR/refactors"

    ln -sf "$log_file" "$LOGS_DIR/current.log"

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/maintainer.md" 2>/dev/null || cat "$AGENTS_DIR/dev.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob,Bash" \
            --max-budget-usd 12.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_investigate() {
    local topic="$1"
    local output_file="$STORIES_DIR/investigations/${topic}.md"
    local log_file="$LOGS_DIR/${topic}-investigate.log"
    local model="${CLAUDE_MODEL_PLANNING:-sonnet}"  # Use Sonnet for investigation (read-heavy)

    # Show persona switch
    print_persona_banner "MAINTAINER" "Codebase Investigation & Analysis" "\033[1;36m" "$model"

    echo "> Investigating: $topic"

    local prompt="INVESTIGATE AND DOCUMENT: $topic

## Instructions
1. Explore the codebase thoroughly to understand: $topic
2. Trace code paths, data flows, and dependencies
3. Document what you find in a comprehensive report
4. Include:
   - How the feature/component works
   - Key files and their responsibilities
   - Data flows and state management
   - External dependencies
   - Potential issues or technical debt
   - Recommendations for improvements

Create a detailed investigation report at: $output_file

DO NOT make any code changes. This is a read-only investigation."

    # Ensure investigations directory exists
    mkdir -p "$STORIES_DIR/investigations"

    ln -sf "$log_file" "$LOGS_DIR/current.log"

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/maintainer.md" 2>/dev/null || cat "$AGENTS_DIR/architect.md" 2>/dev/null)" \
            --tools "Read,Grep,Glob" \
            --max-budget-usd 5.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_quickfix() {
    local description="$1"
    local log_file="$LOGS_DIR/quickfix-$(date +%Y%m%d-%H%M%S).log"
    local model="${CLAUDE_MODEL_PLANNING:-sonnet}"  # Use Sonnet for quick fixes

    # Show persona switch
    print_persona_banner "MAINTAINER" "Quick Fix" "\033[1;33m" "$model"

    echo "> Quick fix: $description"

    local prompt="QUICK FIX: $description

## Instructions
1. Make the requested change with minimal modifications
2. Only change what is absolutely necessary
3. Run tests if applicable
4. Do not refactor unrelated code
5. Do not add unnecessary comments or documentation

This is a quick, focused change. Be efficient."

    ln -sf "$log_file" "$LOGS_DIR/current.log"

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/maintainer.md" 2>/dev/null || cat "$AGENTS_DIR/dev.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob,Bash" \
            --max-budget-usd 3.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_migrate() {
    local migration_id="$1"
    local migration_file="$STORIES_DIR/migrations/${migration_id}.md"
    local log_file="$LOGS_DIR/${migration_id}-migrate.log"
    local model="${CLAUDE_MODEL_DEV:-opus}"

    # Show persona switch
    print_persona_banner "MAINTAINER" "Migration & Upgrade" "\033[1;34m" "$model"

    echo "> Running migration: $migration_id"

    local prompt=""
    if [[ -f "$migration_file" ]]; then
        local migration_content=$(cat "$migration_file")
        prompt="EXECUTE THIS MIGRATION.

## Migration Specification
$migration_content

## Instructions
1. Read the migration plan carefully
2. Back up any critical data/configuration if needed
3. Execute the migration steps in order
4. Run tests after each major step
5. Document any issues encountered
6. Verify the migration is complete

Create a migration log at: $STORIES_DIR/migrations/${migration_id}.log.md"
    else
        prompt="PLAN AND EXECUTE MIGRATION: $migration_id

## Instructions
1. Analyze what needs to be migrated based on: $migration_id
2. Create a migration plan
3. Execute the migration with careful testing
4. Document all changes made

Create:
- $STORIES_DIR/migrations/${migration_id}.md (migration plan)
- $STORIES_DIR/migrations/${migration_id}.log.md (execution log)"
    fi

    # Ensure migrations directory exists
    mkdir -p "$STORIES_DIR/migrations"

    ln -sf "$log_file" "$LOGS_DIR/current.log"

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/maintainer.md" 2>/dev/null || cat "$AGENTS_DIR/architect.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob,Bash" \
            --max-budget-usd 15.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

invoke_tech_debt() {
    local debt_id="$1"
    local debt_file="$STORIES_DIR/tech-debt/${debt_id}.md"
    local log_file="$LOGS_DIR/${debt_id}-tech-debt.log"
    local model="${CLAUDE_MODEL_DEV:-opus}"

    # Show persona switch
    print_persona_banner "MAINTAINER" "Technical Debt Resolution" "\033[1;35m" "$model"

    echo "> Resolving technical debt: $debt_id"

    local prompt=""
    if [[ -f "$debt_file" ]]; then
        local debt_content=$(cat "$debt_file")
        prompt="RESOLVE THIS TECHNICAL DEBT.

## Technical Debt Item
$debt_content

## Instructions
1. Understand the scope of the technical debt
2. Identify all affected areas
3. Plan incremental improvements
4. Implement fixes while maintaining backwards compatibility
5. Add tests where missing
6. Run all tests to ensure no regressions

Document resolution at: $STORIES_DIR/tech-debt/${debt_id}.resolved.md"
    else
        prompt="IDENTIFY AND RESOLVE TECHNICAL DEBT: $debt_id

## Instructions
1. Search for code related to: $debt_id
2. Identify technical debt (poor patterns, missing tests, outdated code)
3. Prioritize fixes by impact
4. Implement improvements incrementally
5. Run tests after each change

Create:
- $STORIES_DIR/tech-debt/${debt_id}.md (debt identification)
- $STORIES_DIR/tech-debt/${debt_id}.resolved.md (resolution summary)"
    fi

    # Ensure tech-debt directory exists
    mkdir -p "$STORIES_DIR/tech-debt"

    ln -sf "$log_file" "$LOGS_DIR/current.log"

    (
        cd "$PROJECT_ROOT" || exit 1
        echo "$prompt" | $CLAUDE_CLI -p \
            --model "$model" \
            $(get_permission_flags) \
            --append-system-prompt "$(cat "$AGENTS_DIR/maintainer.md" 2>/dev/null || cat "$AGENTS_DIR/dev.md" 2>/dev/null)" \
            --tools "Read,Write,Edit,Grep,Glob,Bash" \
            --max-budget-usd 12.00
    ) 2>&1 | tee "$log_file"

    return ${PIPESTATUS[0]}
}

# Functions are available when this file is sourced
