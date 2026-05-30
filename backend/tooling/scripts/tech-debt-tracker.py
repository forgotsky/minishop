#!/usr/bin/env python3
"""
Tech Debt Tracker - Technical Debt Metrics and Reporting

This script scans the codebase for technical debt indicators and generates
comprehensive reports. It tracks:
  - TODO/FIXME/HACK comments
  - Tech debt documentation files
  - Code complexity indicators
  - Outdated dependencies
  - Missing tests

Usage:
    python tech-debt-tracker.py                    # Full report
    python tech-debt-tracker.py --scan             # Scan for debt indicators
    python tech-debt-tracker.py --report           # Generate markdown report
    python tech-debt-tracker.py --dashboard        # Show interactive dashboard
    python tech-debt-tracker.py --json             # Output as JSON
    python tech-debt-tracker.py --trend            # Show trend over time
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.colors import Colors

# Debt indicator patterns
DEBT_PATTERNS = {
    "TODO": {
        "pattern": r"\b(TODO|@todo)\b[:\s]*(.*?)(?:\n|$)",
        "severity": "low",
        "category": "planned-work",
    },
    "FIXME": {
        "pattern": r"\b(FIXME|@fixme)\b[:\s]*(.*?)(?:\n|$)",
        "severity": "medium",
        "category": "bugs",
    },
    "HACK": {
        "pattern": r"\b(HACK|@hack|WORKAROUND)\b[:\s]*(.*?)(?:\n|$)",
        "severity": "high",
        "category": "code-quality",
    },
    "XXX": {
        "pattern": r"\bXXX\b[:\s]*(.*?)(?:\n|$)",
        "severity": "high",
        "category": "critical",
    },
    "DEPRECATED": {
        "pattern": r"\b(DEPRECATED|@deprecated)\b[:\s]*(.*?)(?:\n|$)",
        "severity": "medium",
        "category": "maintenance",
    },
    "REFACTOR": {
        "pattern": r"\b(REFACTOR|NEEDS[_\s]REFACTOR)\b[:\s]*(.*?)(?:\n|$)",
        "severity": "medium",
        "category": "code-quality",
    },
    "TECH_DEBT": {
        "pattern": r"\b(TECH[_\s]?DEBT|TECHNICAL[_\s]?DEBT)\b[:\s]*(.*?)(?:\n|$)",
        "severity": "high",
        "category": "architecture",
    },
    "OPTIMIZE": {
        "pattern": r"\b(OPTIMIZE|PERF|PERFORMANCE)\b[:\s]*(.*?)(?:\n|$)",
        "severity": "low",
        "category": "performance",
    },
}

# File extensions to scan
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".dart",
    ".java",
    ".kt",
    ".swift",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".yaml",
    ".yml",
    ".json",
    ".md",
}

# Directories to skip
SKIP_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".cache",
    "build",
    "dist",
    ".dart_tool",
    ".pub",
    "coverage",
    ".idea",
    ".vscode",
    "vendor",
}


@dataclass
class DebtItem:
    """A single technical debt item."""

    file_path: str
    line_number: int
    debt_type: str
    severity: str
    category: str
    message: str
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file_path,
            "line": self.line_number,
            "type": self.debt_type,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "context": self.context,
        }


@dataclass
class DebtReport:
    """Complete tech debt report."""

    scan_date: str
    project_path: str
    items: list[DebtItem] = field(default_factory=list)
    documented_debt: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.items)

    @property
    def by_severity(self) -> dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for item in self.items:
            if item.severity in counts:
                counts[item.severity] += 1
        return counts

    @property
    def by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            counts[item.category] = counts.get(item.category, 0) + 1
        return counts

    @property
    def by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            counts[item.debt_type] = counts.get(item.debt_type, 0) + 1
        return counts

    @property
    def debt_score(self) -> int:
        """Calculate a debt score (lower is better)."""
        weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        score = 0
        for item in self.items:
            score += weights.get(item.severity, 1)
        return score

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_date": self.scan_date,
            "project_path": self.project_path,
            "summary": {
                "total_items": self.total_count,
                "debt_score": self.debt_score,
                "by_severity": self.by_severity,
                "by_category": self.by_category,
                "by_type": self.by_type,
            },
            "items": [item.to_dict() for item in self.items],
            "documented_debt": self.documented_debt,
        }


class TechDebtTracker:
    """Main tracker class."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.history_file = project_path / "tooling" / ".automation" / "debt-history.json"

    def scan_file(self, file_path: Path) -> list[DebtItem]:
        """Scan a single file for debt indicators."""
        items: list[DebtItem] = []

        try:
            content = file_path.read_text(errors="ignore")
            lines = content.split("\n")

            for debt_type, config in DEBT_PATTERNS.items():
                pattern = re.compile(config["pattern"], re.IGNORECASE | re.MULTILINE)

                for match in pattern.finditer(content):
                    # Find line number
                    line_start = content[: match.start()].count("\n") + 1

                    # Extract message
                    groups = match.groups()
                    message = groups[-1].strip() if groups else ""

                    # Get context (the line itself)
                    context = lines[line_start - 1].strip() if line_start <= len(lines) else ""

                    items.append(
                        DebtItem(
                            file_path=str(file_path.relative_to(self.project_path)),
                            line_number=line_start,
                            debt_type=debt_type,
                            severity=config["severity"],
                            category=config["category"],
                            message=message[:200],  # Limit message length
                            context=context[:200],
                        )
                    )

        except Exception:
            pass  # Skip files that can't be read

        return items

    def scan_directory(self, path: Path) -> list[DebtItem]:
        """Recursively scan a directory for debt indicators."""
        items: list[DebtItem] = []

        for item in path.iterdir():
            if item.name.startswith("."):
                continue

            if item.is_dir():
                if item.name not in SKIP_DIRS:
                    items.extend(self.scan_directory(item))
            elif item.is_file():
                if item.suffix in CODE_EXTENSIONS:
                    items.extend(self.scan_file(item))

        return items

    def find_documented_debt(self) -> list[dict[str, Any]]:
        """Find formally documented tech debt files."""
        documented: list[dict[str, Any]] = []

        # Look for tech debt templates
        self.project_path / "tooling" / "docs" / "templates"
        debt_pattern = re.compile(r"(tech[_-]?debt|DEBT)", re.IGNORECASE)

        # Search common locations
        search_paths = [
            self.project_path / "docs",
            self.project_path / "tooling" / "docs",
            self.project_path / ".github",
        ]

        for search_path in search_paths:
            if search_path.exists():
                for md_file in search_path.rglob("*.md"):
                    if debt_pattern.search(md_file.name):
                        documented.append(
                            {
                                "file": str(md_file.relative_to(self.project_path)),
                                "type": "documentation",
                            }
                        )

        return documented

    def scan_project(self) -> DebtReport:
        """Perform a full project scan."""
        items = self.scan_directory(self.project_path)
        documented = self.find_documented_debt()

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda x: (severity_order.get(x.severity, 4), x.file_path, x.line_number))

        return DebtReport(
            scan_date=datetime.now().isoformat(),
            project_path=str(self.project_path),
            items=items,
            documented_debt=documented,
        )

    def save_history(self, report: DebtReport):
        """Save scan results to history file."""
        history: list[dict[str, Any]] = []

        # Load existing history
        if self.history_file.exists():
            try:
                history = json.loads(self.history_file.read_text())
            except (json.JSONDecodeError, OSError):
                history = []

        # Add new entry
        history.append(
            {
                "date": report.scan_date,
                "total": report.total_count,
                "score": report.debt_score,
                "by_severity": report.by_severity,
            }
        )

        # Keep last 100 entries
        history = history[-100:]

        # Save
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.write_text(json.dumps(history, indent=2))

    def load_history(self) -> list[dict[str, Any]]:
        """Load scan history."""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text())
            except (json.JSONDecodeError, OSError):
                return []
        return []


