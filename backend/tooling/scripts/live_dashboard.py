#!/usr/bin/env python3
"""
Live Dashboard - Real-time status display for Devflow.

Provides a rich, auto-updating terminal dashboard showing:
- Current agent and activity
- Context window usage with visual progress bar
- Cost tracking with budget visualization
- Token history and trends
- Session statistics

Usage:
    python live_dashboard.py [story-key] [options]

Options:
    --refresh SECONDS    Refresh interval (default: 0.5)
    --compact            Use compact single-line mode
    --no-color           Disable colors
    --width WIDTH        Dashboard width (default: 70)

Examples:
    python live_dashboard.py 3-5
    python live_dashboard.py 3-5 --refresh 0.25
    python live_dashboard.py --compact
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# Add lib directory for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

try:
    from lib.platform import IS_WINDOWS
except ImportError:
    IS_WINDOWS = sys.platform == "win32"

# Project paths
PROJECT_ROOT = SCRIPT_DIR.parent.parent
CONTEXT_STATE_DIR = PROJECT_ROOT / "tooling" / ".automation" / "context"
COST_SESSIONS_DIR = PROJECT_ROOT / "tooling" / ".automation" / "costs" / "sessions"


# ANSI escape codes
class Colors:
    """ANSI color codes for terminal output."""

    # Basic colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"

    # Background
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"

    # Reset
    RESET = "\033[0m"
    END = "\033[0m"

    @classmethod
    def disable(cls):
        """Disable all colors."""
        for attr in dir(cls):
            if not attr.startswith("_") and attr != "disable":
                setattr(cls, attr, "")


# Box drawing characters
class Box:
    """Box drawing characters for dashboard frames."""

    # Single line
    TOP_LEFT = "╔"
    TOP_RIGHT = "╗"
    BOTTOM_LEFT = "╚"
    BOTTOM_RIGHT = "╝"
    HORIZONTAL = "═"
    VERTICAL = "║"
    T_LEFT = "╠"
    T_RIGHT = "╣"
    T_TOP = "╦"
    T_BOTTOM = "╩"
    CROSS = "╬"

    # Progress bar characters
    BLOCK_FULL = "█"
    BLOCK_7_8 = "▉"
    BLOCK_3_4 = "▊"
    BLOCK_5_8 = "▋"
    BLOCK_HALF = "▌"
    BLOCK_3_8 = "▍"
    BLOCK_1_4 = "▎"
    BLOCK_1_8 = "▏"
    BLOCK_EMPTY = "░"

    # Trend indicators
    ARROW_UP = "▲"
    ARROW_DOWN = "▼"
    ARROW_RIGHT = "▶"
    ARROW_FLAT = "─"

    # Status indicators
    DOT_FILLED = "●"
    DOT_EMPTY = "○"
    CHECK = "✓"
    CROSS_MARK = "✗"
    SPINNER = ["◐", "◓", "◑", "◒"]


class DashboardState:
    """Holds the current dashboard state loaded from files."""

    def __init__(self, story_key: str = "default"):
        self.story_key = story_key
        self.last_update = datetime.now()

        # Context state
        self.context_percent = 0.0
        self.context_tokens = 0
        self.context_window = 200000
        self.tokens_remaining = 200000
        self.exchanges_remaining = 40

        # Activity state
        self.current_agent = None
        self.current_phase = None
        self.current_task = None
        self.phase_start_time = None
        self.phases_completed = 0
        self.total_phases = 0

        # Cost state
        self.cost_usd = 0.0
        self.budget_usd = 15.0
        self.cost_percent = 0.0
        self.input_tokens = 0
        self.output_tokens = 0

        # History
        self.token_history = []
        self.session_start = datetime.now()

        # Status
        self.is_active = False
        self.last_file_update = None

    def load_context_state(self):
        """Load context state from file."""
        state_file = CONTEXT_STATE_DIR / f"context_{self.story_key}.json"
        if state_file.exists():
            try:
                mtime = datetime.fromtimestamp(state_file.stat().st_mtime)
                self.last_file_update = mtime

                with open(state_file) as f:
                    data = json.load(f)

                self.context_window = data.get("context_window", 200000)
                self.context_tokens = data.get("estimated_context_tokens", 0)
                self.context_percent = (
                    (self.context_tokens / self.context_window * 100)
                    if self.context_window > 0
                    else 0
                )
                self.tokens_remaining = max(0, self.context_window - self.context_tokens)
                self.exchanges_remaining = self.tokens_remaining // 5000

                self.input_tokens = data.get("total_input_tokens", 0)
                self.output_tokens = data.get("total_output_tokens", 0)
                self.token_history = data.get("token_history", [])[-10:]

                if data.get("session_start"):
                    try:
                        self.session_start = datetime.fromisoformat(data["session_start"])
                    except (ValueError, TypeError):
                        pass

                # Check if recently updated (within last 30 seconds)
                if data.get("last_update"):
                    try:
                        last = datetime.fromisoformat(data["last_update"])
                        self.is_active = (datetime.now() - last).total_seconds() < 30
                    except (ValueError, TypeError):
                        self.is_active = False

            except (OSError, json.JSONDecodeError):
                pass

    def load_cost_state(self):
        """Load cost state from session files."""
        if not COST_SESSIONS_DIR.exists():
            return

        # Find most recent session file for this story
        session_files = list(COST_SESSIONS_DIR.glob(f"*{self.story_key}*.json"))
        if not session_files:
            # Try to find any recent session
            session_files = list(COST_SESSIONS_DIR.glob("*.json"))

        if session_files:
            # Get most recent
            latest = max(session_files, key=lambda p: p.stat().st_mtime)
            try:
                with open(latest) as f:
                    data = json.load(f)

                self.cost_usd = data.get("total_cost_usd", 0.0)
                self.budget_usd = data.get("budget_limit_usd", 15.0)
                self.cost_percent = (
                    (self.cost_usd / self.budget_usd * 100) if self.budget_usd > 0 else 0
                )

            except (OSError, json.JSONDecodeError):
                pass

    def load_activity_state(self):
        """Load current activity from context state."""
        state_file = CONTEXT_STATE_DIR / f"context_{self.story_key}.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)

                self.current_agent = data.get("current_agent")
                self.current_phase = data.get("current_phase")
                self.current_task = data.get("current_task")
                self.phases_completed = data.get("phases_completed", 0)
                self.total_phases = data.get("total_phases", 0)

                if data.get("phase_start_time"):
                    try:
                        self.phase_start_time = datetime.fromisoformat(data["phase_start_time"])
                    except (ValueError, TypeError):
                        self.phase_start_time = None

            except (OSError, json.JSONDecodeError):
                pass

    def refresh(self):
        """Refresh all state from files."""
        self.load_context_state()
        self.load_cost_state()
        self.load_activity_state()
        self.last_update = datetime.now()


class LiveDashboard:
    """
    Rich terminal dashboard with real-time updates.

    Displays context, cost, activity, and history in a visual format.
    """

    AGENT_COLORS = {
        "SM": Colors.CYAN,
        "DEV": Colors.GREEN,
        "REVIEWER": Colors.MAGENTA,
        "ARCHITECT": Colors.BLUE,
        "BA": Colors.YELLOW,
        "PM": Colors.CYAN,
        "MAINTAINER": Colors.YELLOW,
        "SECURITY": Colors.RED,
    }

    def __init__(
        self,
        story_key: str = "default",
        width: int = 70,
        refresh_interval: float = 0.5,
        compact: bool = False,
    ):
        self.story_key = story_key
        self.width = width
        self.refresh_interval = refresh_interval
        self.compact = compact
        self.state = DashboardState(story_key)
        self.running = False
        self.spinner_index = 0
        self.frame_count = 0

    def _clear_screen(self):
        """Clear terminal screen."""
        if IS_WINDOWS:
            os.system("cls")
        else:
            # Use ANSI escape to clear and move cursor to top
            print("\033[2J\033[H", end="")

    def _move_cursor_home(self):
        """Move cursor to top-left without clearing."""
        print("\033[H", end="")

    def _hide_cursor(self):
        """Hide terminal cursor."""
        print("\033[?25l", end="")

    def _show_cursor(self):
        """Show terminal cursor."""
        print("\033[?25h", end="")

    def _draw_line(self, left: str, fill: str, right: str, content: str = "") -> str:
        """Draw a line with borders and optional content."""
        inner_width = self.width - 2
        if content:
            padding = inner_width - len(self._strip_ansi(content))
            if padding < 0:
                content = content[:inner_width]
                padding = 0
            return f"{left}{content}{' ' * padding}{right}"
        return f"{left}{fill * inner_width}{right}"

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes for length calculation."""
        import re

        return re.sub(r"\033\[[0-9;]*m", "", text)

    def _pad_content(self, content: str, width: int, align: str = "left") -> str:
        """Pad content to width, accounting for ANSI codes."""
        visible_len = len(self._strip_ansi(content))
        padding = width - visible_len
        if padding <= 0:
            return content
        if align == "center":
            left_pad = padding // 2
            right_pad = padding - left_pad
            return " " * left_pad + content + " " * right_pad
        elif align == "right":
            return " " * padding + content
        return content + " " * padding

    def _progress_bar(
        self,
        percent: float,
        width: int = 20,
        filled_color: str = Colors.GREEN,
        empty_color: str = Colors.DIM,
        show_percent: bool = True,
    ) -> str:
        """Create a colored progress bar."""
        percent = max(0, min(100, percent))
        filled = int((percent / 100) * width)
        empty = width - filled

        bar = f"{filled_color}{Box.BLOCK_FULL * filled}{Colors.RESET}"
        bar += f"{empty_color}{Box.BLOCK_EMPTY * empty}{Colors.RESET}"

        if show_percent:
            bar += f" {percent:5.1f}%"

        return bar

    def _get_context_color(self, percent: float) -> str:
        """Get color based on context usage level."""
        if percent >= 85:
            return Colors.BRIGHT_RED
        elif percent >= 75:
            return Colors.RED
        elif percent >= 65:
            return Colors.YELLOW
        elif percent >= 50:
            return Colors.BRIGHT_YELLOW
        return Colors.GREEN

    def _get_cost_color(self, percent: float) -> str:
        """Get color based on cost usage level."""
        if percent >= 90:
            return Colors.BRIGHT_RED
        elif percent >= 75:
            return Colors.YELLOW
        return Colors.GREEN

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS."""
        if seconds < 0:
            return "0:00"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _format_tokens(self, tokens: int) -> str:
        """Format token count with K/M suffix."""
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.1f}M"
        elif tokens >= 1000:
            return f"{tokens / 1000:.1f}K"
        return str(tokens)

    def _get_trend_indicator(self) -> str:
        """Calculate trend from recent token history."""
        history = self.state.token_history
        if len(history) < 2:
            return f"{Colors.DIM}{Box.ARROW_FLAT}{Colors.RESET}"

        # Compare last two entries
        recent = history[-1].get("context", 0)
        previous = history[-2].get("context", 0)

        if recent > previous:
            delta = recent - previous
            if delta > 10000:
                return f"{Colors.RED}{Box.ARROW_UP}{Box.ARROW_UP}{Colors.RESET}"
            return f"{Colors.YELLOW}{Box.ARROW_UP}{Colors.RESET}"
        elif recent < previous:
            return f"{Colors.GREEN}{Box.ARROW_DOWN}{Colors.RESET}"
        return f"{Colors.DIM}{Box.ARROW_FLAT}{Colors.RESET}"

    def _render_header(self) -> list[str]:
        """Render dashboard header."""
        lines = []

        # Top border with title
        title = " DEVFLOW LIVE DASHBOARD "
        title_colored = f"{Colors.BOLD}{Colors.CYAN}{title}{Colors.RESET}"

        left_border = Box.TOP_LEFT + Box.HORIZONTAL * 2
        right_border = Box.HORIZONTAL * 2 + Box.TOP_RIGHT
        middle_width = self.width - len(left_border) - len(right_border) - len(title)
        left_fill = Box.HORIZONTAL * (middle_width // 2)
        right_fill = Box.HORIZONTAL * (middle_width - middle_width // 2)

        lines.append(
            f"{Colors.CYAN}{left_border}{left_fill}{Colors.RESET}{title_colored}{Colors.CYAN}{right_fill}{right_border}{Colors.RESET}"
        )

        # Status line
        spinner = Box.SPINNER[self.spinner_index % len(Box.SPINNER)]
        status_indicator = (
            f"{Colors.GREEN}{spinner}{Colors.RESET}"
            if self.state.is_active
            else f"{Colors.DIM}{Box.DOT_EMPTY}{Colors.RESET}"
        )

        story_display = f"Story: {Colors.BOLD}{self.story_key}{Colors.RESET}"
        time_display = f"{Colors.DIM}{datetime.now().strftime('%H:%M:%S')}{Colors.RESET}"

        status_content = f" {status_indicator} {story_display}{''.ljust(20)}{time_display} "
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(status_content, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Separator
        lines.append(
            f"{Colors.CYAN}{Box.T_LEFT}{Box.HORIZONTAL * (self.width - 2)}{Box.T_RIGHT}{Colors.RESET}"
        )

        return lines

    def _render_activity(self) -> list[str]:
        """Render current activity section."""
        lines = []

        # Section header
        section_title = f" {Colors.BOLD}ACTIVITY{Colors.RESET} "
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(section_title, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Agent and phase
        if self.state.current_agent:
            agent_color = self.AGENT_COLORS.get(self.state.current_agent, Colors.WHITE)
            agent_display = f"{agent_color}{Colors.BOLD}{self.state.current_agent}{Colors.RESET}"

            phase_display = ""
            if self.state.total_phases > 0:
                phase_display = f" [{self.state.phases_completed + 1}/{self.state.total_phases}]"

            if self.state.current_phase:
                phase_name = self.state.current_phase
                if len(phase_name) > 25:
                    phase_name = phase_name[:22] + "..."
                phase_display += f" {Colors.DIM}{phase_name}{Colors.RESET}"

            # Elapsed time
            time_display = ""
            if self.state.phase_start_time:
                elapsed = (datetime.now() - self.state.phase_start_time).total_seconds()
                time_display = f" {Colors.DIM}({self._format_time(elapsed)}){Colors.RESET}"

            agent_line = f"  Agent: {agent_display}{phase_display}{time_display}"
        else:
            agent_line = f"  {Colors.DIM}No active agent{Colors.RESET}"

        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(agent_line, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Task
        if self.state.current_task:
            task = self.state.current_task
            max_task_len = self.width - 12
            if len(task) > max_task_len:
                task = task[: max_task_len - 3] + "..."
            task_line = f"  Task: {Colors.DIM}{task}{Colors.RESET}"
        else:
            task_line = f"  {Colors.DIM}No active task{Colors.RESET}"

        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(task_line, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Separator
        lines.append(
            f"{Colors.CYAN}{Box.T_LEFT}{Box.HORIZONTAL * (self.width - 2)}{Box.T_RIGHT}{Colors.RESET}"
        )

        return lines

    def _render_context(self) -> list[str]:
        """Render context usage section."""
        lines = []

        # Section header
        section_title = f" {Colors.BOLD}CONTEXT{Colors.RESET} "
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(section_title, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Progress bar
        ctx_color = self._get_context_color(self.state.context_percent)
        bar = self._progress_bar(
            self.state.context_percent,
            width=30,
            filled_color=ctx_color,
        )
        trend = self._get_trend_indicator()

        ctx_line = f"  Usage: {bar} {trend}"
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(ctx_line, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Details line
        tokens_display = f"{self._format_tokens(self.state.context_tokens)}/{self._format_tokens(self.state.context_window)}"
        remaining_display = f"~{self.state.exchanges_remaining} exchanges left"

        if self.state.context_percent >= 75:
            remaining_display = f"{Colors.YELLOW}{remaining_display}{Colors.RESET}"
        elif self.state.context_percent >= 85:
            remaining_display = f"{Colors.RED}{remaining_display}{Colors.RESET}"

        detail_line = f"  Tokens: {Colors.DIM}{tokens_display}{Colors.RESET}  {remaining_display}"
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(detail_line, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Warning if critical
        if self.state.context_percent >= 85:
            warning = f"  {Colors.BG_RED}{Colors.WHITE} CHECKPOINT RECOMMENDED {Colors.RESET}"
            lines.append(
                f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(warning, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
            )
        elif self.state.context_percent >= 75:
            warning = (
                f"  {Colors.YELLOW}[!] Context filling up - plan to checkpoint soon{Colors.RESET}"
            )
            lines.append(
                f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(warning, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
            )

        # Separator
        lines.append(
            f"{Colors.CYAN}{Box.T_LEFT}{Box.HORIZONTAL * (self.width - 2)}{Box.T_RIGHT}{Colors.RESET}"
        )

        return lines

    def _render_cost(self) -> list[str]:
        """Render cost tracking section."""
        lines = []

        # Section header
        section_title = f" {Colors.BOLD}COST{Colors.RESET} "
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(section_title, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Progress bar
        cost_color = self._get_cost_color(self.state.cost_percent)
        bar = self._progress_bar(
            self.state.cost_percent,
            width=30,
            filled_color=cost_color,
        )

        cost_line = f"  Budget: {bar}"
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(cost_line, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Cost details
        cost_display = f"${self.state.cost_usd:.2f} / ${self.state.budget_usd:.2f}"
        tokens_display = f"In: {self._format_tokens(self.state.input_tokens)}  Out: {self._format_tokens(self.state.output_tokens)}"

        detail_line = f"  Spent: {Colors.BOLD}{cost_display}{Colors.RESET}  {Colors.DIM}{tokens_display}{Colors.RESET}"
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(detail_line, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Separator
        lines.append(
            f"{Colors.CYAN}{Box.T_LEFT}{Box.HORIZONTAL * (self.width - 2)}{Box.T_RIGHT}{Colors.RESET}"
        )

        return lines

    def _render_history(self) -> list[str]:
        """Render recent token history."""
        lines = []

        # Section header
        section_title = f" {Colors.BOLD}RECENT{Colors.RESET} "
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(section_title, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        history = self.state.token_history[-5:]  # Last 5 entries

        if not history:
            empty_line = f"  {Colors.DIM}No recent activity{Colors.RESET}"
            lines.append(
                f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(empty_line, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
            )
        else:
            for entry in reversed(history):
                try:
                    ts = datetime.fromisoformat(entry.get("timestamp", ""))
                    elapsed = (datetime.now() - ts).total_seconds()

                    if elapsed < 60:
                        time_str = f"{int(elapsed)}s ago"
                    elif elapsed < 3600:
                        time_str = f"{int(elapsed // 60)}m ago"
                    else:
                        time_str = f"{int(elapsed // 3600)}h ago"

                    tokens = entry.get("input", 0) + entry.get("output", 0)
                    entry_line = f"  {Colors.DIM}{Box.ARROW_RIGHT}{Colors.RESET} +{self._format_tokens(tokens)} tokens {Colors.DIM}({time_str}){Colors.RESET}"
                    lines.append(
                        f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(entry_line, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
                    )
                except (ValueError, TypeError, KeyError):
                    continue

        return lines

    def _render_footer(self) -> list[str]:
        """Render dashboard footer."""
        lines = []

        # Session stats
        session_elapsed = (datetime.now() - self.state.session_start).total_seconds()
        session_time = self._format_time(session_elapsed)

        if self.state.last_file_update:
            last_update = self.state.last_file_update.strftime("%H:%M:%S")
        else:
            last_update = "N/A"

        footer_content = f"  Session: {session_time}  {Colors.DIM}|{Colors.RESET}  Last update: {last_update}  {Colors.DIM}|{Colors.RESET}  {Colors.DIM}Ctrl+C to exit{Colors.RESET}"
        lines.append(
            f"{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}{self._pad_content(footer_content, self.width - 2)}{Colors.CYAN}{Box.VERTICAL}{Colors.RESET}"
        )

        # Bottom border
        lines.append(
            f"{Colors.CYAN}{Box.BOTTOM_LEFT}{Box.HORIZONTAL * (self.width - 2)}{Box.BOTTOM_RIGHT}{Colors.RESET}"
        )

        return lines

    def _render_compact(self) -> str:
        """Render compact single-line status."""
        agent = self.state.current_agent or "Idle"
        ctx = f"{self.state.context_percent:.0f}%"
        cost = f"${self.state.cost_usd:.2f}"

        ctx_color = self._get_context_color(self.state.context_percent)
        cost_color = self._get_cost_color(self.state.cost_percent)
        agent_color = self.AGENT_COLORS.get(self.state.current_agent, Colors.DIM)

        spinner = (
            Box.SPINNER[self.spinner_index % len(Box.SPINNER)]
            if self.state.is_active
            else Box.DOT_EMPTY
        )

        return f"{spinner} {agent_color}{agent}{Colors.RESET} | Ctx: {ctx_color}{ctx}{Colors.RESET} | Cost: {cost_color}{cost}{Colors.RESET} | {datetime.now().strftime('%H:%M:%S')}"

    def render(self) -> str:
        """Render the full dashboard."""
        if self.compact:
            return self._render_compact()

        lines = []
        lines.extend(self._render_header())
        lines.extend(self._render_activity())
        lines.extend(self._render_context())
        lines.extend(self._render_cost())
        lines.extend(self._render_history())
        lines.extend(self._render_footer())

        return "\n".join(lines)

    def run(self):
        """Run the dashboard update loop."""
        self.running = True

        # Setup signal handler for clean exit
        def signal_handler(sig, frame):
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self._hide_cursor()
            self._clear_screen()

            while self.running:
                # Refresh state from files
                self.state.refresh()

                # Render dashboard
                if self.compact:
                    print(f"\r{self.render()}", end="", flush=True)
                else:
                    self._move_cursor_home()
                    print(self.render(), flush=True)

                # Update spinner
                self.spinner_index += 1
                self.frame_count += 1

                # Wait for next refresh
                time.sleep(self.refresh_interval)

        finally:
            self._show_cursor()
            if not self.compact:
                print()  # Newline after exit


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Live dashboard for Devflow status monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python live_dashboard.py 3-5
  python live_dashboard.py 3-5 --refresh 0.25
  python live_dashboard.py --compact
  python live_dashboard.py --width 80
        """,
    )

    parser.add_argument(
        "story_key", nargs="?", default="default", help="Story key to monitor (default: 'default')"
    )
    parser.add_argument(
        "--refresh",
        "-r",
        type=float,
        default=0.5,
        help="Refresh interval in seconds (default: 0.5)",
    )
    parser.add_argument("--compact", "-c", action="store_true", help="Use compact single-line mode")
    parser.add_argument("--no-color", action="store_true", help="Disable colors")
    parser.add_argument("--width", "-w", type=int, default=70, help="Dashboard width (default: 70)")

    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    dashboard = LiveDashboard(
        story_key=args.story_key,
        width=args.width,
        refresh_interval=args.refresh,
        compact=args.compact,
    )

    try:
        dashboard.run()
    except KeyboardInterrupt:
        pass

    print(f"\n{Colors.DIM}Dashboard stopped.{Colors.RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
