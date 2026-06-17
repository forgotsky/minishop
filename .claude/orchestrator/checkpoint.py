"""
Checkpoint system — save/resume workflow state.
Herme's Phase 2 pattern: every step writes a snapshot, resume from last save.
"""
import os
import json
import time
from pathlib import Path

BRAIN_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "minishop-brain")


def checkpoint_dir(story_key: str) -> str:
    """Get checkpoint directory for a story."""
    d = os.path.join(BRAIN_DIR, ".ai", "checkpoints", story_key)
    os.makedirs(d, exist_ok=True)
    return d


def save(story_key: str, step: str, state: dict) -> str:
    """Save checkpoint after completing a step.

    Args:
        story_key: e.g. "SHOP-006-A"
        step: e.g. "backend-dev", "tester", "reviewer"
        state: {status, output_file, commit_hash, ...}

    Returns checkpoint file path.
    """
    d = checkpoint_dir(story_key)
    ts = int(time.time())
    filename = f"{step}-{ts}.json"
    filepath = os.path.join(d, filename)

    checkpoint = {
        "story": story_key,
        "step": step,
        "timestamp": ts,
        "state": state,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)

    return filepath


def load(story_key: str) -> dict:
    """Load the latest checkpoint for a story.
    Returns {completed_steps: [...], last_step: str, last_state: dict}
    """
    d = checkpoint_dir(story_key)
    if not os.path.isdir(d):
        return {"completed_steps": [], "last_step": None, "last_state": None}

    completed = []
    last = None

    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            filepath = os.path.join(d, f)
            with open(filepath, "r", encoding="utf-8") as fp:
                cp = json.load(fp)
            step_name = cp.get("step", f)
            completed.append(step_name)
            last = cp

    return {
        "completed_steps": completed,
        "last_step": last.get("step") if last else None,
        "last_state": last.get("state") if last else None,
    }


def resume_context(story_key: str) -> str:
    """Generate context text for resuming a story.
    Tells the agent: 'you already did X, Y, Z — now continue from here'.
    """
    state = load(story_key)
    if not state["completed_steps"]:
        return f"[新任务] {story_key}"

    lines = [
        f"[恢复] {story_key}",
        f"已完成步骤: {', '.join(state['completed_steps'])}",
    ]
    if state["last_state"]:
        ls = state["last_state"]
        if "output_file" in ls:
            lines.append(f"上一步产出: {ls['output_file']}")
        if "commit_hash" in ls:
            lines.append(f"代码提交: {ls['commit_hash'][:8]}")
        if "notes" in ls:
            lines.append(f"备注: {ls['notes']}")
    lines.append("请从上次断点继续。")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", nargs=2, metavar=("STORY", "STEP"), help="Save checkpoint")
    parser.add_argument("--load", metavar="STORY", help="Load latest checkpoint")
    parser.add_argument("--resume", metavar="STORY", help="Generate resume context")
    args = parser.parse_args()

    if args.save:
        path = save(args.save[0], args.save[1], {"notes": "manual save"})
        print(f"Checkpoint saved: {path}")

    if args.load:
        state = load(args.load)
        print(json.dumps(state, indent=2, ensure_ascii=False))

    if args.resume:
        print(resume_context(args.resume))
