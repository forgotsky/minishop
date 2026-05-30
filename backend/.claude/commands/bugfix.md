---
description: Fix a bug
argument-hint: <bug-id>
---

Run the Devflow bugfix automation for: $ARGUMENTS

Execute: `npx @pjmendonca/devflow bugfix $ARGUMENTS`

This invokes the MAINTAINER agent to investigate and fix bugs using a surgical approach.

## What it does

1. Investigates the bug to understand root cause
2. Identifies the minimal change needed to fix it
3. Implements the fix with regression tests
4. Documents the fix and any related technical debt

## Options

- `--dry-run` - Analyze the bug without making changes
- `--investigation-only` - Just investigate, don't fix

## Example

```bash
/bugfix login-crash-123
/bugfix "Users can't submit form on mobile"
```
