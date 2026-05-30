---
description: Personalize agent behavior with guided wizard
argument-hint: [agent-name]
---

Run the agent personalization wizard to customize agent behavior.

Execute: `python3 tooling/scripts/personalize_agent.py $ARGUMENTS`

Available agents: dev, sm, ba, architect, pm, writer, maintainer, reviewer

Examples:
- `/personalize dev` - Customize the developer agent
- `/personalize` - Interactive agent selection
- `/personalize --list` - Show available templates
