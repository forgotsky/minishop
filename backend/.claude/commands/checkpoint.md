---
description: Create or restore context checkpoints
argument-hint: [save|restore|list] [checkpoint-name]
---

Manage Devflow context checkpoints: $ARGUMENTS

Execute: `npx @pjmendonca/devflow checkpoint $ARGUMENTS`

This manages context preservation checkpoints:
- Save current context state before risky operations
- Restore previous context if work is lost
- List available checkpoints for a story

Commands:
- `save <name>` - Save current context as checkpoint
- `restore <name>` - Restore from checkpoint
- `list` - List available checkpoints
- `auto` - Enable automatic checkpointing

Examples:
- `/checkpoint save before-refactor` - Save checkpoint
- `/checkpoint list` - Show available checkpoints
- `/checkpoint restore before-refactor` - Restore state

Automatic checkpointing occurs at:
- Before each agent phase starts
- When approaching context limits
- After major milestones
