#!/usr/bin/env python3
"""
Context Monitor - Real-time context usage tracking and alerting.

Monitors Claude Code context window usage and provides:
1. Real-time context estimation based on token usage
2. Proactive warnings before compaction thresholds
3. Auto-checkpoint triggers at critical levels
4. Integration with cost tracking for unified status display

Usage:
    from lib.context_monitor import ContextMonitor, StatusLine

    monitor = ContextMonitor(story_key="STORY-123")
    monitor.update_from_tokens(input_tokens=50000, output_tokens=10000)

    # Get status line for display
    status = StatusLine(monitor)
    print(status.render())
"""

import json
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent))

from colors import Colors

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONTEXT_STATE_DIR = PROJECT_ROOT / "tooling" / ".automation" / "context"

# Context window sizes (tokens) - Claude model estimates
CONTEXT_WINDOWS = {
    "opus": 200_000,
    "sonnet": 200_000,
    "haiku": 200_000,
    "default": 200_000,
}

# Thresholds (percentage of context window)
THRESHOLD_SAFE = 0.50  # 50% - Normal operation
THRESHOLD_CAUTION = 0.65  # 65% - Start being careful
THRESHOLD_WARNING = 0.75  # 75% - Visible warning
THRESHOLD_CRITICAL = 0.85  # 85% - Auto-checkpoint recommended
THRESHOLD_EMERGENCY = 0.95  # 95% - Compaction imminent


class ContextLevel(Enum):
    """Context usage level classifications."""

    SAFE = "safe"  # < 50%
    CAUTION = "caution"  # 50-65%
    WARNING = "warning"  # 65-75%
    CRITICAL = "critical"  # 75-85%
    EMERGENCY = "emergency"  # > 85%


