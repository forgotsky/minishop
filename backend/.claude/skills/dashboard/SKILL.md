---
name: dashboard
description: Launch live status dashboard in a terminal
---

# Live Dashboard Skill

Launch or provide instructions for the Devflow live status dashboard - a real-time display of context usage, cost tracking, and agent activity.

## Usage

```
/dashboard [story-key] [options]
```

## Options

| Option | Description |
|--------|-------------|
| story-key | Story to monitor (default: 'default') |
| --refresh N | Refresh interval in seconds (default: 0.5) |
| --compact | Single-line compact mode |
| --width N | Dashboard width (default: 70) |

## Prompt

You are helping the user launch the Devflow live dashboard.

**Arguments:** $ARGUMENTS

### Dashboard Launch Instructions

The live dashboard is a terminal-based real-time display that needs to run in a separate terminal to show continuous updates while you work.

**Option 1: VS Code Split Terminal (Recommended)**

Tell the user:

1. Open the VS Code integrated terminal (Ctrl+` or Cmd+`)
2. Click the "Split Terminal" button (or press Cmd+Shift+5 / Ctrl+Shift+5)
3. In the new terminal pane, run:

```bash
python3 tooling/scripts/live_dashboard.py $ARGUMENTS
```

Or if using npm:
```bash
npx devflow dashboard $ARGUMENTS
```

**Option 2: Separate Terminal Window**

For a floating dashboard window:

```bash
# Open a new terminal and run:
cd [project-root] && python3 tooling/scripts/live_dashboard.py $ARGUMENTS
```

**Option 3: Compact Mode (less screen space)**

For minimal display:
```bash
python3 tooling/scripts/live_dashboard.py --compact $ARGUMENTS
```

### Dashboard Features

The dashboard displays:

```
+------------------------------------------------------------------+
|  DEVFLOW LIVE DASHBOARD                          Updated: HH:MM  |
+------------------------------------------------------------------+
|  ACTIVITY                                                        |
|  Agent: DEV [2/3] Development (3:45)                            |
|  Task: Implementing user authentication                          |
+------------------------------------------------------------------+
|  CONTEXT                                                         |
|  Usage: [================--------]  65.2% ^                      |
|  Tokens: 130.4K/200K  ~14 exchanges left                        |
+------------------------------------------------------------------+
|  COST                                                            |
|  Budget: [====--------------------]  12.3%                       |
|  Spent: $1.85 / $15.00  In: 45.2K  Out: 12.1K                   |
+------------------------------------------------------------------+
|  RECENT                                                          |
|  > +3.2K tokens (45s ago)                                       |
|  > +2.8K tokens (1m ago)                                        |
+------------------------------------------------------------------+
```

- **Activity**: Current agent, phase, task, and elapsed time
- **Context**: Visual progress bar with trend indicator and remaining exchanges
- **Cost**: Budget usage with token breakdown
- **Recent**: Token history showing recent activity

### Color Coding

- Green: Safe levels (< 50% context, < 75% budget)
- Yellow: Caution (50-75% context, 75-90% budget)
- Red: Critical (> 75% context, > 90% budget)

### Tips

1. **High refresh rate**: Use `--refresh 0.25` for faster updates
2. **Narrow terminal**: Use `--width 60` for smaller panes
3. **Minimal mode**: Use `--compact` for single-line status
4. **Stop dashboard**: Press Ctrl+C to exit

### If No Data Shows

The dashboard reads from:
- Context state: `tooling/.automation/context/context_[story-key].json`
- Cost data: `tooling/.automation/costs/sessions/*.json`

If these files don't exist yet, run a story or use `/develop` to generate tracking data.