def print_dashboard(report: DebtReport, history: list[dict[str, Any]]):
    """Print an interactive dashboard."""
    print()
    print(f"{Colors.CYAN}{'═' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}  TECHNICAL DEBT DASHBOARD{Colors.NC}")
    print(f"{Colors.CYAN}{'═' * 70}{Colors.NC}")
    print()

    # Summary box
    print(f"{Colors.BOLD} SUMMARY{Colors.NC}")
    print(f"  ┌{'─' * 40}┐")
    print(f"  │ {'Total Items:':<20} {report.total_count:>17} │")
    print(f"  │ {'Debt Score:':<20} {report.debt_score:>17} │")
    print(f"  │ {'Scan Date:':<20} {report.scan_date[:19]:>17} │")
    print(f"  └{'─' * 40}┘")
    print()

    # Severity breakdown
    print(f"{Colors.BOLD}BY SEVERITY{Colors.NC}")
    severity_colors = {
        "critical": Colors.RED,
        "high": Colors.YELLOW,
        "medium": Colors.BLUE,
        "low": Colors.GREEN,
    }
    max_count = max(report.by_severity.values()) if report.by_severity else 1
    for severity, count in report.by_severity.items():
        bar_length = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "█" * bar_length + "░" * (30 - bar_length)
        color = severity_colors.get(severity, Colors.NC)
        print(f"  {color}{severity.capitalize():>10}{Colors.NC} │{bar}│ {count}")
    print()

    # Category breakdown
    print(f"{Colors.BOLD} BY CATEGORY{Colors.NC}")
    for category, count in sorted(report.by_category.items(), key=lambda x: -x[1]):
        bar_length = (
            int((count / max(report.by_category.values())) * 30) if report.by_category else 0
        )
        bar = "█" * bar_length
        print(f"  {category:>15} │ {bar} {count}")
    print()

    # Type breakdown
    print(f"{Colors.BOLD}BY TYPE{Colors.NC}")
    for debt_type, count in sorted(report.by_type.items(), key=lambda x: -x[1]):
        print(f"  {debt_type:>12}: {count}")
    print()

    # Trend (if history available)
    if len(history) > 1:
        print(f"{Colors.BOLD}TREND (last 10 scans){Colors.NC}")
        recent = history[-10:]
        scores = [h.get("score", 0) for h in recent]
        max_score = max(scores) if scores else 1

        for _i, entry in enumerate(recent):
            score = entry.get("score", 0)
            bar_length = int((score / max_score) * 30) if max_score > 0 else 0
            bar = "▓" * bar_length
            date = entry.get("date", "")[:10]
            print(f"  {date} │ {bar} {score}")

        # Calculate change
        if len(scores) >= 2:
            change = scores[-1] - scores[-2]
            if change > 0:
                print(f"\n  {Colors.RED}[UP] Score increased by {change} (more debt){Colors.NC}")
            elif change < 0:
                print(
                    f"\n  {Colors.GREEN}[DOWN] Score decreased by {abs(change)} (less debt){Colors.NC}"
                )
            else:
                print(f"\n  {Colors.YELLOW}-> Score unchanged{Colors.NC}")
        print()

    # Top offenders
    print(f"{Colors.BOLD}TOP 5 FILES WITH MOST DEBT{Colors.NC}")
    file_counts: dict[str, int] = {}
    for item in report.items:
        file_counts[item.file_path] = file_counts.get(item.file_path, 0) + 1

    for file_path, count in sorted(file_counts.items(), key=lambda x: -x[1])[:5]:
        print(f"  {count:>3} items │ {file_path}")
    print()