@dataclass
class ContextState:
    """Current context window state."""

    story_key: str
    model: str = "sonnet"
    context_window: int = 200_000

    # Token tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_context_tokens: int = 0

    # History for trend analysis
    token_history: list = field(default_factory=list)

    # Timestamps
    session_start: str = field(default_factory=lambda: datetime.now().isoformat())
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())

    # Checkpoint tracking
    last_checkpoint_at: Optional[float] = None  # Context % at last checkpoint
    checkpoint_count: int = 0

    # Current activity tracking
    current_agent: Optional[str] = None
    current_task: Optional[str] = None
    current_phase: Optional[str] = None
    phase_start_time: Optional[str] = None
    phases_completed: int = 0
    total_phases: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used (in + out)."""
        return self.total_input_tokens + self.total_output_tokens

    @property
    def context_usage_ratio(self) -> float:
        """Context usage as ratio (0.0 to 1.0)."""
        if self.context_window <= 0:
            return 0.0
        # Estimate context usage - conversation grows with each exchange
        # Input tokens accumulate in context, output tokens become part of history
        return min(1.0, self.estimated_context_tokens / self.context_window)

    @property
    def context_usage_percent(self) -> float:
        """Context usage as percentage."""
        return self.context_usage_ratio * 100

    @property
    def context_level(self) -> ContextLevel:
        """Current context level classification."""
        ratio = self.context_usage_ratio
        if ratio >= THRESHOLD_EMERGENCY:
            return ContextLevel.EMERGENCY
        elif ratio >= THRESHOLD_CRITICAL:
            return ContextLevel.CRITICAL
        elif ratio >= THRESHOLD_WARNING:
            return ContextLevel.WARNING
        elif ratio >= THRESHOLD_CAUTION:
            return ContextLevel.CAUTION
        return ContextLevel.SAFE

    @property
    def tokens_remaining(self) -> int:
        """Estimated tokens remaining before compaction."""
        return max(0, self.context_window - self.estimated_context_tokens)

    @property
    def exchanges_remaining(self) -> int:
        """Estimated exchanges remaining (assuming avg 5K tokens per exchange)."""
        avg_exchange_tokens = 5000
        return max(0, self.tokens_remaining // avg_exchange_tokens)


class ContextMonitor:
    """
    Monitors and tracks context window usage.

    Provides real-time estimation, warnings, and checkpoint triggers.
    """

    def __init__(
        self,
        story_key: str,
        model: str = "sonnet",
        on_threshold: Optional[Callable[[ContextLevel, ContextState], None]] = None,
        state_dir: Optional[Path] = None,
    ):
        """
        Initialize context monitor.

        Args:
            story_key: Story identifier for state persistence
            model: Model name for context window size
            on_threshold: Callback when threshold crossed (level, state)
            state_dir: Optional custom state directory (for testing)
        """
        self.story_key = story_key
        self.model = model.lower()
        self.on_threshold = on_threshold
        self._lock = threading.Lock()
        self._state_dir = state_dir or CONTEXT_STATE_DIR

        # Initialize state
        context_window = CONTEXT_WINDOWS.get(self.model, CONTEXT_WINDOWS["default"])
        self.state = ContextState(
            story_key=story_key, model=self.model, context_window=context_window
        )

        # Track previous level for threshold crossing detection
        self._previous_level = ContextLevel.SAFE

        # Ensure state directory exists
        self._state_dir.mkdir(parents=True, exist_ok=True)

        # Try to load existing state
        self._load_state()

    def _get_state_file(self) -> Path:
        """Get path to state file."""
        return self._state_dir / f"context_{self.story_key}.json"

    def _load_state(self):
        """Load state from file if exists."""
        state_file = self._get_state_file()
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)
                    self.state = ContextState(
                        story_key=data.get("story_key", self.story_key),
                        model=data.get("model", self.model),
                        context_window=data.get(
                            "context_window", CONTEXT_WINDOWS.get(self.model, 200_000)
                        ),
                        total_input_tokens=data.get("total_input_tokens", 0),
                        total_output_tokens=data.get("total_output_tokens", 0),
                        estimated_context_tokens=data.get("estimated_context_tokens", 0),
                        token_history=data.get("token_history", []),
                        session_start=data.get("session_start", datetime.now().isoformat()),
                        last_update=data.get("last_update", datetime.now().isoformat()),
                        last_checkpoint_at=data.get("last_checkpoint_at"),
                        checkpoint_count=data.get("checkpoint_count", 0),
                    )
            except (json.JSONDecodeError, KeyError):
                pass  # Use default state

    def _save_state(self):
        """Save state to file."""
        state_file = self._get_state_file()
        with open(state_file, "w") as f:
            json.dump(
                {
                    "story_key": self.state.story_key,
                    "model": self.state.model,
                    "context_window": self.state.context_window,
                    "total_input_tokens": self.state.total_input_tokens,
                    "total_output_tokens": self.state.total_output_tokens,
                    "estimated_context_tokens": self.state.estimated_context_tokens,
                    "token_history": self.state.token_history[-100:],  # Keep last 100
                    "session_start": self.state.session_start,
                    "last_update": self.state.last_update,
                    "last_checkpoint_at": self.state.last_checkpoint_at,
                    "checkpoint_count": self.state.checkpoint_count,
                },
                f,
                indent=2,
            )

    def update_from_tokens(
        self, input_tokens: int = 0, output_tokens: int = 0, is_new_exchange: bool = True
    ):
        """
        Update context estimation from token counts.

        Args:
            input_tokens: New input tokens used
            output_tokens: New output tokens generated
            is_new_exchange: Whether this is a new exchange (vs continuation)
        """
        with self._lock:
            self.state.total_input_tokens += input_tokens
            self.state.total_output_tokens += output_tokens

            # Estimate context growth
            # Context accumulates: previous context + new input + output
            if is_new_exchange:
                # New exchange adds both input and output to context
                self.state.estimated_context_tokens += input_tokens + output_tokens
            else:
                # Continuation just adds the delta
                self.state.estimated_context_tokens += output_tokens

            # Record in history
            self.state.token_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "input": input_tokens,
                    "output": output_tokens,
                    "context": self.state.estimated_context_tokens,
                }
            )

            self.state.last_update = datetime.now().isoformat()

            # Check for threshold crossing
            current_level = self.state.context_level
            if current_level != self._previous_level:
                self._handle_threshold_crossing(current_level)
                self._previous_level = current_level

            # Persist state
            self._save_state()

    def update_from_cost_entry(self, input_tokens: int, output_tokens: int):
        """Update from a cost tracker entry."""
        self.update_from_tokens(input_tokens, output_tokens, is_new_exchange=True)

    def _handle_threshold_crossing(self, new_level: ContextLevel):
        """Handle threshold crossing event."""
        if self.on_threshold:
            self.on_threshold(new_level, self.state)

    def record_checkpoint(self):
        """Record that a checkpoint was created."""
        with self._lock:
            self.state.last_checkpoint_at = self.state.context_usage_ratio
            self.state.checkpoint_count += 1
            self._save_state()

    def reset_context(self):
        """Reset context tracking (after compaction/clear)."""
        with self._lock:
            self.state.estimated_context_tokens = 0
            self.state.token_history = []
            self.state.last_update = datetime.now().isoformat()
            self._previous_level = ContextLevel.SAFE
            self._save_state()

    def set_current_activity(
        self,
        agent: Optional[str] = None,
        task: Optional[str] = None,
        phase: Optional[str] = None,
        phases_completed: Optional[int] = None,
        total_phases: Optional[int] = None,
    ):
        """
        Set current activity information for status display.

        Args:
            agent: Current agent name (e.g., "SM", "DEV", "REVIEWER")
            task: Short description of current task
            phase: Current phase name (e.g., "Context", "Development", "Review")
            phases_completed: Number of phases completed
            total_phases: Total number of phases
        """
        with self._lock:
            if agent is not None:
                self.state.current_agent = agent
            if task is not None:
                self.state.current_task = task
            if phase is not None:
                self.state.current_phase = phase
                self.state.phase_start_time = datetime.now().isoformat()
            if phases_completed is not None:
                self.state.phases_completed = phases_completed
            if total_phases is not None:
                self.state.total_phases = total_phases
            self._save_state()

    def clear_current_activity(self):
        """Clear current activity (when idle)."""
        with self._lock:
            self.state.current_agent = None
            self.state.current_task = None
            self.state.current_phase = None
            self.state.phase_start_time = None
            self._save_state()

    def get_recommendation(self) -> str:
        """Get recommended action based on current state."""
        level = self.state.context_level

        if level == ContextLevel.EMERGENCY:
            return "CHECKPOINT NOW - Compaction imminent. Save state and clear session."
        elif level == ContextLevel.CRITICAL:
            return "Consider checkpoint - Context window filling up. Wrap up current task."
        elif level == ContextLevel.WARNING:
            return "Monitor closely - Plan to checkpoint within a few exchanges."
        elif level == ContextLevel.CAUTION:
            return "Context growing - Be aware of window limits."
        return "Context healthy - Plenty of room remaining."

    def should_checkpoint(self) -> bool:
        """Check if checkpoint is recommended."""
        return self.state.context_level in (ContextLevel.CRITICAL, ContextLevel.EMERGENCY)

    def should_warn(self) -> bool:
        """Check if warning should be displayed."""
        return self.state.context_level in (
            ContextLevel.WARNING,
            ContextLevel.CRITICAL,
            ContextLevel.EMERGENCY,
        )


class StatusLine:
    """
    Persistent status line for CLI display.

    Combines context, cost, and activity information in a compact format.
    Shows: Agent | Task | Context% | Cost | Time
    """

    # Agent display names and colors
    AGENT_COLORS = {
        "SM": Colors.CYAN,
        "DEV": Colors.GREEN,
        "REVIEWER": Colors.MAGENTA,
        "ARCHITECT": Colors.BLUE,
        "BA": Colors.YELLOW,
        "PM": Colors.CYAN,
        "MAINTAINER": Colors.YELLOW,
    }

    def __init__(
        self,
        context_monitor: Optional[ContextMonitor] = None,
        cost_tracker: Optional[object] = None,  # Avoid circular import
        width: int = 80,
    ):
        """
        Initialize status line.

        Args:
            context_monitor: ContextMonitor instance
            cost_tracker: Optional CostTracker instance
            width: Display width
        """
        self.context_monitor = context_monitor
        self.cost_tracker = cost_tracker
        self.width = width
        self._last_render = ""
        self._start_time = datetime.now()

    def _get_activity_indicator(self) -> str:
        """Get current activity indicator (agent + task + phase)."""
        if not self.context_monitor:
            return ""

        state = self.context_monitor.state

        parts = []

        # Phase progress (e.g., "[2/3]")
        if state.total_phases > 0:
            parts.append(f"[{state.phases_completed + 1}/{state.total_phases}]")

        # Current agent with color
        if state.current_agent:
            color = self.AGENT_COLORS.get(state.current_agent, Colors.WHITE)
            parts.append(f"{color}{Colors.BOLD}{state.current_agent}{Colors.RESET}")

        # Current phase/task (truncated if long)
        if state.current_phase:
            phase = state.current_phase
            if len(phase) > 20:
                phase = phase[:17] + "..."
            parts.append(f"{Colors.DIM}{phase}{Colors.RESET}")
        elif state.current_task:
            task = state.current_task
            if len(task) > 25:
                task = task[:22] + "..."
            parts.append(f"{Colors.DIM}{task}{Colors.RESET}")

        # Phase elapsed time
        if state.phase_start_time:
            try:
                start = datetime.fromisoformat(state.phase_start_time)
                elapsed = datetime.now() - start
                mins = int(elapsed.total_seconds() // 60)
                secs = int(elapsed.total_seconds() % 60)
                parts.append(f"{Colors.DIM}({mins}:{secs:02d}){Colors.RESET}")
            except (ValueError, TypeError):
                pass

        if not parts:
            return f"{Colors.DIM}Idle{Colors.RESET}"

        return " ".join(parts)

    def _get_context_indicator(self) -> str:
        """Get context usage indicator with color."""
        if not self.context_monitor:
            return ""

        state = self.context_monitor.state
        pct = state.context_usage_percent
        level = state.context_level

        # Color and icon based on level
        if level == ContextLevel.EMERGENCY:
            color = Colors.BG_RED + Colors.WHITE
            icon = "[!!!]"
        elif level == ContextLevel.CRITICAL:
            color = Colors.BOLD_RED
            icon = "[!!]"
        elif level == ContextLevel.WARNING:
            color = Colors.BOLD_YELLOW
            icon = "[!]"
        elif level == ContextLevel.CAUTION:
            color = Colors.YELLOW
            icon = ""
        else:
            color = Colors.GREEN
            icon = ""

        # Format: Ctx: 45% [=====     ] ~12 left
        bar_width = 10
        filled = int((pct / 100) * bar_width)
        bar = "=" * filled + " " * (bar_width - filled)

        remaining = state.exchanges_remaining
        remaining_str = f"~{remaining} left" if remaining < 50 else ""

        return f"{color}Ctx: {pct:.0f}% [{bar}] {icon}{remaining_str}{Colors.RESET}"

    def _get_cost_indicator(self) -> str:
        """Get cost indicator with color."""
        if not self.cost_tracker:
            return ""

        try:
            session = self.cost_tracker.session
            pct = session.budget_used_percent
            cost = session.total_cost_usd

            if pct >= 90:
                color = Colors.RED
            elif pct >= 75:
                color = Colors.YELLOW
            else:
                color = Colors.GREEN

            return f"{color}Cost: ${cost:.2f} ({pct:.0f}%){Colors.RESET}"
        except Exception:
            return ""

    def _get_time_indicator(self) -> str:
        """Get elapsed time indicator."""
        return f"{Colors.DIM}{datetime.now().strftime('%H:%M:%S')}{Colors.RESET}"

    def render(self, include_border: bool = False) -> str:
        """
        Render the status line.

        Format: [1/3] DEV Development (0:45) | Ctx: 45% [=====     ] | Cost: $1.23 (12%) | 14:32:01

        Args:
            include_border: Whether to include a top border line
        """
        parts = []

        # Activity (agent + task + phase progress)
        activity = self._get_activity_indicator()
        if activity:
            parts.append(activity)

        # Context usage
        ctx = self._get_context_indicator()
        if ctx:
            parts.append(ctx)

        # Cost
        cost = self._get_cost_indicator()
        if cost:
            parts.append(cost)

        # Time
        parts.append(self._get_time_indicator())

        # Join with separator
        content = f" {Colors.DIM}|{Colors.RESET} ".join(parts)

        if include_border:
            border = f"{Colors.DIM}{'─' * self.width}{Colors.RESET}"
            return f"{border}\n{content}"

        self._last_render = content
        return content

    def render_warning(self) -> Optional[str]:
        """Render warning message if threshold crossed."""
        if not self.context_monitor:
            return None

        if not self.context_monitor.should_warn():
            return None

        state = self.context_monitor.state
        level = state.context_level
        rec = self.context_monitor.get_recommendation()

        if level == ContextLevel.EMERGENCY:
            return f"\n{Colors.BG_RED}{Colors.WHITE} CONTEXT EMERGENCY {Colors.RESET} {rec}"
        elif level == ContextLevel.CRITICAL:
            return f"\n{Colors.BOLD_RED}[CRITICAL]{Colors.RESET} {rec}"
        elif level == ContextLevel.WARNING:
            return f"\n{Colors.YELLOW}[WARNING]{Colors.RESET} {rec}"

        return None

    def print(self, newline: bool = True):
        """Print status line to terminal."""
        output = self.render()
        warning = self.render_warning()

        if warning:
            output += warning

        if newline:
            print(output)
        else:
            print(f"\r{output}", end="", flush=True)

    def print_header(self, title: str = ""):
        """Print status line as a header with title."""
        border = f"{Colors.DIM}{'─' * self.width}{Colors.RESET}"
        status = self.render()

        if title:
            print(f"{border}")
            print(f"{Colors.BOLD}{title}{Colors.RESET}")
            print(f"{status}")
            print(f"{border}")
        else:
            print(f"{border}")
            print(f"{status}")
            print(f"{border}")


class StatusLineManager:
    """
    Manages persistent status line updates across CLI operations.

    Provides a consistent status display that can be updated from anywhere.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self, story_key: Optional[str] = None, model: str = "sonnet", auto_refresh: bool = False
    ):
        """
        Initialize or update the status line manager.

        Args:
            story_key: Story identifier
            model: Model name
            auto_refresh: Whether to auto-refresh on a timer
        """
        if self._initialized and story_key is None:
            return  # Already initialized, no update needed

        self.story_key = story_key or "default"
        self.model = model
        self.auto_refresh = auto_refresh

        # Create monitor
        self.context_monitor = ContextMonitor(
            story_key=self.story_key, model=self.model, on_threshold=self._on_threshold
        )

        # Cost tracker set externally
        self.cost_tracker = None

        # Status line
        self.status_line = StatusLine(context_monitor=self.context_monitor)

        # Auto-refresh thread
        self._refresh_thread = None
        self._stop_refresh = threading.Event()

        if auto_refresh:
            self._start_auto_refresh()

        self._initialized = True

    def _on_threshold(self, level: ContextLevel, state: ContextState):
        """Handle threshold crossing."""
        if level in (ContextLevel.CRITICAL, ContextLevel.EMERGENCY):
            # Print immediate warning
            warning = self.status_line.render_warning()
            if warning:
                print(warning)

    def set_cost_tracker(self, tracker):
        """Set cost tracker for combined display."""
        self.cost_tracker = tracker
        self.status_line.cost_tracker = tracker

    def update_tokens(self, input_tokens: int, output_tokens: int):
        """Update context from token usage."""
        self.context_monitor.update_from_tokens(input_tokens, output_tokens)

    def print_status(self, newline: bool = True):
        """Print current status line."""
        self.status_line.print(newline=newline)

    def print_header(self, title: str = ""):
        """Print status as header."""
        self.status_line.print_header(title)

    def should_checkpoint(self) -> bool:
        """Check if checkpoint recommended."""
        return self.context_monitor.should_checkpoint()

    def record_checkpoint(self):
        """Record checkpoint event."""
        self.context_monitor.record_checkpoint()

    def reset(self):
        """Reset context tracking."""
        self.context_monitor.reset_context()

    def _start_auto_refresh(self, interval: float = 5.0):
        """Start auto-refresh thread."""
        if self._refresh_thread is not None:
            return

        def refresh_loop():
            while not self._stop_refresh.is_set():
                self.print_status(newline=False)
                time.sleep(interval)

        self._refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self._refresh_thread.start()

    def stop_auto_refresh(self):
        """Stop auto-refresh thread."""
        self._stop_refresh.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=1.0)


# Global instance getter
def get_status_manager(
    story_key: Optional[str] = None, model: str = "sonnet"
) -> StatusLineManager:
    """Get or create the global status line manager."""
    return StatusLineManager(story_key=story_key, model=model)


if __name__ == "__main__":
    # Demo
    print("Context Monitor Demo\n")

    monitor = ContextMonitor(story_key="demo-story", model="sonnet")

    # Simulate token usage growth
    status = StatusLine(context_monitor=monitor)

    print("Initial state:")
    status.print_header("DEVFLOW STATUS")

    # Simulate exchanges
    exchanges = [
        (15000, 3000),  # Small exchange
        (25000, 8000),  # Medium exchange
        (40000, 12000),  # Large exchange
        (30000, 10000),  # Another exchange
        (50000, 15000),  # Big exchange - should trigger caution
    ]

    for i, (inp, out) in enumerate(exchanges, 1):
        print(f"\nExchange {i}: +{inp:,} input, +{out:,} output")
        monitor.update_from_tokens(inp, out)
        status.print()

        if monitor.should_warn():
            print(f"  Recommendation: {monitor.get_recommendation()}")

    print("\n" + "=" * 60)
    print("Final state:")
    status.print_header("DEVFLOW STATUS")
