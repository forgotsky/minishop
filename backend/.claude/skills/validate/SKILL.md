# Validate Skill

Run automated validation checks with feedback loops.

## Description

The validate skill runs a three-tier validation system:

1. **Pre-flight** (Tier 1): Checks before execution
   - Story file exists
   - Budget is available
   - Dependencies are valid

2. **Inter-phase** (Tier 2): Checks between agents
   - Code compiles/parses
   - Linting passes
   - Phase transitions are valid

3. **Post-completion** (Tier 3): Checks after pipeline
   - Tests pass
   - Types are valid
   - Version is synced
   - Changelog is updated

## Usage

```
/validate [story-key] [--tier 1|2|3|all] [--auto-fix] [--json]
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| story-key | Story identifier to validate | Current branch |
| --tier | Validation tier (1, 2, 3, or all) | all |
| --auto-fix | Attempt automatic fixes | false |
| --json | Output as JSON | false |
| --quiet | Minimal output | false |

## Examples

### Run all validations
```
/validate 3-5 --tier all
```

### Run post-completion checks with auto-fix
```
/validate --tier 3 --auto-fix
```

### Get JSON output for CI
```
/validate 3-5 --json
```

## Prompt

You are running validation checks for the Devflow project.

$ARGUMENTS

Execute the validation loop:

```python
import sys
sys.path.insert(0, "tooling/scripts/lib")

from validation_loop import (
    create_validation_loop,
    run_preflight_validation,
    run_post_completion_validation,
    ALL_GATES,
    LoopContext,
)

# Parse arguments
story_key = "$ARGUMENTS".split()[0] if "$ARGUMENTS" else "validation-check"
tier = "all"  # Default to all tiers

# Create context
context = LoopContext(story_key=story_key)

# Run appropriate validation
if tier == "1" or tier == "all":
    print("[VALIDATION] Running pre-flight checks...")
    report = run_preflight_validation(story_key)
    print(report.to_summary())

if tier == "3" or tier == "all":
    print("[VALIDATION] Running post-completion checks...")
    report = run_post_completion_validation(story_key)
    print(report.to_summary())
```

Report results clearly with:
- [PASS] for passed gates
- [WARN] for warnings
- [FAIL] for failures
- Suggested fixes when available
