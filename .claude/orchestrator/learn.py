"""
闭环学习 — 每个 Story 完成后自动提取教训
Hermes GEPA cycle: Goal -> Evaluation -> Plan -> Action -> (Review -> Learn)

Usage:
    python learn.py --extract SHOP-003  # Extract lessons from completed story
    python learn.py --context            # Generate context for next Planning session
    python learn.py --patterns           # Check for repeatable skill patterns
"""
import os
import sys
import json
import time
import re
from pathlib import Path
from collections import Counter

BRAIN_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "minishop-brain")
LEARNINGS_DIR = os.path.join(BRAIN_DIR, ".ai", "learnings")
SKILLS_DIR = os.path.join(BRAIN_DIR, ".ai", "skills")
PATTERNS_FILE = os.path.join(BRAIN_DIR, ".ai", "patterns.json")


def ensure_dirs():
    for d in [LEARNINGS_DIR, SKILLS_DIR]:
        os.makedirs(d, exist_ok=True)


def extract_lessons(story_key: str, notes: str = "", mistakes: list = None, wins: list = None):
    """Write a learning file after story completion."""
    ensure_dirs()
    today = time.strftime("%Y-%m-%d")
    filename = f"{today}-{story_key}.md"
    filepath = os.path.join(LEARNINGS_DIR, filename)

    lines = [
        f"# {story_key} 复盘",
        f"",
        f"日期: {today}",
        f"",
        f"## 做对了什么",
    ]
    for w in (wins or ["无记录"]):
        lines.append(f"- {w}")

    lines.append("")
    lines.append("## 做错了什么 / 下次改进")
    for m in (mistakes or ["无记录"]):
        lines.append(f"- {m}")

    if notes:
        lines.append("")
        lines.append(f"## 备注\n{notes}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return filepath


def recent_learnings(limit: int = 5) -> list:
    """Get the N most recent learning files for Planning context."""
    ensure_dirs()
    files = sorted(
        [f for f in os.listdir(LEARNINGS_DIR) if f.endswith(".md")],
        reverse=True
    )[:limit]

    results = []
    for f in files:
        filepath = os.path.join(LEARNINGS_DIR, f)
        with open(filepath, "r", encoding="utf-8") as fp:
            content = fp.read()
        # Extract mistakes section (what to avoid)
        mistakes = []
        in_mistakes = False
        for line in content.split("\n"):
            if "做错了什么" in line or "下次改进" in line:
                in_mistakes = True
                continue
            if line.startswith("##"):
                in_mistakes = False
            if in_mistakes and line.startswith("- "):
                mistakes.append(line[2:])

        results.append({
            "file": f,
            "story": f.replace(".md", "").split("-", 2)[-1] if "-" in f else f,
            "mistakes": mistakes,
        })
    return results


def learning_context() -> str:
    """Generate context text to inject into next Planning session.
    Tells the planner: 'in past stories, these things went wrong — avoid them'.
    """
    learnings = recent_learnings(limit=5)
    if not learnings:
        return "[无历史教训]"

    lines = ["## 历史教训（来自最近 5 个 Story）", ""]
    for l in learnings:
        if l["mistakes"]:
            lines.append(f"**{l['story']}** 的教训:")
            for m in l["mistakes"]:
                lines.append(f"  - {m}")
    return "\n".join(lines)


# ============================================================
# 技能自进化：重复模式检测 + Skill 模板生成
# ============================================================

def load_patterns() -> dict:
    """Load pattern tracking data."""
    if os.path.exists(PATTERNS_FILE):
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sequences": [], "skills_generated": []}


def save_patterns(data: dict):
    """Save pattern tracking data."""
    with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_workflow(story_key: str, agent_sequence: list):
    """Record a workflow execution pattern.
    If same sequence appears 3+ times, flag for skill generation.
    """
    data = load_patterns()
    seq_str = " -> ".join(agent_sequence)

    data["sequences"].append({
        "story": story_key,
        "sequence": agent_sequence,
        "hash": seq_str,
        "timestamp": int(time.time()),
    })

    # Keep only last 50
    data["sequences"] = data["sequences"][-50:]

    # Check for repeat patterns
    seq_counts = Counter(s["hash"] for s in data["sequences"])
    for seq_hash, count in seq_counts.items():
        if count >= 3 and seq_hash not in data.get("skills_generated", []):
            generate_skill_from_pattern(seq_hash, agent_sequence)
            data.setdefault("skills_generated", []).append(seq_hash)

    save_patterns(data)


def generate_skill_from_pattern(seq_hash: str, agents: list):
    """Generate a reusable SKILL.md from a repeated workflow pattern."""
    ensure_dirs()
    skill_name = f"workflow-{len(agents)}-agents"

    # Determine skill description from agent sequence
    agent_roles = {
        "backend-dev": "FastAPI backend development",
        "miniprogram-dev": "WeChat mini-program frontend",
        "tester": "pytest + httpx testing",
        "reviewer": "code review and security check",
        "planner": "task planning and decomposition",
        "architect": "technical architecture design",
    }

    steps = []
    for i, agent in enumerate(agents, 1):
        role_desc = agent_roles.get(agent, agent)
        steps.append(f"Step {i}: {agent} — {role_desc}")

    skill_content = f"""---
name: {skill_name}
description: Auto-generated workflow pattern — {seq_hash}
metadata:
  type: workflow
  auto_generated: true
  trigger_count: 3
---

# {skill_name}

Auto-generated from repeated workflow pattern.

## Agent Sequence
{chr(10).join(f'- {a}' for a in agents)}

## Steps
{chr(10).join(steps)}

## Usage
Trigger this workflow when a task requires: {", ".join(agents)}.
"""

    filepath = os.path.join(SKILLS_DIR, f"{skill_name}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(skill_content)

    print(f"[Skill Auto-Generated] {skill_name} -> {filepath}")


def check_patterns():
    """Check for patterns ready for skill generation."""
    data = load_patterns()
    seq_counts = Counter(s["hash"] for s in data["sequences"])
    results = []
    for seq_hash, count in seq_counts.most_common():
        already_generated = seq_hash in data.get("skills_generated", [])
        results.append({
            "pattern": seq_hash,
            "count": count,
            "ready": count >= 3 and not already_generated,
            "already_done": already_generated,
        })
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Closed-loop learning + skill evolution")
    parser.add_argument("--extract", metavar="STORY", help="Extract lessons (prompts interactively)")
    parser.add_argument("--context", action="store_true", help="Print learning context for Planning")
    parser.add_argument("--record", nargs="+", metavar=("STORY", "AGENTS..."),
                        help="Record workflow: STORY agent1 agent2 agent3...")
    parser.add_argument("--patterns", action="store_true", help="Check pattern readiness")
    args = parser.parse_args()

    if args.context:
        print(learning_context())

    if args.patterns:
        results = check_patterns()
        if not results:
            print("No patterns recorded yet.")
        for r in results:
            tag = "[READY for skill]" if r["ready"] else ("[generated]" if r["already_done"] else "")
            print(f"  {r['pattern']} x{r['count']} {tag}")

    if args.record:
        story = args.record[0]
        agents = args.record[1:]
        record_workflow(story, agents)
        print(f"Recorded: {story} -> {' -> '.join(agents)}")
