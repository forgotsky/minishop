---
description: Run multi-agent swarm mode (debate/consensus)
argument-hint: <story-key> [--agents AGENT1,AGENT2,...]
---

Run Devflow swarm mode for: $ARGUMENTS

Execute: `npx @pjmendonca/devflow swarm $ARGUMENTS`

This runs multi-agent collaboration where agents debate and iterate until consensus:
- Multiple agents analyze the task simultaneously
- Agents provide feedback on each other's work
- Issues are addressed through iterative refinement
- Continues until consensus or max iterations reached

Default agents: ARCHITECT, DEV, REVIEWER

Examples:
- `/swarm 3-5` - Run swarm with default agents
- `/swarm 3-5 --agents ARCHITECT,DEV,REVIEWER,SECURITY` - Custom agents
- `/swarm 3-5 --max-iter 5` - Increase max iterations
