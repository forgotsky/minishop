---
description: View handoff summaries between agents
argument-hint: <story-key> [--from AGENT] [--to AGENT]
---

View agent handoff summaries: $ARGUMENTS

Execute: `npx @pjmendonca/devflow handoff $ARGUMENTS`

This shows structured handoff information between agents:
- What was completed in the previous phase
- Decisions made and their rationale
- Blockers or warnings for the next agent
- Files modified with change summaries

Options:
- `--from AGENT` - Filter by source agent
- `--to AGENT` - Filter by destination agent
- `--latest` - Show only most recent handoff
- `--export` - Export handoffs to markdown

Examples:
- `/handoff 3-5` - Show all handoffs for story
- `/handoff 3-5 --from DEV --to REVIEWER` - Specific handoff
- `/handoff 3-5 --latest` - Most recent handoff
