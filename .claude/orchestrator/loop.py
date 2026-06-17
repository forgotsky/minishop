#!/usr/bin/env python
"""
Orchestrator scheduling loop.
Scans the board every cycle and dispatches work.

Usage:
    python loop.py --once     # Run one scan cycle
    python loop.py --watch N  # Run every N minutes (Ctrl+C to stop)

In Claude Code:
    /loop 10m python .claude/orchestrator/loop.py --once
"""
import os
import sys
import time
import subprocess

ORCHESTRATOR = os.path.dirname(os.path.abspath(__file__))

# Import board operations
sys.path.insert(0, ORCHESTRATOR)
from board import (
    ensure_board, scan_stage, move_story, find_next_dispatchable, report,
    BOARD_DIR, STAGES,
)


def run_cycle():
    """One scan-dispatch cycle. Returns action summary."""
    ensure_board()
    actions = []

    # ── 1. backlog: detect new URS → launch planning ──
    backlog = scan_stage("backlog")
    if backlog:
        urs_file = backlog[0]  # Pick highest priority
        actions.append(f"PLANNING: {urs_file}")
        # Move to planning stage
        move_story(urs_file, "planning")
        # Trigger planning workflow (outputs a prompt for the agent)
        planning_prompt = f"""
**Orchestrator: Planning 沙箱已创建**

Backlog 中发现新 URS: `{urs_file}`

阅读 `.claude/orchestrator/planning-workflow.md` 获取完整流程。
依次调用 BA → PM → Architect → Planner 完成拆解。
输出 Story 文件到 `{BOARD_DIR}/ready/`。
完成后执行: `python .claude/orchestrator/board.py --move {urs_file} done`
"""
        actions.append("  -> Planning workflow triggered (see planning-workflow.md)")

    # ── 2. planning: check timeout ──
    # (Placeholder — TODO: detect stuck planning sessions)

    # ── 3. ready: find next dispatchable ──
    next_up = find_next_dispatchable()
    if next_up.get("file"):
        story_file = next_up["file"]
        actions.append(f"DISPATCH: {story_file}")
        move_story(story_file, "running")
        actions.append(f"  -> 执行: Workflow 按 story 里的 agents 字段起沙箱")

    elif next_up.get("blocked_stories"):
        for b in next_up["blocked_stories"]:
            actions.append(f"BLOCKED: {b['file']} waiting on {b['waiting_on']}")

    # ── 4. running: check for HUMAN checkpoints ──
    running = scan_stage("running")
    for story_file in running:
        filepath = os.path.join(BOARD_DIR, "running", story_file)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if "[HUMAN]" in content:
            # Check if all non-HUMAN steps are done
            steps = [l for l in content.split("\n") if l.strip().startswith("- [")]
            non_human = [s for s in steps if "[HUMAN]" not in s]
            human = [s for s in steps if "[HUMAN]" in s]
            if all("x]" in s for s in non_human) and any("[ ]" in s for s in human):
                actions.append(f"CHECKPOINT: {story_file} -> 移到 blocked (等人)")
                move_story(story_file, "blocked")

    # ── 5. blocked: check if human responded ──
    blocked = scan_stage("blocked")
    for story_file in blocked:
        filepath = os.path.join(BOARD_DIR, "blocked", story_file)
        mtime = os.path.getmtime(filepath)
        age_hours = (time.time() - mtime) / 3600
        if age_hours > 24:
            actions.append(f"REMINDER: {story_file} blocked for {age_hours:.0f}h — 需要人工关注")

    # ── 6. done: downstream unlock ──
    done = scan_stage("done")
    if done:
        new_done = len(done)
        # Check if any ready stories are now unblocked
        next_after = find_next_dispatchable()
        if next_after.get("file"):
            actions.append(f"UNLOCKED: {next_after['file']} (dep satisfied by new done)")

    # Print report
    actions.insert(0, report())
    return actions


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Orchestrator loop")
    parser.add_argument("--once", action="store_true", help="Run one cycle")
    parser.add_argument("--watch", type=int, metavar="N", help="Run every N minutes")
    args = parser.parse_args()

    if args.once:
        actions = run_cycle()
        for a in actions:
            print(a)

    if args.watch:
        interval = args.watch * 60
        print(f"Orchestrator running every {args.watch}min (Ctrl+C to stop)")
        try:
            while True:
                print(f"\n{'='*50}")
                actions = run_cycle()
                for a in actions:
                    print(a)
                print(f"Next cycle in {args.watch}min...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nOrchestrator stopped.")
