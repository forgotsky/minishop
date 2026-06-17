"""
Kanban state machine — 文件即状态。
Story 状态 = 它在哪个目录。变更 = 移文件。

Directories:
  backlog/    URS 扔进来，等人拆解
  planning/   Planning 沙箱正在拆解
  ready/      拆好的 Story，等 Orchestrator 调度
  running/    正在跑的执行沙箱
  blocked/    [HUMAN] checkpoint 等人
  done/       PR 已合并

Usage:
  python board.py --move SHOP-006 ready --to running
  python board.py --report
  python board.py --next        # Find next dispatchable story
"""
import os
import sys
import shutil
import time
from pathlib import Path

BRAIN_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "minishop-brain")
BOARD_DIR = os.path.join(BRAIN_DIR, ".ai", "board")

STAGES = ["backlog", "planning", "ready", "running", "blocked", "done"]

# Story frontmatter fields to read
REQUIRED_FIELDS = ["story", "priority", "agents"]


def ensure_board():
    """Create all stage directories if missing."""
    for stage in STAGES:
        d = os.path.join(BOARD_DIR, stage)
        os.makedirs(d, exist_ok=True)


def move_story(story_file: str, to_stage: str) -> bool:
    """Move a story file between stages. Returns True on success."""
    ensure_board()

    # Find current location
    src = None
    for stage in STAGES:
        candidate = os.path.join(BOARD_DIR, stage, story_file)
        if os.path.exists(candidate):
            src = candidate
            break

    if src is None:
        print(f"ERROR: Story '{story_file}' not found in any stage")
        return False

    dst = os.path.join(BOARD_DIR, to_stage, story_file)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    print(f"[{story_file}] {os.path.basename(os.path.dirname(src))} -> {to_stage}")
    return True


def scan_stage(stage: str) -> list:
    """List all story files in a stage, sorted by priority then name."""
    d = os.path.join(BOARD_DIR, stage)
    if not os.path.isdir(d):
        return []

    files = [f for f in os.listdir(d) if f.endswith(".md") and f != ".gitkeep"]

    # Parse priority for sorting
    def priority_key(f):
        filepath = os.path.join(d, f)
        with open(filepath, "r", encoding="utf-8") as fp:
            content = fp.read()
        prio = "P9"
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if line.strip().startswith("priority:"):
                        prio = line.split(":", 1)[1].strip()
                        break
        return prio

    return sorted(files, key=priority_key)


def parse_deps(story_file: str, stage: str = None) -> list:
    """Parse depends_on from story frontmatter."""
    # Find the file
    if stage:
        filepath = os.path.join(BOARD_DIR, stage, story_file)
    else:
        filepath = None
        for s in STAGES:
            candidate = os.path.join(BOARD_DIR, s, story_file)
            if os.path.exists(candidate):
                filepath = candidate
                break
    if not filepath or not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        return []

    parts = content.split("---", 2)
    if len(parts) < 3:
        return []

    for line in parts[1].strip().split("\n"):
        if line.strip().startswith("depends_on:"):
            deps_str = line.split(":", 1)[1].strip()
            return [d.strip() for d in deps_str.replace("[", "").replace("]", "").split(",") if d.strip()]
    return []


def find_next_dispatchable() -> dict:
    """Find the next ready story whose dependencies are all satisfied."""
    ensure_board()
    ready = scan_stage("ready")
    done_set = set(f.replace(".md", "") for f in scan_stage("done"))

    for story_file in ready:
        deps = parse_deps(story_file, "ready")
        satisfied = all(d in done_set for d in deps)

        if satisfied:
            filepath = os.path.join(BOARD_DIR, "ready", story_file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return {
                "file": story_file,
                "deps": deps,
                "deps_satisfied": True,
                "content_preview": content[:200],
            }

    # Find blocked stories for reporting
    blocked = []
    for story_file in ready:
        deps = parse_deps(story_file, "ready")
        unsatisfied = [d for d in deps if d not in done_set]
        if unsatisfied:
            blocked.append({"file": story_file, "waiting_on": unsatisfied})

    return {
        "file": None,
        "deps": [],
        "deps_satisfied": False,
        "blocked_stories": blocked,
    }


def report() -> str:
    """Generate human-readable board report."""
    ensure_board()
    lines = [f"=== Board Report ({time.strftime('%H:%M:%S')}) ===", ""]

    counts = {}
    for stage in STAGES:
        files = scan_stage(stage)
        counts[stage] = len(files)

        emoji = {"backlog": "[ ]", "planning": "[~]", "ready": "[>]", "running": "[R]", "blocked": "[!]", "done": "[x]"}.get(stage, "?")

        if files:
            lines.append(f"{emoji} {stage} ({len(files)})")
            for f in files[:5]:  # Show max 5 per stage
                lines.append(f"    - {f}")
            if len(files) > 5:
                lines.append(f"    ... +{len(files) - 5} more")

    lines.append("")
    lines.append(f"Total: {sum(counts.values())} stories | "
                 f"Backlog: {counts['backlog']} | "
                 f"Ready: {counts['ready']} | "
                 f"Running: {counts['running']} | "
                 f"Done: {counts['done']}")

    # Show dispatchable
    next_up = find_next_dispatchable()
    if next_up.get("file"):
        lines.append(f"\nNext dispatchable: {next_up['file']}")
    elif next_up.get("blocked_stories"):
        lines.append("\nBlocked (waiting on deps):")
        for b in next_up["blocked_stories"]:
            lines.append(f"  {b['file']} -> waiting: {b['waiting_on']}")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kanban board state machine")
    parser.add_argument("--init", action="store_true", help="Initialize board directories")
    parser.add_argument("--move", nargs=2, metavar=("STORY", "STAGE"), help="Move story to stage")
    parser.add_argument("--from", dest="from_stage", help="Source stage (for --move)")
    parser.add_argument("--report", action="store_true", help="Print board report")
    parser.add_argument("--next", action="store_true", help="Find next dispatchable story")
    args = parser.parse_args()

    if args.init:
        ensure_board()
        print(f"Board initialized at {BOARD_DIR}")
        report()

    if args.move:
        move_story(args.move[0], args.move[1])

    if args.report:
        print(report())

    if args.next:
        n = find_next_dispatchable()
        if n.get("file"):
            print(f"DISPATCH: {n['file']}")
        else:
            print("No dispatchable stories ready")
            if n.get("blocked_stories"):
                for b in n["blocked_stories"]:
                    print(f"  BLOCKED: {b['file']} -> {b['waiting_on']}")