def print_report(report: DebtReport):
    """Print a detailed report."""
    print()
    print(f"{Colors.CYAN}{'═' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}  TECHNICAL DEBT REPORT{Colors.NC}")
    print(f"{Colors.CYAN}{'═' * 70}{Colors.NC}")
    print()
    print(f"  Scan Date: {report.scan_date}")
    print(f"  Project:   {report.project_path}")
    print(f"  Total:     {report.total_count} items")
    print(f"  Score:     {report.debt_score}")
    print()

    # Group by file
    by_file: dict[str, list[DebtItem]] = {}
    for item in report.items:
        if item.file_path not in by_file:
            by_file[item.file_path] = []
        by_file[item.file_path].append(item)

    for file_path, items in sorted(by_file.items()):
        print(f"{Colors.BLUE}{file_path}{Colors.NC}")
        for item in items:
            severity_color = {
                "critical": Colors.RED,
                "high": Colors.YELLOW,
                "medium": Colors.BLUE,
                "low": Colors.GREEN,
            }.get(item.severity, Colors.NC)

            print(
                f"   {severity_color}[{item.debt_type}]{Colors.NC} Line {item.line_number}: {item.message[:60]}"
            )
        print()

    # Documented debt
    if report.documented_debt:
        print(f"{Colors.BOLD} DOCUMENTED DEBT{Colors.NC}")
        for doc in report.documented_debt:
            print(f"   {doc['file']}")
        print()


