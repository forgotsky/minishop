"""
Orchestrator auto-dispatch — 串联 Phase 1/2/3 所有功能
Herme's pattern: validate → dispatch → checkpoint → judge → pass result

Usage:
    python auto-dispatch.py --scan        # Scan board, dispatch ready tasks
    python auto-dispatch.py --story SHOP-006-A  # Process one story
"""
import os
import sys
import json
import time

# Add orchestrator to path
sys.path.insert(0, os.path.dirname(__file__))

from validate import validate_story, validate_board
from checkpoint import save as save_checkpoint, load as load_checkpoint, resume_context
from dispatch import write_output, read_output, manifest_for_prompt, output_path

BRAIN_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "minishop-brain")
TASKS_DIR = os.path.join(BRAIN_DIR, ".ai", "tasks")
OUTPUTS_DIR = os.path.join(BRAIN_DIR, ".ai", "outputs")
CHECKPOINTS_DIR = os.path.join(BRAIN_DIR, ".ai", "checkpoints")


def scan_and_report() -> dict:
    """Scan brain tasks, validate, return dispatchable stories."""
    # Ensure dirs exist
    for d in [TASKS_DIR, OUTPUTS_DIR, CHECKPOINTS_DIR]:
        os.makedirs(d, exist_ok=True)

    # Validate all stories
    validation = validate_board(TASKS_DIR)

    # Filter: only PASS or WARN stories are dispatchable
    ready = []
    for detail in validation.get("details", []):
        if detail["status"] != "REJECT":
            ready.append(detail["file"])

    # Check DAG dependencies
    dispatchable = []
    blocked_by_dep = []
    for story_file in ready:
        story_key = story_file.replace(".md", "")
        filepath = os.path.join(TASKS_DIR, story_file)

        # Parse depends_on from frontmatter
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        deps = []
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if line.strip().startswith("depends_on:"):
                        deps_str = line.split(":", 1)[1].strip()
                        deps = [d.strip() for d in deps_str.replace("[","").replace("]","").split(",") if d.strip()]

        # Check if all deps are satisfied (have outputs)
        deps_ok = True
        for dep in deps:
            dep_output = output_path(dep)
            if not os.path.exists(dep_output):
                deps_ok = False
                break

        if deps_ok:
            dispatchable.append(story_file)
        else:
            blocked_by_dep.append({
                "story": story_file,
                "waiting_on": [d for d in deps if not os.path.exists(output_path(d))],
            })

    return {
        "validation": validation,
        "dispatchable": dispatchable,
        "blocked_by_dep": blocked_by_dep,
        "timestamp": int(time.time()),
    }


def dispatch_context(story_file: str) -> dict:
    """Generate the full context needed to dispatch a story.
    Includes: upstream results + checkpoint resume + validation report.
    """
    story_key = story_file.replace(".md", "")
    filepath = os.path.join(TASKS_DIR, story_file)

    # Read story
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse depends_on
    deps = []
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if line.strip().startswith("depends_on:"):
                    deps_str = line.split(":", 1)[1].strip()
                    deps = [d.strip() for d in deps_str.replace("[","").replace("]","").split(",") if d.strip()]

    # Collect upstream outputs
    upstream_context = ""
    for dep in deps:
        result = read_output(dep)
        if result:
            upstream_context += f"\n### 依赖 {dep} 的产出\n{result}\n"

    # Check for existing checkpoints (resume)
    resume = resume_context(story_key) if story_key else ""

    return {
        "story_key": story_key,
        "content": content,
        "upstream": upstream_context,
        "resume": resume,
        "dependencies": deps,
        "manifest": manifest_for_prompt(),
    }


def print_report():
    """Print a human-readable board report."""
    report = scan_and_report()
    v = report["validation"]

    print(f"=== Board Report ({time.strftime('%H:%M:%S')}) ===")
    print(f"Total stories: {v['total']}")
    print(f"  PASS: {v['pass']}  WARN: {v['warn']}  REJECT: {v['reject']}")
    print()

    if report["dispatchable"]:
        print(f"Ready ({len(report['dispatchable'])}):")
        for s in report["dispatchable"]:
            print(f"  [OK] {s}")
    else:
        print("Ready: none")

    if report["blocked_by_dep"]:
        print(f"\nBlocked ({len(report['blocked_by_dep'])}):")
        for b in report["blocked_by_dep"]:
            print(f"  [BLOCKED] {b['story']} -> waiting: {b['waiting_on']}")

    if v["reject"] > 0:
        print(f"\nRejected ({v['reject']}):")
        for d in v["details"]:
            if d["status"] == "REJECT":
                for e in d.get("errors", []):
                    print(f"  [REJECT] {d['file']}: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Orchestrator auto-dispatch")
    parser.add_argument("--scan", action="store_true", help="Scan and print board report")
    parser.add_argument("--dispatch", metavar="STORY_FILE", help="Generate dispatch context for a story")
    parser.add_argument("--checkpoint", nargs=2, metavar=("STORY", "STEP"), help="Save checkpoint")
    parser.add_argument("--done", nargs=2, metavar=("STORY", "SUMMARY"), help="Mark story done, write output")
    args = parser.parse_args()

    if args.scan:
        print_report()

    if args.dispatch:
        ctx = dispatch_context(args.dispatch)
        print(f"# Dispatch: {ctx['story_key']}")
        print(ctx['upstream'])
        print(ctx['resume'])
        print(f"\n{ctx['manifest']}")
        print(f"\n--- Story Content ---\n{ctx['content'][:500]}")

    if args.checkpoint:
        save_checkpoint(args.checkpoint[0], args.checkpoint[1], {"timestamp": int(time.time())})
        print(f"Checkpoint: {args.checkpoint[0]}/{args.checkpoint[1]}")

    if args.done:
        write_output(args.done[0], args.done[1])
        print(f"Done: {args.done[0]} → output.md written")
