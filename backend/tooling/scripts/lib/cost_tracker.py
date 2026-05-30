#!/usr/bin/env python3
"""
Cost Tracker - Core cost tracking engine for Claude Code automation.

Tracks token usage, calculates costs, monitors budgets, and stores session data.

Usage:
    from lib.cost_tracker import CostTracker

    tracker = CostTracker(story_key="3-5", budget_limit_usd=15.00)
    tracker.log_usage(agent="DEV", model="opus", input_tokens=1000, output_tokens=500)
    print(tracker.get_session_summary())
"""

import json
import re
import sys
import threading
import uuid
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

# Try to import enhanced error handling
try:
    from errors import (
        BudgetError,
        CalculationError,
        CostTrackingError,
        ErrorCode,
        ErrorContext,
        SessionError,
        create_error,
        log_warning,
    )

    ENHANCED_ERRORS = True
except ImportError:
    ENHANCED_ERRORS = False
    # Warn user about degraded functionality (only once)
    warnings.warn(
        "Enhanced error handling not available (errors.py not found). "
        "Using basic error classes. For better error messages, ensure "
        "errors.py is in the lib directory.",
        ImportWarning,
        stacklevel=2,
    )

    # Fallback error classes
    class CostTrackingError(Exception):
        pass

    class SessionError(Exception):
        pass

    class BudgetError(Exception):
        pass

    class CalculationError(Exception):
        pass


# Token pricing per 1M tokens (USD)
# Last updated: December 2025
# Source: https://www.anthropic.com/pricing
# NOTE: Verify pricing at source before production use - rates may change
PRICING = {
    # Claude 3.5 models (current generation)
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    # Claude 3 models
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # Short aliases (for convenience)
    "opus": {"input": 15.00, "output": 75.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.80, "output": 4.00},
}

# Default budget thresholds
DEFAULT_THRESHOLDS = {
    "warning": 0.75,  # 75% - Yellow warning
    "critical": 0.90,  # 90% - Red warning
    "stop": 1.00,  # 100% - Auto-stop
}

# Cache for model pricing lookups (model_lower -> pricing dict)
_pricing_cache: dict[str, dict[str, float]] = {}


def _get_pricing(model: str) -> tuple[dict[str, float], bool]:
    """Get pricing for a model with caching.

    Args:
        model: Model name

    Returns:
        Tuple of (pricing dict, is_default) where is_default indicates if
        sonnet default pricing was used for an unknown model.
    """
    model_lower = model.lower()

    # Check cache first
    if model_lower in _pricing_cache:
        return _pricing_cache[model_lower], False

    # Search for matching pricing
    for key, price in PRICING.items():
        if key in model_lower or model_lower in key:
            _pricing_cache[model_lower] = price
            return price, False

    # Cache and return default
    _pricing_cache[model_lower] = PRICING["sonnet"]
    return PRICING["sonnet"], True


# Storage paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
COSTS_DIR = PROJECT_ROOT / "tooling" / ".automation" / "costs"
SESSIONS_DIR = COSTS_DIR / "sessions"


