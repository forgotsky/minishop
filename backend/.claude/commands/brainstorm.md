---
description: Run story brainstorming workshop
argument-hint: [--quick|--journey|--features|--decompose EPIC|--prioritize]
---

# Brainstorm Command

Run the brainstorm skill for story discovery and backlog creation.

Use the Skill tool to invoke the brainstorm skill with the provided arguments:

```
skill: brainstorm
args: $ARGUMENTS
```

If no arguments provided, run the full workshop mode.

## Quick Reference

| Mode | Time | Description |
|------|------|-------------|
| (default) | 30 min | Full workshop: vision, features, journey, decomposition, planning |
| --quick | 10 min | Vision + 5 key features |
| --journey | 15 min | Focus on user journey mapping |
| --features | 15 min | Focus on rapid feature brainstorming |
| --decompose EPIC | 10 min | Break down an epic into stories |
| --prioritize | 5 min | Re-prioritize existing backlog |
