#!/usr/bin/env python3
"""
Cost Dashboard - CLI for viewing and managing cost data.

Provides commands for viewing session history, generating summaries,
subscription usage tracking, model efficiency metrics, usage projections,
and exporting comprehensive analytics reports.

Usage:
    python cost_dashboard.py                        # Show current/latest session
    python cost_dashboard.py --history 10           # Show last 10 sessions
    python cost_dashboard.py --summary              # Show aggregate summary
    python cost_dashboard.py --subscription         # Show subscription usage %
    python cost_dashboard.py --efficiency           # Show model efficiency
    python cost_dashboard.py --set-plan pro         # Set subscription plan
    python cost_dashboard.py --story 3-5            # Show costs for story
    python cost_dashboard.py --export costs.csv     # Export to file
    python cost_dashboard.py --schedule-export r.md # Export analytics report
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Lowercase generic types for Python 3.9+ compatibility
# Using 'list' instead of 'List' from typing

# Add lib directory for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from cost_config import SUBSCRIPTION_PLANS, get_config
from cost_display import Colors
from cost_tracker import SESSIONS_DIR, CostTracker, SessionCost
from currency_converter import get_converter


class CostDashboard:
    """
    CLI Dashboard for cost analysis.

    Provides commands for viewing, summarizing, and exporting cost data.
    """

    # Box drawing
    BOX_TOP_LEFT = "╔"
    BOX_TOP_RIGHT = "╗"
    BOX_BOTTOM_LEFT = "╚"
    BOX_BOTTOM_RIGHT = "╝"
    BOX_HORIZONTAL = "═"
    BOX_VERTICAL = "║"
    BOX_T_LEFT = "╠"
    BOX_T_RIGHT = "╣"
    BOX_LINE = "─"

    def __init__(self, width: int = 70):
        self.width = width
        self.converter = get_converter()

    def _box_line(self, left: str, right: str, fill: str = "═") -> str:
        """Create a box line."""
        return f"{left}{fill * (self.width - 2)}{right}"

    def _content_line(self, content: str, align: str = "left") -> str:
        """Create a content line within the box."""
        clean_content = Colors.strip(content)
        padding = self.width - 4 - len(clean_content)

        if align == "center":
            left_pad = padding // 2
            right_pad = padding - left_pad
            return f"{self.BOX_VERTICAL} {' ' * left_pad}{content}{' ' * right_pad} {self.BOX_VERTICAL}"
        elif align == "right":
            return f"{self.BOX_VERTICAL} {' ' * padding}{content} {self.BOX_VERTICAL}"
        else:
            return f"{self.BOX_VERTICAL} {content}{' ' * padding} {self.BOX_VERTICAL}"

    def _empty_line(self) -> str:
        """Create an empty content line."""
        return self._content_line("")

    def _section_header(self, title: str) -> str:
        """Create a section header."""
        line = f"{self.BOX_LINE * 3} {title} "
        remaining = self.width - 6 - len(title)
        return self._content_line(f"{Colors.BOLD}{line}{self.BOX_LINE * remaining}{Colors.RESET}")

    def _format_tokens(self, tokens: int) -> str:
        """Format token count with K/M suffix."""
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.1f}M"
        elif tokens >= 1_000:
            return f"{tokens / 1_000:.1f}K"
        return str(tokens)

    def show_session(self, session: SessionCost):
        """Display a single session."""
        lines = []

        # Header
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_TOP_LEFT, self.BOX_TOP_RIGHT)}{Colors.RESET}"
        )
        title = f"SESSION: {session.session_id[:20]}"
        lines.append(
            f"{Colors.CYAN}{self._content_line(Colors.BOLD + title + Colors.RESET, 'center')}{Colors.RESET}"
        )
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_T_LEFT, self.BOX_T_RIGHT)}{Colors.RESET}"
        )

        # Session info
        lines.append(self._empty_line())
        lines.append(
            self._content_line(f"Story: {Colors.BOLD_CYAN}{session.story_key}{Colors.RESET}")
        )
        lines.append(self._content_line(f"Start: {session.start_time[:19]}"))
        if session.end_time:
            lines.append(self._content_line(f"End:   {session.end_time[:19]}"))

        # Tokens
        lines.append(self._empty_line())
        lines.append(self._section_header("TOKENS"))
        lines.append(
            self._content_line(
                f"Input:  {Colors.BOLD}{self._format_tokens(session.total_input_tokens):>10}{Colors.RESET}    "
                f"Output: {Colors.BOLD}{self._format_tokens(session.total_output_tokens):>10}{Colors.RESET}"
            )
        )
        lines.append(
            self._content_line(
                f"Total:  {Colors.BOLD_WHITE}{self._format_tokens(session.total_tokens):>10}{Colors.RESET}"
            )
        )

        # Cost by agent
        lines.append(self._empty_line())
        lines.append(self._section_header("COST BY AGENT"))

        by_agent = session.get_cost_by_agent()
        if by_agent:
            for agent, cost in sorted(by_agent.items(), key=lambda x: -x[1]):
                pct = (cost / session.total_cost_usd * 100) if session.total_cost_usd > 0 else 0
                lines.append(
                    self._content_line(
                        f"{agent:<12} {Colors.BOLD}${cost:>8.2f}{Colors.RESET}  ({pct:>5.1f}%)"
                    )
                )
        else:
            lines.append(self._content_line(f"{Colors.DIM}No entries{Colors.RESET}"))

        # Cost by model
        lines.append(self._empty_line())
        lines.append(self._section_header("COST BY MODEL"))

        by_model = session.get_cost_by_model()
        if by_model:
            for model, cost in sorted(by_model.items(), key=lambda x: -x[1]):
                pct = (cost / session.total_cost_usd * 100) if session.total_cost_usd > 0 else 0
                lines.append(
                    self._content_line(
                        f"{model:<12} {Colors.BOLD}${cost:>8.2f}{Colors.RESET}  ({pct:>5.1f}%)"
                    )
                )

        # Total
        lines.append(self._empty_line())
        lines.append(self._section_header("TOTAL"))
        lines.append(
            self._content_line(
                f"Cost: {Colors.BOLD_GREEN}${session.total_cost_usd:.2f}{Colors.RESET}    "
                f"Budget: ${session.budget_limit_usd:.2f}    "
                f"Used: {session.budget_used_percent:.0f}%"
            )
        )

        # Multi-currency
        lines.append(self._empty_line())
        lines.append(self._content_line(self.converter.format_all(session.total_cost_usd, " │ ")))

        # Footer
        lines.append(self._empty_line())
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_BOTTOM_LEFT, self.BOX_BOTTOM_RIGHT)}{Colors.RESET}"
        )

        print("\n".join(lines))

    def show_history(self, sessions: list[SessionCost], limit: int = 10):
        """Display session history."""
        sessions = sessions[:limit]

        lines = []

        # Header
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_TOP_LEFT, self.BOX_TOP_RIGHT)}{Colors.RESET}"
        )
        title = f"SESSION HISTORY - Last {len(sessions)} Sessions"
        lines.append(
            f"{Colors.CYAN}{self._content_line(Colors.BOLD + title + Colors.RESET, 'center')}{Colors.RESET}"
        )
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_T_LEFT, self.BOX_T_RIGHT)}{Colors.RESET}"
        )

        # Table header
        lines.append(self._empty_line())
        lines.append(
            self._content_line(
                f"{Colors.DIM}{'Date':<12} {'Story':<10} {'Tokens':>10} {'Cost':>10} {'Budget%':>8}{Colors.RESET}"
            )
        )
        lines.append(self._content_line(f"{Colors.DIM}{self.BOX_LINE * 54}{Colors.RESET}"))

        # Sessions
        total_cost = 0
        total_tokens = 0

        for session in sessions:
            date_str = session.start_time[:10]
            tokens = self._format_tokens(session.total_tokens)
            cost = f"${session.total_cost_usd:.2f}"
            budget_pct = f"{session.budget_used_percent:.0f}%"

            # Color based on budget usage
            if session.budget_used_percent >= 90:
                color = Colors.RED
            elif session.budget_used_percent >= 75:
                color = Colors.YELLOW
            else:
                color = Colors.GREEN

            lines.append(
                self._content_line(
                    f"{date_str:<12} {session.story_key:<10} {tokens:>10} "
                    f"{color}{cost:>10}{Colors.RESET} {budget_pct:>8}"
                )
            )

            total_cost += session.total_cost_usd
            total_tokens += session.total_tokens

        # Totals
        lines.append(self._content_line(f"{Colors.DIM}{self.BOX_LINE * 54}{Colors.RESET}"))
        lines.append(
            self._content_line(
                f"{Colors.BOLD}{'TOTAL':<12} {'':<10} {self._format_tokens(total_tokens):>10} "
                f"${total_cost:>9.2f}{Colors.RESET}"
            )
        )

        # Footer
        lines.append(self._empty_line())
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_BOTTOM_LEFT, self.BOX_BOTTOM_RIGHT)}{Colors.RESET}"
        )

        print("\n".join(lines))

    def _format_subscription_bar(self, percentage: float, width: int = 30) -> str:
        """Create a progress bar for subscription usage."""
        filled = int((percentage / 100) * width)
        filled = min(filled, width)  # Cap at width even if over 100%

        # Color based on percentage
        if percentage >= 100:
            color = Colors.RED
        elif percentage >= 90:
            color = Colors.RED
        elif percentage >= 75:
            color = Colors.YELLOW
        else:
            color = Colors.GREEN

        bar = "█" * filled + "░" * (width - filled)
        return f"{color}{bar}{Colors.RESET}"

    def show_subscription(self):
        """Display subscription usage status with projection."""
        config = get_config()

        if config.subscription_token_limit <= 0:
            print(f"{Colors.YELLOW}Subscription tracking not configured.{Colors.RESET}")
            print()
            print("To enable, use one of the following methods:")
            print()
            print("1. Set a plan preset (recommended):")
            print("   export SUBSCRIPTION_PLAN=pro")
            print()
            print("   Available plans:")
            for name, info in SUBSCRIPTION_PLANS.items():
                print(
                    f"     {name:<12} {self._format_tokens(info['token_limit']):>8} tokens/month  ({info['description']})"
                )
            print()
            print("2. Set a custom token limit:")
            print("   export SUBSCRIPTION_TOKEN_LIMIT=5000000")
            print()
            print("3. Use config file: tooling/.automation/costs/config.json")
            print('   {"subscription_plan": "pro"}')
            return

        sub = CostTracker.get_subscription_percentage(
            config.subscription_token_limit,
            config.subscription_billing_period_days,
        )
        projection = CostTracker.get_usage_projection(
            config.subscription_token_limit,
            config.subscription_billing_period_days,
        )

        lines = []

        # Header
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_TOP_LEFT, self.BOX_TOP_RIGHT)}{Colors.RESET}"
        )
        title = "SUBSCRIPTION USAGE"
        lines.append(
            f"{Colors.CYAN}{self._content_line(Colors.BOLD + title + Colors.RESET, 'center')}{Colors.RESET}"
        )
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_T_LEFT, self.BOX_T_RIGHT)}{Colors.RESET}"
        )

        # Plan info
        plan_info = config.get_subscription_plan_info()
        lines.append(self._empty_line())
        lines.append(
            self._content_line(f"Plan: {Colors.BOLD_CYAN}{plan_info['description']}{Colors.RESET}")
        )

        # Status indicator
        status_colors = {
            "ok": Colors.GREEN,
            "warning": Colors.YELLOW,
            "critical": Colors.RED,
            "exceeded": Colors.RED,
        }
        status_color = status_colors.get(sub["status"], Colors.WHITE)
        status_text = sub["status"].upper()

        lines.append(
            self._content_line(
                f"Status: {status_color}{Colors.BOLD}{status_text}{Colors.RESET}    "
                f"Billing Period: {Colors.BOLD}{sub['billing_period_days']} days{Colors.RESET}"
            )
        )

        # Progress bar
        lines.append(self._empty_line())
        lines.append(self._section_header("USAGE"))
        bar = self._format_subscription_bar(sub["percentage"])
        lines.append(
            self._content_line(f"{bar} {status_color}{sub['percentage']:.1f}%{Colors.RESET}")
        )

        # Token details
        lines.append(self._empty_line())
        lines.append(
            self._content_line(
                f"Used:      {Colors.BOLD}{self._format_tokens(sub['used_tokens']):>10}{Colors.RESET} tokens"
            )
        )
        lines.append(
            self._content_line(
                f"Limit:     {Colors.BOLD}{self._format_tokens(sub['limit_tokens']):>10}{Colors.RESET} tokens"
            )
        )

        remaining_color = Colors.GREEN if sub["remaining_tokens"] > 0 else Colors.RED
        remaining_sign = "" if sub["remaining_tokens"] >= 0 else "-"
        lines.append(
            self._content_line(
                f"Remaining: {remaining_color}{remaining_sign}{self._format_tokens(abs(sub['remaining_tokens'])):>10}{Colors.RESET} tokens"
            )
        )

        # Projection / Forecast
        lines.append(self._empty_line())
        lines.append(self._section_header("PROJECTION"))

        proj_color = Colors.GREEN if projection["on_track"] else Colors.YELLOW
        if projection["days_until_limit"] is not None and projection["days_until_limit"] <= 0:
            proj_color = Colors.RED

        lines.append(
            self._content_line(
                f"Daily Avg:     {Colors.BOLD}{self._format_tokens(projection['daily_average']):>10}{Colors.RESET} tokens/day"
            )
        )
        lines.append(
            self._content_line(
                f"Projected:     {Colors.BOLD}{self._format_tokens(projection['projected_end_usage']):>10}{Colors.RESET} tokens by period end"
            )
        )

        if projection["days_until_limit"] is not None:
            days_str = (
                f"{projection['days_until_limit']:.0f}"
                if projection["days_until_limit"] > 0
                else "0"
            )
            lines.append(
                self._content_line(
                    f"Days to Limit: {proj_color}{Colors.BOLD}{days_str:>10}{Colors.RESET} days"
                )
            )

        lines.append(self._empty_line())
        lines.append(self._content_line(f"{proj_color}{projection['message']}{Colors.RESET}"))

        # Cost in period
        lines.append(self._empty_line())
        lines.append(self._section_header("PERIOD COST"))
        lines.append(
            self._content_line(
                f"Total Cost: {Colors.BOLD_GREEN}${sub['total_cost_usd']:.2f}{Colors.RESET}    "
                f"Sessions: {Colors.BOLD}{sub['total_sessions']}{Colors.RESET}"
            )
        )

        # Multi-currency
        lines.append(self._empty_line())
        lines.append(self._content_line(self.converter.format_all(sub["total_cost_usd"], " | ")))

        # Footer
        lines.append(self._empty_line())
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_BOTTOM_LEFT, self.BOX_BOTTOM_RIGHT)}{Colors.RESET}"
        )

        print("\n".join(lines))

    def show_efficiency(self):
        """Display model efficiency metrics."""
        efficiency = CostTracker.get_model_efficiency()

        if not efficiency:
            print(f"{Colors.YELLOW}No usage data available for efficiency analysis.{Colors.RESET}")
            return

        lines = []

        # Header
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_TOP_LEFT, self.BOX_TOP_RIGHT)}{Colors.RESET}"
        )
        title = "MODEL EFFICIENCY"
        lines.append(
            f"{Colors.CYAN}{self._content_line(Colors.BOLD + title + Colors.RESET, 'center')}{Colors.RESET}"
        )
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_T_LEFT, self.BOX_T_RIGHT)}{Colors.RESET}"
        )

        # Table header
        lines.append(self._empty_line())
        lines.append(
            self._content_line(
                f"{Colors.DIM}{'Model':<12} {'$/1K Out':>10} {'Out/In':>8} {'Calls':>8} {'Cost':>10}{Colors.RESET}"
            )
        )
        lines.append(self._content_line(f"{Colors.DIM}{self.BOX_LINE * 52}{Colors.RESET}"))

        # Models (sorted by efficiency - lowest cost per output first)
        best_model = list(efficiency.keys())[0] if efficiency else None
        for model, stats in efficiency.items():
            # Highlight the most efficient model
            if model == best_model:
                model_display = f"{Colors.GREEN}{model:<12}{Colors.RESET}"
                efficiency_badge = f" {Colors.GREEN}[BEST]{Colors.RESET}"
            else:
                model_display = f"{model:<12}"
                efficiency_badge = ""

            lines.append(
                self._content_line(
                    f"{model_display} ${stats['cost_per_1k_output']:>9.4f} "
                    f"{stats['output_input_ratio']:>7.2f}x "
                    f"{stats['total_calls']:>8} "
                    f"${stats['total_cost']:>9.2f}{efficiency_badge}"
                )
            )

        # Summary
        lines.append(self._empty_line())
        lines.append(self._section_header("METRICS EXPLAINED"))
        lines.append(
            self._content_line(
                f"{Colors.DIM}$/1K Out  = Cost per 1,000 output tokens (lower is better){Colors.RESET}"
            )
        )
        lines.append(
            self._content_line(
                f"{Colors.DIM}Out/In    = Output tokens per input token (efficiency ratio){Colors.RESET}"
            )
        )

        # Footer
        lines.append(self._empty_line())
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_BOTTOM_LEFT, self.BOX_BOTTOM_RIGHT)}{Colors.RESET}"
        )

        print("\n".join(lines))

    def show_summary(self, days: int = 30):
        """Display aggregate summary."""
        stats = CostTracker.get_aggregate_stats(days)
        config = get_config()

        lines = []

        # Header
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_TOP_LEFT, self.BOX_TOP_RIGHT)}{Colors.RESET}"
        )
        title = f"COST SUMMARY - Last {days} Days"
        lines.append(
            f"{Colors.CYAN}{self._content_line(Colors.BOLD + title + Colors.RESET, 'center')}{Colors.RESET}"
        )
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_T_LEFT, self.BOX_T_RIGHT)}{Colors.RESET}"
        )

        # Subscription status (if configured)
        if config.subscription_token_limit > 0:
            sub = CostTracker.get_subscription_percentage(
                config.subscription_token_limit,
                config.subscription_billing_period_days,
            )
            status_colors = {
                "ok": Colors.GREEN,
                "warning": Colors.YELLOW,
                "critical": Colors.RED,
                "exceeded": Colors.RED,
            }
            status_color = status_colors.get(sub["status"], Colors.WHITE)

            lines.append(self._empty_line())
            lines.append(self._section_header("SUBSCRIPTION"))
            bar = self._format_subscription_bar(sub["percentage"], width=25)
            lines.append(
                self._content_line(
                    f"{bar} {status_color}{sub['percentage']:.1f}%{Colors.RESET} of "
                    f"{self._format_tokens(sub['limit_tokens'])} token limit"
                )
            )
            lines.append(
                self._content_line(
                    f"Used: {self._format_tokens(sub['used_tokens'])} | "
                    f"Remaining: {self._format_tokens(max(0, sub['remaining_tokens']))}"
                )
            )

        # Overview
        lines.append(self._empty_line())
        lines.append(self._section_header("OVERVIEW"))
        lines.append(
            self._content_line(
                f"Total Sessions: {Colors.BOLD}{stats['total_sessions']}{Colors.RESET}"
            )
        )
        lines.append(
            self._content_line(
                f"Total Tokens:   {Colors.BOLD}{self._format_tokens(stats['total_tokens'])}{Colors.RESET}"
            )
        )
        lines.append(
            self._content_line(
                f"Total Cost:     {Colors.BOLD_GREEN}${stats['total_cost_usd']:.2f}{Colors.RESET}"
            )
        )
        lines.append(
            self._content_line(
                f"Avg/Session:    {Colors.BOLD}${stats.get('average_per_session', 0):.2f}{Colors.RESET}"
            )
        )

        # Multi-currency total
        lines.append(self._empty_line())
        lines.append(self._content_line(self.converter.format_all(stats["total_cost_usd"], " │ ")))

        # By Agent
        if stats.get("by_agent"):
            lines.append(self._empty_line())
            lines.append(self._section_header("BY AGENT"))
            lines.append(
                self._content_line(
                    f"{Colors.DIM}{'Agent':<12} {'Sessions':>10} {'Cost':>12}{Colors.RESET}"
                )
            )
            lines.append(self._content_line(f"{Colors.DIM}{self.BOX_LINE * 38}{Colors.RESET}"))

            for agent, data in sorted(stats["by_agent"].items(), key=lambda x: -x[1]["cost"]):
                lines.append(
                    self._content_line(
                        f"{agent:<12} {data['sessions']:>10} {Colors.BOLD}${data['cost']:>10.2f}{Colors.RESET}"
                    )
                )

        # By Model
        if stats.get("by_model"):
            lines.append(self._empty_line())
            lines.append(self._section_header("BY MODEL"))
            lines.append(
                self._content_line(f"{Colors.DIM}{'Model':<20} {'Cost':>12}{Colors.RESET}")
            )
            lines.append(self._content_line(f"{Colors.DIM}{self.BOX_LINE * 36}{Colors.RESET}"))

            for model, data in sorted(stats["by_model"].items(), key=lambda x: -x[1]["cost"]):
                lines.append(
                    self._content_line(
                        f"{model:<20} {Colors.BOLD}${data['cost']:>10.2f}{Colors.RESET}"
                    )
                )

        # Footer
        lines.append(self._empty_line())
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_BOTTOM_LEFT, self.BOX_BOTTOM_RIGHT)}{Colors.RESET}"
        )

        print("\n".join(lines))

    def show_story(self, story_key: str):
        """Display costs for a specific story."""
        sessions = CostTracker.get_historical_sessions(days=365)
        story_sessions = [s for s in sessions if s.story_key == story_key]

        if not story_sessions:
            print(f"{Colors.YELLOW}No sessions found for story: {story_key}{Colors.RESET}")
            return

        lines = []

        # Header
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_TOP_LEFT, self.BOX_TOP_RIGHT)}{Colors.RESET}"
        )
        title = f"STORY COSTS: {story_key}"
        lines.append(
            f"{Colors.CYAN}{self._content_line(Colors.BOLD + title + Colors.RESET, 'center')}{Colors.RESET}"
        )
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_T_LEFT, self.BOX_T_RIGHT)}{Colors.RESET}"
        )

        # Summary
        total_cost = sum(s.total_cost_usd for s in story_sessions)
        total_tokens = sum(s.total_tokens for s in story_sessions)

        lines.append(self._empty_line())
        lines.append(
            self._content_line(f"Sessions:     {Colors.BOLD}{len(story_sessions)}{Colors.RESET}")
        )
        lines.append(
            self._content_line(
                f"Total Tokens: {Colors.BOLD}{self._format_tokens(total_tokens)}{Colors.RESET}"
            )
        )
        lines.append(
            self._content_line(f"Total Cost:   {Colors.BOLD_GREEN}${total_cost:.2f}{Colors.RESET}")
        )

        # Multi-currency
        lines.append(self._empty_line())
        lines.append(self._content_line(self.converter.format_all(total_cost, " │ ")))

        # Sessions
        lines.append(self._empty_line())
        lines.append(self._section_header("SESSIONS"))
        lines.append(
            self._content_line(
                f"{Colors.DIM}{'Date':<12} {'Duration':<10} {'Tokens':>10} {'Cost':>10}{Colors.RESET}"
            )
        )
        lines.append(self._content_line(f"{Colors.DIM}{self.BOX_LINE * 46}{Colors.RESET}"))

        for session in story_sessions:
            date_str = session.start_time[:10]

            # Calculate duration
            if session.end_time:
                try:
                    start = datetime.fromisoformat(session.start_time)
                    end = datetime.fromisoformat(session.end_time)
                    duration = end - start
                    duration_str = f"{int(duration.total_seconds() // 60)}m"
                except (ValueError, TypeError):
                    duration_str = "N/A"
            else:
                duration_str = "Running"

            lines.append(
                self._content_line(
                    f"{date_str:<12} {duration_str:<10} "
                    f"{self._format_tokens(session.total_tokens):>10} "
                    f"${session.total_cost_usd:>9.2f}"
                )
            )

        # Footer
        lines.append(self._empty_line())
        lines.append(
            f"{Colors.CYAN}{self._box_line(self.BOX_BOTTOM_LEFT, self.BOX_BOTTOM_RIGHT)}{Colors.RESET}"
        )

        print("\n".join(lines))

    def export_data(self, filepath: str, sessions: Optional[list[SessionCost]] = None):
        """Export cost data to file."""
        if sessions is None:
            sessions = CostTracker.get_historical_sessions(days=365)

        path = Path(filepath)
        ext = path.suffix.lower()

        if ext == ".csv":
            self._export_csv(path, sessions)
        elif ext == ".json":
            self._export_json(path, sessions)
        elif ext == ".md":
            self._export_markdown(path, sessions)
        else:
            print(f"{Colors.RED}Unsupported format: {ext}{Colors.RESET}")
            print("Supported formats: .csv, .json, .md")
            return

        print(f"{Colors.GREEN}Exported to: {filepath}{Colors.RESET}")
        print(f"  Sessions: {len(sessions)}")
        print(f"  Total Cost: ${sum(s.total_cost_usd for s in sessions):.2f}")

    def _export_csv(self, path: Path, sessions: list[SessionCost]):
        """Export to CSV."""
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "session_id",
                    "story_key",
                    "start_time",
                    "end_time",
                    "input_tokens",
                    "output_tokens",
                    "total_tokens",
                    "cost_usd",
                    "budget_limit",
                    "budget_used_pct",
                ]
            )

            # Data
            for session in sessions:
                writer.writerow(
                    [
                        session.session_id,
                        session.story_key,
                        session.start_time,
                        session.end_time or "",
                        session.total_input_tokens,
                        session.total_output_tokens,
                        session.total_tokens,
                        round(session.total_cost_usd, 4),
                        session.budget_limit_usd,
                        round(session.budget_used_percent, 2),
                    ]
                )

    def _export_json(self, path: Path, sessions: list[SessionCost]):
        """Export to JSON."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_sessions": len(sessions),
            "total_cost_usd": sum(s.total_cost_usd for s in sessions),
            "sessions": [s.to_dict() for s in sessions],
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def export_analytics_report(self, filepath: str, days: int = 30):
        """
        Export comprehensive analytics report with trends, rankings, and comparisons.

        Includes:
        - Daily/Weekly usage trends
        - Per-story cost rankings
        - Period comparison (current vs previous)
        - API rate statistics
        - Model efficiency metrics
        """
        path = Path(filepath)
        ext = path.suffix.lower()

        # Gather all analytics data
        config = get_config()
        daily_usage = CostTracker.get_daily_usage(days)
        story_rankings = CostTracker.get_story_rankings(days, limit=15)
        comparison = CostTracker.get_period_comparison(days)
        api_rates = CostTracker.get_api_rate_stats(days)
        efficiency = CostTracker.get_model_efficiency()
        stats = CostTracker.get_aggregate_stats(days)

        # Subscription data if configured
        subscription = None
        projection = None
        if config.subscription_token_limit > 0:
            subscription = CostTracker.get_subscription_percentage(
                config.subscription_token_limit,
                config.subscription_billing_period_days,
            )
            projection = CostTracker.get_usage_projection(
                config.subscription_token_limit,
                config.subscription_billing_period_days,
            )

        if ext == ".json":
            self._export_analytics_json(
                path,
                {
                    "generated_at": datetime.now().isoformat(),
                    "period_days": days,
                    "summary": stats,
                    "subscription": subscription,
                    "projection": projection,
                    "daily_usage": daily_usage,
                    "story_rankings": story_rankings,
                    "period_comparison": comparison,
                    "api_rates": api_rates,
                    "model_efficiency": efficiency,
                },
            )
        elif ext == ".md":
            self._export_analytics_markdown(
                path,
                days,
                stats,
                subscription,
                projection,
                daily_usage,
                story_rankings,
                comparison,
                api_rates,
                efficiency,
            )
        else:
            print(f"{Colors.RED}Unsupported format: {ext}{Colors.RESET}")
            print("Supported formats for analytics: .json, .md")
            return

        print(f"{Colors.GREEN}Analytics report exported to: {filepath}{Colors.RESET}")
        print(f"  Period: {days} days")
        print(f"  Total Sessions: {stats['total_sessions']}")
        print(f"  Total Cost: ${stats['total_cost_usd']:.2f}")

    def _export_analytics_json(self, path: Path, data: dict):
        """Export analytics to JSON."""
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _export_analytics_markdown(
        self,
        path: Path,
        days: int,
        stats: dict,
        subscription: dict,
        projection: dict,
        daily_usage: list,
        story_rankings: list,
        comparison: dict,
        api_rates: dict,
        efficiency: dict,
    ):
        """Export comprehensive analytics to Markdown."""
        lines = [
            "# Cost Analytics Report",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Period: Last {days} days",
            "",
        ]

        # Summary
        lines.extend(
            [
                "## Summary",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Total Sessions | {stats['total_sessions']} |",
                f"| Total Tokens | {stats['total_tokens']:,} |",
                f"| Total Cost | ${stats['total_cost_usd']:.2f} |",
                f"| Avg per Session | ${stats.get('average_per_session', 0):.2f} |",
                "",
            ]
        )

        # Subscription Status
        if subscription:
            lines.extend(
                [
                    "## Subscription Status",
                    "",
                    "| Metric | Value |",
                    "|--------|-------|",
                    f"| Usage | {subscription['percentage']:.1f}% |",
                    f"| Used Tokens | {subscription['used_tokens']:,} |",
                    f"| Limit | {subscription['limit_tokens']:,} |",
                    f"| Remaining | {subscription['remaining_tokens']:,} |",
                    f"| Status | {subscription['status'].upper()} |",
                    "",
                ]
            )

            if projection:
                lines.extend(
                    [
                        "### Projection",
                        "",
                        f"- **Daily Average**: {projection['daily_average']:,} tokens/day",
                        f"- **Projected End Usage**: {projection['projected_end_usage']:,} tokens",
                        f"- **Days Until Limit**: {projection['days_until_limit'] or 'N/A'}",
                        f"- **Forecast**: {projection['message']}",
                        "",
                    ]
                )

        # Period Comparison
        lines.extend(
            [
                "## Period Comparison",
                "",
                f"Comparing current {days} days vs previous {days} days:",
                "",
                "| Metric | Current | Previous | Change |",
                "|--------|---------|----------|--------|",
            ]
        )

        curr = comparison["current_period"]
        prev = comparison["previous_period"]
        delta = comparison["delta"]

        token_arrow = "+" if delta["tokens"] >= 0 else ""
        cost_arrow = "+" if delta["cost_usd"] >= 0 else ""

        lines.extend(
            [
                f"| Tokens | {curr['tokens']:,} | {prev['tokens']:,} | {token_arrow}{delta['tokens_pct']:.1f}% |",
                f"| Cost | ${curr['cost_usd']:.2f} | ${prev['cost_usd']:.2f} | {cost_arrow}{delta['cost_pct']:.1f}% |",
                f"| Sessions | {curr['sessions']} | {prev['sessions']} | - |",
                "",
            ]
        )

        # Daily Trends
        if daily_usage:
            lines.extend(
                [
                    "## Daily Usage Trends",
                    "",
                    "| Date | Tokens | Cost | Sessions |",
                    "|------|--------|------|----------|",
                ]
            )
            for day in daily_usage[-14:]:  # Last 14 days
                lines.append(
                    f"| {day['date']} | {day['tokens']:,} | ${day['cost_usd']:.2f} | {day['sessions']} |"
                )
            lines.append("")

        # Story Rankings
        if story_rankings:
            lines.extend(
                [
                    "## Top Stories by Token Usage",
                    "",
                    "| Rank | Story | Tokens | Cost | Sessions |",
                    "|------|-------|--------|------|----------|",
                ]
            )
            for i, story in enumerate(story_rankings[:10], 1):
                lines.append(
                    f"| {i} | {story['story_key']} | {story['total_tokens']:,} | "
                    f"${story['total_cost_usd']:.2f} | {story['sessions']} |"
                )
            lines.append("")

        # API Rate Statistics
        lines.extend(
            [
                "## API Rate Statistics",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Total Calls | {api_rates['total_calls']} |",
                f"| Calls/Day (avg) | {api_rates['calls_per_day']} |",
                f"| Calls/Hour (avg) | {api_rates['calls_per_hour']} |",
                f"| Peak Hour | {api_rates['peak_hour']}:00 ({api_rates['peak_hour_calls']} calls) |"
                if api_rates["peak_hour"] is not None
                else "| Peak Hour | N/A |",
                f"| Peak Day | {api_rates['peak_day']} ({api_rates['peak_day_calls']} calls) |"
                if api_rates["peak_day"]
                else "| Peak Day | N/A |",
                "",
            ]
        )

        # Model Efficiency
        if efficiency:
            lines.extend(
                [
                    "## Model Efficiency",
                    "",
                    "| Model | $/1K Output | Out/In Ratio | Calls | Total Cost |",
                    "|-------|-------------|--------------|-------|------------|",
                ]
            )
            for model, stats in efficiency.items():
                lines.append(
                    f"| {model} | ${stats['cost_per_1k_output']:.4f} | "
                    f"{stats['output_input_ratio']:.2f}x | {stats['total_calls']} | "
                    f"${stats['total_cost']:.2f} |"
                )
            lines.append("")

        # Footer
        lines.extend(
            [
                "---",
                "",
                "Report generated by Devflow Cost Dashboard",
            ]
        )

        with open(path, "w") as f:
            f.write("\n".join(lines))

    def _export_markdown(self, path: Path, sessions: list[SessionCost]):
        """Export to Markdown."""
        total_cost = sum(s.total_cost_usd for s in sessions)
        total_tokens = sum(s.total_tokens for s in sessions)

        lines = [
            "# Cost Report",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            "",
            f"- **Total Sessions**: {len(sessions)}",
            f"- **Total Tokens**: {total_tokens:,}",
            f"- **Total Cost**: ${total_cost:.2f}",
            f"- **Average per Session**: ${total_cost / len(sessions):.2f}" if sessions else "",
            "",
            "### Multi-Currency",
            "",
            f"- USD: ${total_cost:.2f}",
            f"- EUR: {self.converter.format(total_cost, 'EUR')}",
            f"- GBP: {self.converter.format(total_cost, 'GBP')}",
            f"- BRL: {self.converter.format(total_cost, 'BRL')}",
            "",
            "## Sessions",
            "",
            "| Date | Story | Tokens | Cost | Budget % |",
            "|------|-------|--------|------|----------|",
        ]

        for session in sessions:
            lines.append(
                f"| {session.start_time[:10]} | {session.story_key} | "
                f"{session.total_tokens:,} | ${session.total_cost_usd:.2f} | "
                f"{session.budget_used_percent:.0f}% |"
            )

        with open(path, "w") as f:
            f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(
        description="Cost Dashboard - View and manage cost data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cost_dashboard.py                        # Show latest session
  python cost_dashboard.py --history 10           # Show last 10 sessions
  python cost_dashboard.py --summary              # Show 30-day summary
  python cost_dashboard.py --subscription         # Show subscription usage %
  python cost_dashboard.py --efficiency           # Show model efficiency
  python cost_dashboard.py --set-plan pro         # Set subscription to pro plan
  python cost_dashboard.py --story 3-5            # Show costs for story
  python cost_dashboard.py --export costs.csv     # Export to CSV
  python cost_dashboard.py --schedule-export r.md # Export analytics report
        """,
    )

    parser.add_argument("--history", "-H", type=int, metavar="N", help="Show last N sessions")
    parser.add_argument("--summary", "-s", action="store_true", help="Show aggregate summary")
    parser.add_argument(
        "--subscription", "-S", action="store_true", help="Show subscription usage percentage"
    )
    parser.add_argument(
        "--efficiency", "-E", action="store_true", help="Show model efficiency metrics"
    )
    parser.add_argument(
        "--set-plan",
        type=str,
        metavar="PLAN",
        help="Set subscription plan (free, developer, pro, scale, enterprise)",
    )
    parser.add_argument(
        "--days", "-d", type=int, default=30, help="Number of days for summary (default: 30)"
    )
    parser.add_argument("--story", type=str, metavar="KEY", help="Show costs for specific story")
    parser.add_argument(
        "--export", "-e", type=str, metavar="FILE", help="Export to file (.csv, .json, .md)"
    )
    parser.add_argument(
        "--schedule-export",
        type=str,
        metavar="FILE",
        help="Export comprehensive report with analytics to file",
    )
    parser.add_argument("--from-date", type=str, metavar="YYYY-MM-DD", help="Filter from date")
    parser.add_argument("--to-date", type=str, metavar="YYYY-MM-DD", help="Filter to date")

    args = parser.parse_args()
    dashboard = CostDashboard()

    # Get sessions
    sessions = CostTracker.get_historical_sessions(days=args.days)

    # Apply date filters
    if args.from_date:
        try:
            from_dt = datetime.fromisoformat(args.from_date)
            sessions = [s for s in sessions if datetime.fromisoformat(s.start_time) >= from_dt]
        except ValueError:
            print(f"{Colors.RED}Invalid from-date format. Use YYYY-MM-DD{Colors.RESET}")
            return 1

    if args.to_date:
        try:
            to_dt = datetime.fromisoformat(args.to_date)
            sessions = [s for s in sessions if datetime.fromisoformat(s.start_time) <= to_dt]
        except ValueError:
            print(f"{Colors.RED}Invalid to-date format. Use YYYY-MM-DD{Colors.RESET}")
            return 1

    # Execute command
    if args.set_plan:
        # Set subscription plan
        config = get_config()
        if config.set_subscription_plan(args.set_plan):
            config_file = (
                Path(__file__).parent
                / "lib"
                / ".."
                / ".."
                / ".automation"
                / "costs"
                / "config.json"
            )
            config_file = config_file.resolve()
            config.save(config_file)
            plan_info = config.get_subscription_plan_info()
            print(
                f"{Colors.GREEN}Subscription plan set to: {plan_info['description']}{Colors.RESET}"
            )
            print(
                f"  Token Limit: {dashboard._format_tokens(plan_info['token_limit'])} tokens/month"
            )
            print(f"  Config saved to: {config_file}")
        else:
            print(f"{Colors.RED}Unknown plan: {args.set_plan}{Colors.RESET}")
            print(f"Available plans: {', '.join(SUBSCRIPTION_PLANS.keys())}")
            return 1
    elif args.schedule_export:
        dashboard.export_analytics_report(args.schedule_export, args.days)
    elif args.export:
        dashboard.export_data(args.export, sessions)
    elif args.efficiency:
        dashboard.show_efficiency()
    elif args.subscription:
        dashboard.show_subscription()
    elif args.summary:
        dashboard.show_summary(args.days)
    elif args.story:
        dashboard.show_story(args.story)
    elif args.history:
        dashboard.show_history(sessions, args.history)
    else:
        # Show latest session
        if sessions:
            dashboard.show_session(sessions[0])
        else:
            print(f"{Colors.YELLOW}No session data found.{Colors.RESET}")
            print(f"Session data is stored in: {SESSIONS_DIR}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