@dataclass
class CostEntry:
    """Single cost entry for a Claude API call."""

    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    agent: str = "unknown"  # Optional for backwards compatibility

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SessionCost:
    """Complete cost data for a session."""

    session_id: str
    story_key: str
    start_time: str
    end_time: Optional[str] = None
    budget_limit_usd: float = 15.00
    entries: list[CostEntry] = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(e.input_tokens for e in self.entries)

    @property
    def total_output_tokens(self) -> int:
        return sum(e.output_tokens for e in self.entries)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def total_cost_usd(self) -> float:
        return sum(e.cost_usd for e in self.entries)

    @property
    def budget_remaining(self) -> float:
        return max(0, self.budget_limit_usd - self.total_cost_usd)

    @property
    def budget_used_percent(self) -> float:
        if self.budget_limit_usd <= 0:
            return 0
        return min(100, (self.total_cost_usd / self.budget_limit_usd) * 100)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "story_key": self.story_key,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "budget_limit_usd": self.budget_limit_usd,
            "entries": [e.to_dict() for e in self.entries],
            "totals": {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "total_tokens": self.total_tokens,
                "cost_usd": round(self.total_cost_usd, 4),
                "budget_remaining": round(self.budget_remaining, 4),
                "budget_used_percent": round(self.budget_used_percent, 2),
            },
        }

    def get_cost_by_agent(self) -> dict[str, float]:
        """Get cost breakdown by agent."""
        costs = {}
        for entry in self.entries:
            if entry.agent not in costs:
                costs[entry.agent] = 0
            costs[entry.agent] += entry.cost_usd
        return costs

    def get_cost_by_model(self) -> dict[str, float]:
        """Get cost breakdown by model."""
        costs = {}
        for entry in self.entries:
            if entry.model not in costs:
                costs[entry.model] = 0
            costs[entry.model] += entry.cost_usd
        return costs

    def get_tokens_by_agent(self) -> dict[str, dict[str, int]]:
        """Get token breakdown by agent."""
        tokens = {}
        for entry in self.entries:
            if entry.agent not in tokens:
                tokens[entry.agent] = {"input": 0, "output": 0}
            tokens[entry.agent]["input"] += entry.input_tokens
            tokens[entry.agent]["output"] += entry.output_tokens
        return tokens


