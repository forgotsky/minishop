---
description: View or query shared agent memory
argument-hint: <story-key> [--query "question"]
---

View shared memory for: $ARGUMENTS

Execute: `npx @pjmendonca/devflow memory $ARGUMENTS`

This displays the shared memory and knowledge graph for a story:
- Cross-agent shared memory pool
- Decision tracking with knowledge graph
- Learnings and context from all agents

Query Mode:
Use `--query` to ask questions about past decisions:
- `/memory 3-5 --query "What did ARCHITECT decide about auth?"`
- `/memory 3-5 --query "Why was the database schema changed?"`

Examples:
- `/memory 3-5` - Show all shared memory for story 3-5
- `/memory 3-5 --query "security decisions"` - Query specific topic
