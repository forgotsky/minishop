#!/usr/bin/env python3
"""
Memory Summarization Utility

Summarizes agent memory files to prevent unbounded growth.
Uses simple heuristics to identify and consolidate similar entries.

Usage:
    python3 memory_summarize.py [agent_name] [--dry-run] [--max-entries 50]
    python3 memory_summarize.py --all [--dry-run] [--max-entries 50]

Examples:
    python3 memory_summarize.py dev                    # Summarize dev agent memory
    python3 memory_summarize.py --all                  # Summarize all agents
    python3 memory_summarize.py dev --dry-run          # Preview without changes
    python3 memory_summarize.py dev --max-entries 30   # Keep max 30 entries
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Find project root
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
MEMORY_DIR = PROJECT_ROOT / ".automation" / "memory"

# Pre-compiled regex patterns for performance
_ENTRY_WITH_TIMESTAMP_RE = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}):\s*(.+)$")
_ENTRY_WITHOUT_TIMESTAMP_RE = re.compile(r"^-\s*(.+)$")


def parse_memory_entry(line: str) -> tuple[Optional[datetime], str]:
    """Parse a memory entry line into timestamp and content."""
    # Format: - YYYY-MM-DD HH:MM: content
    match = _ENTRY_WITH_TIMESTAMP_RE.match(line.strip())
    if match:
        try:
            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M")
            return timestamp, match.group(2).strip()
        except ValueError:
            pass

    # Format without timestamp: - content
    match = _ENTRY_WITHOUT_TIMESTAMP_RE.match(line.strip())
    if match:
        return None, match.group(1).strip()

    return None, line.strip()


def categorize_entry(content: str) -> str:
    """Categorize a memory entry by its content."""
    content_lower = content.lower()

    # Error/bug related
    if any(word in content_lower for word in ["error", "bug", "fix", "crash", "issue", "fail"]):
        return "errors"

    # Preference/style related
    if any(
        word in content_lower for word in ["prefer", "style", "convention", "pattern", "approach"]
    ):
        return "preferences"

    # Code/implementation related
    if any(
        word in content_lower
        for word in ["implement", "code", "function", "class", "module", "file"]
    ):
        return "implementation"

    # Testing related
    if any(word in content_lower for word in ["test", "spec", "coverage", "assert"]):
        return "testing"

    # Architecture/design related
    if any(
        word in content_lower for word in ["architect", "design", "structure", "pattern", "layer"]
    ):
        return "architecture"

    # Performance related
    if any(
        word in content_lower
        for word in ["performance", "optimize", "slow", "fast", "memory", "cache"]
    ):
        return "performance"

    # Documentation related
    if any(word in content_lower for word in ["doc", "readme", "comment", "explain"]):
        return "documentation"

    return "general"


def similarity_score(entry1: str, entry2: str) -> float:
    """Calculate simple similarity between two entries."""
    words1 = set(entry1.lower().split())
    words2 = set(entry2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def find_duplicates(
    entries: list[tuple[Optional[datetime], str]], threshold: float = 0.7
) -> list[list[int]]:
    """Find groups of similar entries."""
    groups = []
    used = set()

    for i, (_, content1) in enumerate(entries):
        if i in used:
            continue

        group = [i]
        for j, (_, content2) in enumerate(entries[i + 1 :], start=i + 1):
            if j in used:
                continue

            if similarity_score(content1, content2) >= threshold:
                group.append(j)
                used.add(j)

        if len(group) > 1:
            groups.append(group)
            used.add(i)

    return groups


def summarize_group(entries: list[tuple[Optional[datetime], str]]) -> str:
    """Create a summary for a group of similar entries."""
    if not entries:
        return ""

    # Keep the most recent entry's content
    sorted_entries = sorted(entries, key=lambda x: x[0] or datetime.min, reverse=True)
    most_recent = sorted_entries[0][1]

    if len(entries) > 2:
        return f"{most_recent} (noted {len(entries)} times)"
    return most_recent


def load_memory_file(agent_name: str) -> list[str]:
    """Load memory file contents."""
    memory_file = MEMORY_DIR / f"{agent_name}.memory.md"

    if not memory_file.exists():
        return []

    with open(memory_file) as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def save_memory_file(agent_name: str, lines: list[str]) -> None:
    """Save memory file contents."""
    memory_file = MEMORY_DIR / f"{agent_name}.memory.md"

    with open(memory_file, "w") as f:
        f.write("\n".join(lines) + "\n")


def summarize_agent_memory(agent_name: str, max_entries: int = 50, dry_run: bool = False) -> dict:
    """Summarize an agent's memory file."""
    lines = load_memory_file(agent_name)

    if not lines:
        return {"agent": agent_name, "status": "empty", "original": 0, "final": 0}

    # Parse entries
    entries = [parse_memory_entry(line) for line in lines]

    result = {
        "agent": agent_name,
        "original": len(entries),
        "categories": defaultdict(int),
        "duplicates_found": 0,
        "final": 0,
        "changes": [],
    }

    # Categorize entries
    for _, content in entries:
        category = categorize_entry(content)
        result["categories"][category] += 1

    # Find and consolidate duplicates
    duplicate_groups = find_duplicates(entries)
    result["duplicates_found"] = sum(len(g) - 1 for g in duplicate_groups)

    # Build new entry list
    indices_to_remove = set()
    summaries = []

    for group in duplicate_groups:
        group_entries = [entries[i] for i in group]
        summary = summarize_group(group_entries)
        most_recent_time = max((e[0] for e in group_entries if e[0]), default=None)
        summaries.append((most_recent_time, summary))
        indices_to_remove.update(group)
        result["changes"].append(f"Consolidated {len(group)} similar entries")

    # Keep non-duplicate entries
    new_entries = []
    for i, entry in enumerate(entries):
        if i not in indices_to_remove:
            new_entries.append(entry)

    # Add summaries
    new_entries.extend(summaries)

    # Sort by timestamp (most recent first for trimming)
    new_entries.sort(key=lambda x: x[0] or datetime.min, reverse=True)

    # Trim to max entries if needed
    if len(new_entries) > max_entries:
        trimmed_count = len(new_entries) - max_entries
        new_entries = new_entries[:max_entries]
        result["changes"].append(f"Trimmed {trimmed_count} oldest entries")

    # Sort back to chronological order for output
    new_entries.sort(key=lambda x: x[0] or datetime.min)

    result["final"] = len(new_entries)

    # Format output lines
    output_lines = []
    for timestamp, content in new_entries:
        if timestamp:
            output_lines.append(f"- {timestamp.strftime('%Y-%m-%d %H:%M')}: {content}")
        else:
            output_lines.append(f"- {content}")

    if not dry_run and output_lines != lines:
        save_memory_file(agent_name, output_lines)
        result["status"] = "updated"
    else:
        result["status"] = "dry-run" if dry_run else "no-change"

    return result