class CostTracker:
    """
    Main cost tracking class.

    Tracks token usage, calculates costs, monitors budgets.
    """

    def __init__(
        self,
        story_key: str = "unknown",
        budget_limit_usd: float = 15.00,
        thresholds: Optional[dict[str, float]] = None,
        auto_save: bool = True,
    ):
        self.story_key = story_key
        self.budget_limit_usd = budget_limit_usd
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.copy()
        self.auto_save = auto_save

        # Generate session ID
        self.session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Initialize session
        self.session = SessionCost(
            session_id=self.session_id,
            story_key=story_key,
            start_time=datetime.now().isoformat(),
            budget_limit_usd=budget_limit_usd,
        )

        # Ensure directories exist
        COSTS_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

        # Current agent/model tracking
        self.current_agent = None
        self.current_model = None

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for a given usage.

        Args:
            model: Model name (opus, sonnet, haiku, or full Claude model name)
            input_tokens: Number of input tokens (must be >= 0)
            output_tokens: Number of output tokens (must be >= 0)

        Returns:
            Calculated cost in USD

        Raises:
            CalculationError: If token counts are invalid or non-numeric
        """
        # Validate input types
        try:
            input_tokens = int(input_tokens)
            output_tokens = int(output_tokens)
        except (TypeError, ValueError) as e:
            error_msg = f"Token counts must be numeric: {e}"
            if ENHANCED_ERRORS:
                raise create_error(
                    ErrorCode.INVALID_TOKENS,
                    context=ErrorContext(operation="calculating cost", model=model),
                    custom_message=error_msg,
                ) from e
            raise CalculationError(error_msg) from e

        # Validate inputs
        if input_tokens < 0:
            error_msg = f"Invalid input_tokens: {input_tokens}. Token count cannot be negative."
            if ENHANCED_ERRORS:
                raise create_error(
                    ErrorCode.INVALID_TOKENS,
                    context=ErrorContext(operation="calculating cost", model=model),
                    custom_message=error_msg,
                )
            raise CalculationError(error_msg)

        if output_tokens < 0:
            error_msg = f"Invalid output_tokens: {output_tokens}. Token count cannot be negative."
            if ENHANCED_ERRORS:
                raise create_error(
                    ErrorCode.INVALID_TOKENS,
                    context=ErrorContext(operation="calculating cost", model=model),
                    custom_message=error_msg,
                )
            raise CalculationError(error_msg)

        # Get pricing with caching
        pricing, is_default = _get_pricing(model)

        if is_default:
            # Warn about using default pricing for unknown model
            warning_msg = (
                f"Unknown model '{model}'. Using sonnet pricing as default. "
                f"Supported models: {', '.join(k for k in PRICING.keys() if not k.startswith('claude-'))}"
            )
            warnings.warn(warning_msg, UserWarning, stacklevel=2)
            if ENHANCED_ERRORS:
                log_warning(warning_msg)

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return round(input_cost + output_cost, 6)

    def log_usage(self, agent: str, model: str, input_tokens: int, output_tokens: int) -> CostEntry:
        """
        Log a usage entry.

        Args:
            agent: Agent name (SM, DEV, BA, etc.)
            model: Model name (opus, sonnet, haiku)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            The created CostEntry
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        entry = CostEntry(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

        self.session.entries.append(entry)
        self.current_agent = agent
        self.current_model = model

        if self.auto_save:
            self.save_session()

        return entry

    def set_current_agent(self, agent: str, model: str):
        """Set the current agent and model (for display purposes)."""
        self.current_agent = agent
        self.current_model = model

    def check_budget(self) -> tuple[bool, str, str]:
        """
        Check budget status.

        Returns:
            Tuple of (is_ok, status_level, message)
            - is_ok: True if can continue, False if should stop
            - status_level: "ok", "warning", "critical", or "stop"
            - message: Human-readable status message
        """
        if self.budget_limit_usd <= 0:
            return (True, "ok", "No budget limit set - tracking costs without enforcement")

        usage_pct = self.session.total_cost_usd / self.budget_limit_usd
        remaining = self.session.budget_remaining
        total_cost = self.session.total_cost_usd

        if usage_pct >= self.thresholds["stop"]:
            return (
                False,
                "stop",
                (
                    f" BUDGET EXCEEDED - ${total_cost:.2f} spent of ${self.budget_limit_usd:.2f} limit. "
                    f"Action required: Increase budget or stop operations. "
                    f"Story: {self.story_key}"
                ),
            )
        elif usage_pct >= self.thresholds["critical"]:
            return (
                True,
                "critical",
                (
                    f"CRITICAL: {usage_pct * 100:.0f}% of budget used (${total_cost:.2f}). "
                    f"Only ${remaining:.2f} remaining. Consider wrapping up soon."
                ),
            )
        elif usage_pct >= self.thresholds["warning"]:
            return (
                True,
                "warning",
                (
                    f"WARNING: {usage_pct * 100:.0f}% of budget used (${total_cost:.2f}). "
                    f"${remaining:.2f} remaining of ${self.budget_limit_usd:.2f} budget."
                ),
            )

        return (
            True,
            "ok",
            f"Budget OK: {usage_pct * 100:.0f}% used (${total_cost:.2f}/${self.budget_limit_usd:.2f})",
        )

    def get_session_summary(self) -> dict:
        """Get session summary as dictionary."""
        return self.session.to_dict()

    def save_session(self) -> bool:
        """
        Save session to disk.

        Returns:
            True if save was successful, False otherwise

        Note:
            Attempts to save session data to disk. On failure, prints an error
            message but does not raise an exception to avoid disrupting workflow.
        """
        self.session.end_time = datetime.now().isoformat()

        filename = f"{datetime.now().strftime('%Y-%m-%d')}_{self.session_id}.json"
        filepath = SESSIONS_DIR / filename

        try:
            # Ensure directory exists
            SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w") as f:
                json.dump(self.session.to_dict(), f, indent=2)
            return True

        except PermissionError:
            error_msg = (
                f"Permission denied when saving session to {filepath}. "
                f"Check directory permissions. Session data is preserved in memory."
            )
            if ENHANCED_ERRORS:
                log_warning(error_msg)
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            return False

        except OSError as e:
            error_msg = (
                f"Failed to save session to {filepath}: {e}. "
                f"Check disk space and file system. Session data is preserved in memory."
            )
            if ENHANCED_ERRORS:
                log_warning(error_msg)
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            return False

        except Exception as e:
            error_msg = (
                f"Unexpected error saving session: {type(e).__name__}: {e}. "
                f"Session data is preserved in memory."
            )
            if ENHANCED_ERRORS:
                log_warning(error_msg)
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            return False

    def end_session(self) -> dict:
        """End session and save final state."""
        self.session.end_time = datetime.now().isoformat()
        self.save_session()
        return self.session.to_dict()

    @staticmethod
    def load_session(session_file: Path) -> Optional[SessionCost]:
        """
        Load a session from file.

        Args:
            session_file: Path to the session JSON file

        Returns:
            SessionCost object if successful, None if file cannot be loaded

        Note:
            Returns None instead of raising to allow graceful handling of
            corrupted or missing files in bulk operations.
        """
        if not session_file.exists():
            warning_msg = f"Session file not found: {session_file}"
            if ENHANCED_ERRORS:
                log_warning(warning_msg)
            else:
                print(f"Warning: {warning_msg}", file=sys.stderr)
            return None

        try:
            with open(session_file) as f:
                data = json.load(f)

            # Validate required fields
            required_fields = ["session_id", "story_key", "start_time"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                warning_msg = (
                    f"Session file {session_file.name} is missing required fields: "
                    f"{', '.join(missing_fields)}. File may be corrupted."
                )
                if ENHANCED_ERRORS:
                    log_warning(warning_msg)
                else:
                    print(f"Warning: {warning_msg}", file=sys.stderr)
                return None

            entries = [CostEntry(**e) for e in data.get("entries", [])]

            return SessionCost(
                session_id=data["session_id"],
                story_key=data["story_key"],
                start_time=data["start_time"],
                end_time=data.get("end_time"),
                budget_limit_usd=data.get("budget_limit_usd", 15.00),
                entries=entries,
            )
        except json.JSONDecodeError as e:
            error_msg = (
                f"Failed to parse session file {session_file.name}: Invalid JSON at "
                f"line {e.lineno}, column {e.colno}. The file may be corrupted or incomplete."
            )
            if ENHANCED_ERRORS:
                log_warning(error_msg)
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            return None
        except TypeError as e:
            error_msg = (
                f"Failed to load session from {session_file.name}: Data structure mismatch. "
                f"Expected fields may be missing or have wrong types. Details: {e}"
            )
            if ENHANCED_ERRORS:
                log_warning(error_msg)
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            return None
        except Exception as e:
            error_msg = (
                f"Unexpected error loading session {session_file.name}: {type(e).__name__}: {e}"
            )
            if ENHANCED_ERRORS:
                log_warning(error_msg)
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            return None

    @staticmethod
    def get_historical_sessions(days: int = 30) -> list[SessionCost]:
        """Get historical sessions from the last N days."""
        sessions = []

        if not SESSIONS_DIR.exists():
            return sessions

        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for file in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
            if file.stat().st_mtime >= cutoff:
                session = CostTracker.load_session(file)
                if session:
                    sessions.append(session)

        return sessions

    @staticmethod
    def get_aggregate_stats(days: int = 30) -> dict:
        """Get aggregate statistics for the last N days."""
        sessions = CostTracker.get_historical_sessions(days)

        if not sessions:
            return {
                "total_sessions": 0,
                "total_cost_usd": 0,
                "total_tokens": 0,
                "by_agent": {},
                "by_model": {},
            }

        total_cost = sum(s.total_cost_usd for s in sessions)
        total_tokens = sum(s.total_tokens for s in sessions)

        # Aggregate by agent
        by_agent = {}
        for session in sessions:
            for agent, cost in session.get_cost_by_agent().items():
                if agent not in by_agent:
                    by_agent[agent] = {"cost": 0, "sessions": 0}
                by_agent[agent]["cost"] += cost
                by_agent[agent]["sessions"] += 1

        # Aggregate by model
        by_model = {}
        for session in sessions:
            for model, cost in session.get_cost_by_model().items():
                if model not in by_model:
                    by_model[model] = {"cost": 0}
                by_model[model]["cost"] += cost

        return {
            "total_sessions": len(sessions),
            "total_cost_usd": round(total_cost, 2),
            "total_tokens": total_tokens,
            "average_per_session": round(total_cost / len(sessions), 2) if sessions else 0,
            "by_agent": by_agent,
            "by_model": by_model,
        }

    @staticmethod
    def get_subscription_usage(billing_period_days: int = 30) -> dict:
        """
        Get subscription usage statistics for the billing period.

        Args:
            billing_period_days: Number of days in the billing period (default: 30)

        Returns:
            Dictionary with:
            - total_tokens: Total tokens used in the billing period
            - total_input_tokens: Input tokens used
            - total_output_tokens: Output tokens used
            - total_sessions: Number of sessions
            - total_cost_usd: Total cost in USD
        """
        sessions = CostTracker.get_historical_sessions(days=billing_period_days)

        total_input = sum(s.total_input_tokens for s in sessions)
        total_output = sum(s.total_output_tokens for s in sessions)

        return {
            "total_tokens": total_input + total_output,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_sessions": len(sessions),
            "total_cost_usd": round(sum(s.total_cost_usd for s in sessions), 2),
        }

    @staticmethod
    def get_subscription_percentage(token_limit: int, billing_period_days: int = 30) -> dict:
        """
        Calculate subscription usage percentage.

        Args:
            token_limit: Total tokens allowed in the subscription billing period
            billing_period_days: Number of days in the billing period

        Returns:
            Dictionary with:
            - percentage: Usage percentage (0-100+, can exceed 100 if over limit)
            - used_tokens: Total tokens used
            - remaining_tokens: Tokens remaining (can be negative if over)
            - limit_tokens: The configured limit
            - status: "ok", "warning", "critical", or "exceeded"
        """
        if token_limit <= 0:
            return {
                "percentage": 0,
                "used_tokens": 0,
                "remaining_tokens": 0,
                "limit_tokens": 0,
                "status": "not_configured",
            }

        usage = CostTracker.get_subscription_usage(billing_period_days)
        used_tokens = usage["total_tokens"]
        percentage = (used_tokens / token_limit) * 100
        remaining = token_limit - used_tokens

        # Determine status
        if percentage >= 100:
            status = "exceeded"
        elif percentage >= 90:
            status = "critical"
        elif percentage >= 75:
            status = "warning"
        else:
            status = "ok"

        return {
            "percentage": round(percentage, 2),
            "used_tokens": used_tokens,
            "remaining_tokens": remaining,
            "limit_tokens": token_limit,
            "status": status,
            "billing_period_days": billing_period_days,
            "total_sessions": usage["total_sessions"],
            "total_cost_usd": usage["total_cost_usd"],
        }

    @staticmethod
    def get_usage_projection(token_limit: int, billing_period_days: int = 30) -> dict:
        """
        Calculate usage projection and forecast when limit will be reached.

        Args:
            token_limit: Total tokens allowed in the subscription billing period
            billing_period_days: Number of days in the billing period

        Returns:
            Dictionary with projection data including days until limit reached.
        """
        if token_limit <= 0:
            return {
                "daily_average": 0,
                "days_until_limit": None,
                "projected_end_usage": 0,
                "on_track": True,
                "message": "Subscription tracking not configured",
            }

        sessions = CostTracker.get_historical_sessions(days=billing_period_days)
        if not sessions:
            return {
                "daily_average": 0,
                "days_until_limit": None,
                "projected_end_usage": 0,
                "on_track": True,
                "message": "No usage data available",
            }

        # Calculate tokens used and days elapsed
        total_tokens = sum(s.total_tokens for s in sessions)

        # Find the earliest session to calculate actual days of usage
        earliest = min(datetime.fromisoformat(s.start_time) for s in sessions)
        days_elapsed = max(1, (datetime.now() - earliest).days + 1)

        # Daily average based on actual usage period
        daily_average = total_tokens / days_elapsed

        # Project to end of billing period
        projected_end_usage = daily_average * billing_period_days

        # Calculate days until limit reached
        if daily_average > 0:
            remaining_tokens = token_limit - total_tokens
            days_until_limit = remaining_tokens / daily_average if remaining_tokens > 0 else 0
        else:
            days_until_limit = None

        # Determine if on track to stay within limit
        on_track = projected_end_usage <= token_limit

        # Generate message
        if days_until_limit is not None and days_until_limit <= 0:
            message = "Limit already exceeded"
        elif days_until_limit is not None and days_until_limit < 7:
            message = f"At current rate, limit reached in {days_until_limit:.0f} days"
        elif not on_track:
            overage_pct = ((projected_end_usage / token_limit) - 1) * 100
            message = f"Projected to exceed limit by {overage_pct:.0f}%"
        else:
            message = "On track to stay within limit"

        return {
            "daily_average": round(daily_average),
            "days_elapsed": days_elapsed,
            "days_until_limit": round(days_until_limit, 1)
            if days_until_limit is not None
            else None,
            "projected_end_usage": round(projected_end_usage),
            "on_track": on_track,
            "message": message,
            "total_tokens": total_tokens,
            "token_limit": token_limit,
        }

    @staticmethod
    def get_model_efficiency() -> dict:
        """
        Calculate model efficiency metrics (cost per output token).

        Returns:
            Dictionary with efficiency data per model.
        """
        sessions = CostTracker.get_historical_sessions(days=30)

        model_stats = {}
        for session in sessions:
            for entry in session.entries:
                model = entry.model
                if model not in model_stats:
                    model_stats[model] = {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_cost": 0,
                        "calls": 0,
                    }
                model_stats[model]["input_tokens"] += entry.input_tokens
                model_stats[model]["output_tokens"] += entry.output_tokens
                model_stats[model]["total_cost"] += entry.cost_usd
                model_stats[model]["calls"] += 1

        # Calculate efficiency metrics
        efficiency = {}
        for model, stats in model_stats.items():
            output_tokens = stats["output_tokens"]
            total_cost = stats["total_cost"]

            # Cost per 1K output tokens (the "value" metric)
            cost_per_1k_output = (total_cost / output_tokens * 1000) if output_tokens > 0 else 0

            # Output/Input ratio (how much output per input)
            output_input_ratio = (
                stats["output_tokens"] / stats["input_tokens"] if stats["input_tokens"] > 0 else 0
            )

            efficiency[model] = {
                "cost_per_1k_output": round(cost_per_1k_output, 4),
                "output_input_ratio": round(output_input_ratio, 2),
                "total_cost": round(total_cost, 4),
                "total_output_tokens": output_tokens,
                "total_input_tokens": stats["input_tokens"],
                "total_calls": stats["calls"],
                "avg_output_per_call": round(output_tokens / stats["calls"])
                if stats["calls"] > 0
                else 0,
            }

        # Sort by cost efficiency (lowest cost per output token first)
        sorted_efficiency = dict(
            sorted(efficiency.items(), key=lambda x: x[1]["cost_per_1k_output"])
        )

        return sorted_efficiency

    @staticmethod
    def get_daily_usage(days: int = 30) -> list[dict]:
        """
        Get daily token usage breakdown for trends.

        Args:
            days: Number of days to retrieve

        Returns:
            List of daily usage dictionaries sorted by date.
        """
        sessions = CostTracker.get_historical_sessions(days=days)

        daily = {}
        for session in sessions:
            date_str = session.start_time[:10]
            if date_str not in daily:
                daily[date_str] = {
                    "date": date_str,
                    "tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0,
                    "sessions": 0,
                }
            daily[date_str]["tokens"] += session.total_tokens
            daily[date_str]["input_tokens"] += session.total_input_tokens
            daily[date_str]["output_tokens"] += session.total_output_tokens
            daily[date_str]["cost_usd"] += session.total_cost_usd
            daily[date_str]["sessions"] += 1

        # Sort by date
        return sorted(daily.values(), key=lambda x: x["date"])

    @staticmethod
    def get_story_rankings(days: int = 30, limit: int = 10) -> list[dict]:
        """
        Get stories ranked by token consumption.

        Args:
            days: Number of days to look back
            limit: Maximum number of stories to return

        Returns:
            List of stories sorted by total tokens (descending).
        """
        sessions = CostTracker.get_historical_sessions(days=days)

        stories = {}
        for session in sessions:
            story = session.story_key
            if story not in stories:
                stories[story] = {
                    "story_key": story,
                    "total_tokens": 0,
                    "total_cost_usd": 0,
                    "sessions": 0,
                }
            stories[story]["total_tokens"] += session.total_tokens
            stories[story]["total_cost_usd"] += session.total_cost_usd
            stories[story]["sessions"] += 1

        # Sort by tokens and limit
        ranked = sorted(stories.values(), key=lambda x: -x["total_tokens"])
        return ranked[:limit]

    @staticmethod
    def get_api_rate_stats(days: int = 7) -> dict:
        """
        Get API call rate statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with call rate statistics.
        """
        sessions = CostTracker.get_historical_sessions(days=days)

        if not sessions:
            return {
                "total_calls": 0,
                "calls_per_day": 0,
                "calls_per_hour": 0,
                "peak_hour": None,
                "peak_day": None,
                "hourly_distribution": {},
                "daily_distribution": {},
            }

        # Collect all call timestamps
        hourly = {}  # hour -> count
        daily = {}  # date -> count
        total_calls = 0

        for session in sessions:
            for entry in session.entries:
                total_calls += 1
                try:
                    ts = datetime.fromisoformat(entry.timestamp)
                    hour = ts.hour
                    date_str = ts.strftime("%Y-%m-%d")

                    hourly[hour] = hourly.get(hour, 0) + 1
                    daily[date_str] = daily.get(date_str, 0) + 1
                except (ValueError, TypeError):
                    continue

        # Calculate averages
        actual_days = len(daily) if daily else 1
        calls_per_day = total_calls / actual_days
        calls_per_hour = total_calls / (actual_days * 24)

        # Find peaks
        peak_hour = max(hourly, key=hourly.get) if hourly else None
        peak_day = max(daily, key=daily.get) if daily else None

        return {
            "total_calls": total_calls,
            "calls_per_day": round(calls_per_day, 1),
            "calls_per_hour": round(calls_per_hour, 2),
            "peak_hour": peak_hour,
            "peak_hour_calls": hourly.get(peak_hour, 0) if peak_hour is not None else 0,
            "peak_day": peak_day,
            "peak_day_calls": daily.get(peak_day, 0) if peak_day else 0,
            "hourly_distribution": hourly,
            "daily_distribution": daily,
            "days_analyzed": actual_days,
        }

    @staticmethod
    def get_period_comparison(current_days: int = 30) -> dict:
        """
        Compare current period vs previous period.

        Args:
            current_days: Number of days in current period

        Returns:
            Dictionary with current and previous period stats and deltas.
        """
        # Current period
        current_sessions = CostTracker.get_historical_sessions(days=current_days)
        current_tokens = sum(s.total_tokens for s in current_sessions)
        current_cost = sum(s.total_cost_usd for s in current_sessions)

        # Previous period (load sessions from current_days to 2*current_days ago)
        all_sessions = CostTracker.get_historical_sessions(days=current_days * 2)
        cutoff = datetime.now().timestamp() - (current_days * 24 * 60 * 60)

        previous_sessions = [
            s for s in all_sessions if datetime.fromisoformat(s.start_time).timestamp() < cutoff
        ]
        previous_tokens = sum(s.total_tokens for s in previous_sessions)
        previous_cost = sum(s.total_cost_usd for s in previous_sessions)

        # Calculate deltas
        token_delta = current_tokens - previous_tokens
        cost_delta = current_cost - previous_cost

        token_delta_pct = (
            ((current_tokens / previous_tokens) - 1) * 100
            if previous_tokens > 0
            else (100 if current_tokens > 0 else 0)
        )
        cost_delta_pct = (
            ((current_cost / previous_cost) - 1) * 100
            if previous_cost > 0
            else (100 if current_cost > 0 else 0)
        )

        return {
            "current_period": {
                "days": current_days,
                "tokens": current_tokens,
                "cost_usd": round(current_cost, 2),
                "sessions": len(current_sessions),
            },
            "previous_period": {
                "days": current_days,
                "tokens": previous_tokens,
                "cost_usd": round(previous_cost, 2),
                "sessions": len(previous_sessions),
            },
            "delta": {
                "tokens": token_delta,
                "tokens_pct": round(token_delta_pct, 1),
                "cost_usd": round(cost_delta, 2),
                "cost_pct": round(cost_delta_pct, 1),
            },
        }


def parse_token_usage(output: str) -> Optional[tuple[int, int]]:
    """
    Parse token usage from Claude CLI output.

    Looks for patterns like:
    - "Token usage: 45000/200000"
    - "Tokens: 45000 in / 12000 out"
    - "Input: 30000, Output: 8000"
    - "input_tokens: X, output_tokens: Y"

    Returns:
        Tuple of (input_tokens, output_tokens) or None if not found

    Note:
        When only total tokens are available (Pattern 1), we cannot determine
        the exact split. Returns None in this case to avoid inaccurate estimates.
        The caller should handle this appropriately.
    """
    # Pattern 1: Explicit input/output tokens (most accurate)
    input_match = re.search(r"input[_\s]*tokens?[:\s]+(\d+)", output, re.IGNORECASE)
    output_match = re.search(r"output[_\s]*tokens?[:\s]+(\d+)", output, re.IGNORECASE)
    if input_match and output_match:
        return (int(input_match.group(1)), int(output_match.group(1)))

    # Pattern 2: "X in / Y out"
    match = re.search(r"(\d+)\s*in\s*/\s*(\d+)\s*out", output, re.IGNORECASE)
    if match:
        return (int(match.group(1)), int(match.group(2)))

    # Pattern 3: "Input: X, Output: Y" or "Input: X Output: Y"
    input_match = re.search(r"input[:\s]+(\d+)", output, re.IGNORECASE)
    output_match = re.search(r"output[:\s]+(\d+)", output, re.IGNORECASE)
    if input_match and output_match:
        return (int(input_match.group(1)), int(output_match.group(1)))

    # Pattern 4: "Token usage: X/Y" (total/limit) - cannot determine split
    # Return None rather than guessing, let caller decide how to handle
    match = re.search(r"Token usage:\s*(\d+)/(\d+)", output, re.IGNORECASE)
    if match:
        # Log warning that we couldn't determine the split
        total = int(match.group(1))
        warnings.warn(
            f"Found total token count ({total}) but cannot determine input/output split. "
            "Token usage will not be tracked for this call.",
            UserWarning,
            stacklevel=2,
        )
        return None

    return None


# Thread-safe module-level tracker storage
_tracker_local = threading.local()


def get_tracker() -> Optional[CostTracker]:
    """
    Get the current thread-local tracker.

    Returns:
        The CostTracker for the current thread, or None if not set.

    Note:
        Each thread has its own tracker instance to avoid race conditions
        in multi-threaded scenarios (e.g., swarm mode with parallel agents).
    """
    return getattr(_tracker_local, "tracker", None)


def set_tracker(tracker: CostTracker):
    """
    Set the current thread-local tracker.

    Args:
        tracker: The CostTracker instance to use for this thread.
    """
    _tracker_local.tracker = tracker


def start_tracking(story_key: str, budget_limit_usd: float = 15.00) -> CostTracker:
    """
    Start a new tracking session for the current thread.

    Args:
        story_key: Identifier for the story being tracked.
        budget_limit_usd: Maximum budget for this session.

    Returns:
        A new CostTracker instance, also set as the thread-local tracker.
    """
    tracker = CostTracker(story_key, budget_limit_usd)
    _tracker_local.tracker = tracker
    return tracker


if __name__ == "__main__":
    # Demo/test
    tracker = CostTracker(story_key="test-story", budget_limit_usd=10.00)

    # Simulate some usage
    tracker.log_usage("SM", "sonnet", 15000, 3000)
    tracker.log_usage("DEV", "opus", 50000, 15000)
    tracker.log_usage("SM", "sonnet", 10000, 2000)

    # Print summary
    import pprint

    pprint.pprint(tracker.get_session_summary())

    # Check budget
    ok, level, msg = tracker.check_budget()
    print(f"\nBudget status: {level} - {msg}")
