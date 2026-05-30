#!/usr/bin/env python3
"""
Session Tracker - Tracks costs for ALL Claude Code sessions.

Called by hooks to track token usage across the entire session lifecycle.

Usage:
    python session_tracker.py start [--session-id ID]
    python session_tracker.py log --input TOKENS --output TOKENS [--model MODEL]
    python session_tracker.py end
    python session_tracker.py status
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

# Project paths
PROJECT_DIR = Path(__file__).parent.parent.parent
COSTS_DIR = PROJECT_DIR / "tooling" / ".automation" / "costs"
SESSIONS_DIR = COSTS_DIR / "sessions"
ACTIVE_SESSION_FILE = COSTS_DIR / ".active_session.json"

# Pricing per 1M tokens (USD) - December 2025
PRICING = {
    "claude-opus-4-5-20251101": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "opus": {"input": 15.00, "output": 75.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.80, "output": 4.00},
}


def get_pricing(model: str) -> dict:
    """Get pricing for a model."""
    model_lower = model.lower()

    # Direct match
    if model_lower in PRICING:
        return PRICING[model_lower]

    # Partial match
    for key, price in PRICING.items():
        if key in model_lower or model_lower in key:
            return price

    # Check for model family
    if "opus" in model_lower:
        return PRICING["opus"]
    elif "sonnet" in model_lower:
        return PRICING["sonnet"]
    elif "haiku" in model_lower:
        return PRICING["haiku"]

    # Default to sonnet pricing
    return PRICING["sonnet"]


def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate cost in USD."""
    pricing = get_pricing(model)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


def ensure_dirs():
    """Ensure required directories exist."""
    COSTS_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def start_session(session_id: str = None, model: str = None) -> dict:
    """Start a new tracking session."""
    ensure_dirs()

    now = datetime.now()
    if not session_id:
        session_id = now.strftime("%Y%m%d_%H%M%S")

    session = {
        "session_id": session_id,
        "start_time": now.isoformat(),
        "end_time": None,
        "model": model or "unknown",
        "story_key": None,
        "entries": [],
        "totals": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        },
    }

    # Save active session
    with open(ACTIVE_SESSION_FILE, "w") as f:
        json.dump(session, f, indent=2)

    return session


def get_active_session() -> dict | None:
    """Get the currently active session."""
    if not ACTIVE_SESSION_FILE.exists():
        return None

    try:
        with open(ACTIVE_SESSION_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def log_usage(input_tokens: int, output_tokens: int, model: str = None) -> dict | None:
    """Log token usage to the active session."""
    session = get_active_session()

    if not session:
        # Auto-start session if none exists
        session = start_session(model=model)

    # Update model if provided
    if model and session.get("model") == "unknown":
        session["model"] = model

    # Use session model for pricing
    use_model = model or session.get("model", "sonnet")
    cost = calculate_cost(input_tokens, output_tokens, use_model)

    # Create entry
    entry = {
        "timestamp": datetime.now().isoformat(),
        "model": use_model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }

    session["entries"].append(entry)

    # Update totals
    session["totals"]["input_tokens"] += input_tokens
    session["totals"]["output_tokens"] += output_tokens
    session["totals"]["total_tokens"] += input_tokens + output_tokens
    session["totals"]["cost_usd"] += cost

    # Save updated session
    with open(ACTIVE_SESSION_FILE, "w") as f:
        json.dump(session, f, indent=2)

    return session


def end_session() -> dict | None:
    """End the current session and save to sessions directory."""
    session = get_active_session()

    if not session:
        return None

    # Set end time
    session["end_time"] = datetime.now().isoformat()

    # Only save if there was activity
    if session["totals"]["total_tokens"] > 0:
        # Generate filename
        start_time = datetime.fromisoformat(session["start_time"])
        filename = f"{start_time.strftime('%Y-%m-%d')}_{session['session_id']}.json"
        session_file = SESSIONS_DIR / filename

        # Save to sessions directory
        with open(session_file, "w") as f:
            json.dump(session, f, indent=2)

    # Remove active session file
    if ACTIVE_SESSION_FILE.exists():
        ACTIVE_SESSION_FILE.unlink()

    return session


def get_status() -> dict:
    """Get current session status."""
    session = get_active_session()

    if not session:
        return {"active": False, "message": "No active session"}

    totals = session.get("totals", {})
    return {
        "active": True,
        "session_id": session.get("session_id"),
        "model": session.get("model"),
        "input_tokens": totals.get("input_tokens", 0),
        "output_tokens": totals.get("output_tokens", 0),
        "total_tokens": totals.get("total_tokens", 0),
        "cost_usd": totals.get("cost_usd", 0.0),
        "entries_count": len(session.get("entries", [])),
    }


def main():
    parser = argparse.ArgumentParser(description="Session cost tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a new session")
    start_parser.add_argument("--session-id", help="Custom session ID")
    start_parser.add_argument("--model", help="Model name")

    # Log command
    log_parser = subparsers.add_parser("log", help="Log token usage")
    log_parser.add_argument("--input", type=int, required=True, help="Input tokens")
    log_parser.add_argument("--output", type=int, required=True, help="Output tokens")
    log_parser.add_argument("--model", help="Model name")

    # End command
    subparsers.add_parser("end", help="End current session")

    # Status command
    subparsers.add_parser("status", help="Get session status")

    args = parser.parse_args()

    if args.command == "start":
        session = start_session(args.session_id, args.model)
        print(json.dumps({"status": "started", "session_id": session["session_id"]}))

    elif args.command == "log":
        model = getattr(args, "model", None)
        session = log_usage(args.input, args.output, model)
        if session:
            print(
                json.dumps(
                    {
                        "status": "logged",
                        "total_tokens": session["totals"]["total_tokens"],
                        "cost_usd": round(session["totals"]["cost_usd"], 4),
                    }
                )
            )
        else:
            print(json.dumps({"status": "error", "message": "No active session"}))

    elif args.command == "end":
        session = end_session()
        if session:
            print(
                json.dumps(
                    {
                        "status": "ended",
                        "total_tokens": session["totals"]["total_tokens"],
                        "cost_usd": round(session["totals"]["cost_usd"], 4),
                        "saved": session["totals"]["total_tokens"] > 0,
                    }
                )
            )
        else:
            print(json.dumps({"status": "no_session"}))

    elif args.command == "status":
        status = get_status()
        print(json.dumps(status))


if __name__ == "__main__":
    main()