def get_all_agents() -> list[str]:
    """Get list of agents with memory files."""
    agents = []

    if MEMORY_DIR.exists():
        for file in MEMORY_DIR.glob("*.memory.md"):
            agent_name = file.stem.replace(".memory", "")
            agents.append(agent_name)

    return agents


def print_result(result: dict) -> None:
    """Print summarization result."""
    print(f"\n{'=' * 50}")
    print(f"Agent: {result['agent']}")
    print(f"Status: {result['status']}")

    if result["status"] == "empty":
        print("No memory entries found.")
        return

    print(f"Original entries: {result['original']}")
    print(f"Final entries: {result['final']}")

    if result.get("duplicates_found", 0) > 0:
        print(f"Duplicates consolidated: {result['duplicates_found']}")

    if result.get("categories"):
        print("\nCategories:")
        for cat, count in sorted(result["categories"].items(), key=lambda x: -x[1]):
            print(f"  - {cat}: {count}")

    if result.get("changes"):
        print("\nChanges made:")
        for change in result["changes"]:
            print(f"  - {change}")


def main():
    parser = argparse.ArgumentParser(
        description="Summarize agent memory files to prevent unbounded growth."
    )
    parser.add_argument("agent", nargs="?", help="Agent name to summarize")
    parser.add_argument("--all", action="store_true", help="Summarize all agents")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument(
        "--max-entries", type=int, default=50, help="Maximum entries to keep (default: 50)"
    )

    args = parser.parse_args()

    if not args.agent and not args.all:
        parser.print_help()
        print("\nError: Please specify an agent name or use --all")
        sys.exit(1)

    if args.all:
        agents = get_all_agents()
        if not agents:
            print("No agent memory files found.")
            sys.exit(0)

        print(f"Summarizing memory for {len(agents)} agents...")
        for agent in agents:
            result = summarize_agent_memory(agent, args.max_entries, args.dry_run)
            print_result(result)
    else:
        result = summarize_agent_memory(args.agent, args.max_entries, args.dry_run)
        print_result(result)

    if args.dry_run:
        print("\n(Dry run - no changes made)")


if __name__ == "__main__":
    main()
