---
description: Run code review for a story
argument-hint: <story-key>
---

Run the Devflow code review for story: $ARGUMENTS

Execute: `npx @pjmendonca/devflow review $ARGUMENTS`

This invokes the REVIEWER agent to perform a thorough code review.

## What it does

1. Reviews all code changes for the story
2. Checks security, reliability, correctness, and maintainability
3. Classifies issues by severity (CRITICAL, HIGH, MEDIUM, LOW)
4. Produces a structured review with actionable feedback

## Review Output

The review produces a verdict:
- **APPROVED** - Code meets standards, ready to merge
- **CHANGES REQUIRED** - Issues found that must be addressed
- **BLOCKED** - Critical issues prevent progress

## Options

- `--adversarial` - Use Opus for deeper, more critical analysis

## Example

```bash
/review 3-5
/review 3-5 --adversarial
```