def generate_markdown_report(report: DebtReport) -> str:
    """Generate a markdown report."""
    lines = [
        "# Technical Debt Report",
        "",
        f"**Generated:** {report.scan_date}",
        f"**Project:** {report.project_path}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Items | {report.total_count} |",
        f"| Debt Score | {report.debt_score} |",
        f"| Critical | {report.by_severity['critical']} |",
        f"| High | {report.by_severity['high']} |",
        f"| Medium | {report.by_severity['medium']} |",
        f"| Low | {report.by_severity['low']} |",
        "",
        "## By Category",
        "",
        "| Category | Count |",
        "|----------|-------|",
    ]

    for category, count in sorted(report.by_category.items(), key=lambda x: -x[1]):
        lines.append(f"| {category} | {count} |")

    lines.extend(
        [
            "",
            "## All Items",
            "",
        ]
    )

    # Group by file
    by_file: dict[str, list[DebtItem]] = {}
    for item in report.items:
        if item.file_path not in by_file:
            by_file[item.file_path] = []
        by_file[item.file_path].append(item)

    for file_path, items in sorted(by_file.items()):
        lines.append(f"### `{file_path}`")
        lines.append("")
        lines.append("| Line | Type | Severity | Message |")
        lines.append("|------|------|----------|---------|")
        for item in items:
            msg = item.message[:50] + "..." if len(item.message) > 50 else item.message
            lines.append(f"| {item.line_number} | {item.debt_type} | {item.severity} | {msg} |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Track and report technical debt")
    parser.add_argument("--scan", action="store_true", help="Scan for debt indicators")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    parser.add_argument("--dashboard", action="store_true", help="Show dashboard view")
    parser.add_argument("--markdown", action="store_true", help="Output markdown report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--trend", action="store_true", help="Show trend over time")
    parser.add_argument("--save", action="store_true", help="Save to history")
    parser.add_argument("--path", type=str, help="Project path to scan")
    args = parser.parse_args()

    # Find project root
    if args.path:
        project_path = Path(args.path)
    else:
        script_dir = Path(__file__).parent
        project_path = script_dir.parent.parent  # Go up from scripts to project root

    if not project_path.exists():
        print(f"{Colors.RED}Error: Project path not found: {project_path}{Colors.NC}")
        sys.exit(1)

    tracker = TechDebtTracker(project_path)

    # Default to dashboard if no specific mode
    if not any([args.scan, args.report, args.dashboard, args.json, args.markdown, args.trend]):
        args.dashboard = True

    # Perform scan
    report = tracker.scan_project()

    # Save to history if requested or if dashboard/trend
    if args.save or args.dashboard or args.trend:
        tracker.save_history(report)

    # Load history for trend
    history = tracker.load_history()

    # Output
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    elif args.markdown:
        print(generate_markdown_report(report))
    elif args.trend:
        if not history:
            print(
                f"{Colors.YELLOW}No historical data available. Run with --save to start tracking.{Colors.NC}"
            )
        else:
            print_dashboard(report, history)
    elif args.report:
        print_report(report)
    else:  # dashboard
        print_dashboard(report, history)


if __name__ == "__main__":
    main()
