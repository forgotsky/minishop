"""
Pre-flight validation for story files.
Runs BEFORE dispatch — REJECT invalid tasks, WARN on suspicious patterns.
Herme's Phase 1 pattern: fail fast, never dispatch garbage.
"""
import os
import sys
import json
import re
from pathlib import Path

BRAIN_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "minishop-brain")

# Known agent types (sync with .ai/agents/pool.md)
KNOWN_AGENTS = {
    "planner", "backend-dev", "miniprogram-dev", "tester",
    "reviewer", "business-analyst", "product-manager", "architect",
    "devops-engineer", "maintainer", "tech-writer", "scrum-master",
}

# Valid priority values
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}

# Valid status values
VALID_STATUSES = {"backlog", "ready", "in-progress", "blocked", "done", "cancelled"}


def validate_story(filepath: str) -> dict:
    """Validate a single story file. Returns {status, errors, warnings}."""
    errors = []
    warnings = []

    if not os.path.exists(filepath):
        return {"status": "REJECT", "errors": ["File not found"], "warnings": []}

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # ── Parse frontmatter ──
    fm = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, val = line.partition(":")
                    fm[key.strip()] = val.strip()

    # ── Required fields ──
    priority = fm.get("priority", "")
    if priority not in VALID_PRIORITIES:
        errors.append(f"REJECT: invalid or missing priority '{priority}'. Must be {VALID_PRIORITIES}")

    agents_raw = fm.get("agents", "")
    agents = []
    if not agents_raw:
        errors.append("REJECT: missing 'agents' field")
    else:
        agents = [a.strip() for a in agents_raw.replace("[", "").replace("]", "").split(",")]
        unknown = [a for a in agents if a not in KNOWN_AGENTS]
        if unknown:
            errors.append(f"REJECT: unknown agent types: {unknown}")

    if len(agents) == 0 and not errors:
        warnings.append("WARNING: no agents assigned to this task")

    # ── Content checks ──
    if "## 步骤" not in content and "## Steps" not in content:
        warnings.append("WARNING: no '## 步骤' or '## Steps' section found")

    has_checklist = bool(re.search(r'- \[ \]', content))
    has_human = bool(re.search(r'\[HUMAN\]', content, re.IGNORECASE))
    if not has_checklist:
        warnings.append("WARNING: no checkbox items (- [ ]) found")
    if not has_human and len(agents) > 0:
        warnings.append("WARNING: no [HUMAN] checkpoint — will run to completion without review")

    # ── DAG reference check ──
    deps = fm.get("depends_on", "")
    if deps:
        deps_clean = deps.replace("[", "").replace("]", "")
        for dep in deps_clean.split(","):
            dep = dep.strip()
            if dep:
                dep_file = os.path.join(os.path.dirname(filepath), f"{dep}.md")
                if not os.path.exists(dep_file):
                    errors.append(f"REJECT: depends_on '{dep}' not found")

    # ── Cycle detection ──
    if not errors and not has_cycle(filepath, visited=set()):
        pass  # No cycle
    elif not errors:
        # has_cycle already added errors
        pass

    # ── Determine status ──
    if errors:
        status = "REJECT"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    return {"status": status, "errors": errors, "warnings": warnings}


def has_cycle(filepath: str, visited: set = None, path: list = None) -> bool:
    """DFS cycle detection on DAG dependency graph.
    Returns True if a cycle is found (adds to global errors via add_cycle_error).
    """
    if visited is None:
        visited = set()
    if path is None:
        path = []

    story_key = os.path.basename(filepath).replace(".md", "")
    board_dir = os.path.dirname(os.path.dirname(filepath))

    if story_key in path:
        cycle_path = " -> ".join(path[path.index(story_key):] + [story_key])
        return True  # Cycle found (error added in validate_board)

    if story_key in visited:
        return False

    visited.add(story_key)
    path.append(story_key)

    # Read depends_on
    deps = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if line.strip().startswith("depends_on:"):
                        deps_str = line.split(":", 1)[1].strip()
                        deps = [d.strip() for d in deps_str.replace("[", "").replace("]", "").split(",") if d.strip()]

    for dep in deps:
        dep_file = os.path.join(os.path.dirname(filepath), f"{dep}.md")
        if os.path.exists(dep_file):
            if has_cycle(dep_file, visited, path):
                cycle_path = " -> ".join(path[path.index(dep):] + [dep])
                return True

    path.pop()
    return False


def validate_board(board_dir: str = None) -> dict:
    """Scan board/ready/ and validate all stories. Returns report."""
    if board_dir is None:
        board_dir = os.path.join(BRAIN_DIR, ".ai", "tasks")

    report = {"total": 0, "pass": 0, "warn": 0, "reject": 0, "details": []}

    if not os.path.isdir(board_dir):
        return report

    for f in sorted(os.listdir(board_dir)):
        if f.startswith("SHOP-") and f.endswith(".md") and f != "PENDING.md":
            filepath = os.path.join(board_dir, f)
            result = validate_story(filepath)
            result["file"] = f
            report["details"].append(result)
            report["total"] += 1
            if result["status"] == "REJECT":
                report["reject"] += 1
            elif result["status"] == "WARN":
                report["warn"] += 1
            else:
                report["pass"] += 1

    # ── Global cycle detection (cross-story) ──
    visited = set()
    for f in sorted(os.listdir(board_dir)):
        if f.startswith("SHOP-") and f.endswith(".md") and f != "PENDING.md":
            filepath = os.path.join(board_dir, f)
            story_key = f.replace(".md", "")
            if story_key not in visited:
                if has_cycle(filepath, visited, []):
                    # Find the report entry and mark it REJECT
                    for detail in report["details"]:
                        if detail["file"] == f:
                            detail.setdefault("errors", []).append("REJECT: circular dependency detected")
                            if detail["status"] != "REJECT":
                                detail["status"] = "REJECT"
                                report["reject"] += 1
                                if detail["status"] == "WARN":
                                    report["warn"] -= 1
                                elif detail["status"] == "PASS":
                                    report["pass"] -= 1

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Validate a single story file")
    parser.add_argument("--board", help="Validate entire board directory")
    args = parser.parse_args()

    if args.file:
        result = validate_story(args.file)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] != "REJECT" else 1)

    if args.board:
        report = validate_board(args.board)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(0 if report["reject"] == 0 else 1)
