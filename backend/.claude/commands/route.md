---
description: Auto-route task to best agents
argument-hint: <task-description>
---

Auto-route task to optimal agents: $ARGUMENTS

Execute: `npx @pjmendonca/devflow route $ARGUMENTS`

This intelligently selects the best agents based on task analysis:
- Analyzes task description for keywords and patterns
- Detects task type (bugfix, security, feature, refactor, etc.)
- Estimates complexity (trivial to critical)
- Routes to appropriate specialists

Task type detection examples:
- "fix login bug" -> MAINTAINER, DEV, REVIEWER
- "security vulnerability" -> SECURITY, ARCHITECT, REVIEWER
- "new user profile feature" -> BA, ARCHITECT, DEV, REVIEWER
- "refactor auth module" -> ARCHITECT, DEV, MAINTAINER

Examples:
- `/route fix authentication timeout` - Routes to bug specialists
- `/route add payment integration` - Routes to feature team
- `/route --route-only fix memory leak` - Preview routing only
