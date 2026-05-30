# Validate

Run validation checks on the current story or codebase.

## Usage

```
/validate [story-key] [options]
```

## Options

- `--tier 1|2|3|all` - Which validation tier to run
  - 1: Pre-flight (story exists, budget, dependencies)
  - 2: Inter-phase (code compiles, lint, transitions)
  - 3: Post-completion (tests, types, version sync)
  - all: Run all tiers
- `--auto-fix` - Attempt automatic fixes for failures
- `--json` - Output as JSON
- `--quiet` - Minimal output

## Examples

```bash
# Run all validation tiers
/validate 3-5 --tier all

# Run pre-flight checks only
/validate 3-5 --tier 1

# Run post-completion with auto-fix
/validate 3-5 --tier 3 --auto-fix
```

## Prompt

Run the validation loop for story: $ARGUMENTS

Execute the following:

```bash
python3 tooling/scripts/lib/validation_loop.py --story "$ARGUMENTS" --all
```

If no story key is provided, run validation on the current codebase state:

```bash
python3 tooling/scripts/lib/validation_loop.py --tier 3
```

Report the validation results clearly, including:
- Which gates passed
- Which gates failed with reasons
- Any warnings
- Suggested fixes if available
