---
description: Run collaborative story with mode selection
argument-hint: <story-key> [--swarm|--pair|--auto]
---

Run Devflow collaboration for: $ARGUMENTS

Execute: `npx @pjmendonca/devflow collab $ARGUMENTS`

This is the unified collaboration CLI with all modes:

Modes:
- `--auto` - Auto-route to best agents (default)
- `--swarm` - Multi-agent debate/consensus
- `--pair` - DEV + REVIEWER pair programming
- `--sequential` - Traditional sequential pipeline

Options:
- `--agents AGENT1,AGENT2` - Specify agents (for swarm)
- `--max-iterations N` - Max iterations (default: 3)
- `--budget N` - Budget limit in USD
- `--memory` - Show shared memory
- `--query "Q"` - Query knowledge graph
- `--route-only` - Preview routing only

Examples:
- `/collab 3-5 --swarm` - Run swarm mode
- `/collab 3-5 --pair` - Run pair programming
- `/collab "fix auth bug" --auto` - Auto-route task
