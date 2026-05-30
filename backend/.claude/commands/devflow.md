---
description: Run any Devflow command
argument-hint: <command> [args]
---

Run: `devflow $ARGUMENTS`

This is a passthrough command to run any Devflow CLI command directly.

## Available Commands

| Command | Description |
|---------|-------------|
| `story` | Run full story pipeline (context + dev + review) |
| `collab` | Run collaborative multi-agent mode |
| `checkpoint` | Create or restore context checkpoints |
| `memory` | View or query shared agent memory |
| `cost` | View cost dashboard and spending analytics |
| `validate` | Validate project configuration |
| `personalize` | Personalize agent behavior |
| `version` | Show version information |

## Examples

```bash
/devflow story 3-5
/devflow cost --history 10
/devflow checkpoint --list
/devflow validate
```

Run `devflow --help` for full command list.
