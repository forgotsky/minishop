#!/usr/bin/env python3
"""
Context Checkpoint Manager for Claude Code Sessions

Monitors Claude Code sessions for context window warnings and automatically:
1. Saves session state before context compaction
2. Creates checkpoint files with conversation history
3. Clears the session
4. Restarts with saved context

Usage:
    python3 tooling/scripts/context_checkpoint.py --session-id <id>
    python3 tooling/scripts/context_checkpoint.py --watch-logs
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from lib.colors import Colors
from lib.platform import IS_WINDOWS

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
CHECKPOINT_DIR = PROJECT_ROOT / "tooling" / ".automation" / "checkpoints"
LOGS_DIR = PROJECT_ROOT / "tooling" / ".automation" / "logs"
# Platform-specific CLI command
CLAUDE_CLI = "claude.cmd" if IS_WINDOWS else "claude"

# Context thresholds
CONTEXT_WARNING_THRESHOLD = 0.75  # 75% - Start warning
CONTEXT_CRITICAL_THRESHOLD = 0.85  # 85% - Auto-checkpoint
CONTEXT_EMERGENCY_THRESHOLD = 0.95  # 95% - Force checkpoint


class ContextCheckpointManager:
    """Manages context checkpointing for Claude Code sessions."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id
        self.checkpoint_dir = CHECKPOINT_DIR
        self.logs_dir = LOGS_DIR
        self.running = True
        self.last_checkpoint_time = None
        self.checkpoint_count = 0

        # Create directories
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Handle graceful shutdown (Windows-compatible)
        signal.signal(signal.SIGINT, self._signal_handler)
        # SIGTERM is not available on Windows
        if not IS_WINDOWS:
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n{Colors.YELLOW}Shutting down checkpoint manager...{Colors.END}")
        self.running = False
        sys.exit(0)

    def _log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp and color."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "INFO": Colors.CYAN,
            "SUCCESS": Colors.GREEN,
            "WARNING": Colors.YELLOW,
            "ERROR": Colors.RED,
            "CRITICAL": Colors.RED + Colors.BOLD,
        }
        color = color_map.get(level, Colors.END)
        print(f"{Colors.BOLD}[{timestamp}]{Colors.END} {color}{message}{Colors.END}")

    def extract_context_usage(self, output: str) -> Optional[float]:
        """Extract context usage percentage from Claude output.

        Looks for patterns like:
        - "Token usage: 75000/200000"
        - "Context: 75%"
        - " CONTEXT WARNING"
        """
        # Pattern 1: Token usage: X/Y
        match = re.search(r"Token usage:\s*(\d+)/(\d+)", output)
        if match:
            used = int(match.group(1))
            total = int(match.group(2))
            return used / total

        # Pattern 2: Context: X%
        match = re.search(r"Context:\s*(\d+)%", output)
        if match:
            return int(match.group(1)) / 100

        # Pattern 3: Warning messages
        if " CONTEXT WARNING" in output or "Approaching context limit" in output:
            return 0.90  # Assume 90% if warning present

        return None

    def get_current_conversation(self) -> dict:
        """Extract current conversation from Claude session.

        Uses Claude CLI to get session history if available.
        """
        try:
            # Try to export session history
            result = subprocess.run(
                [CLAUDE_CLI, "session", "export", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)

            self._log("Could not export session via CLI, using fallback", "WARNING")
            return self._fallback_conversation_extract()

        except subprocess.TimeoutExpired:
            self._log("Session export timed out", "ERROR")
            return self._fallback_conversation_extract()
        except Exception as e:
            self._log(f"Error extracting conversation: {e}", "ERROR")
            return self._fallback_conversation_extract()

    def _fallback_conversation_extract(self) -> dict:
        """Fallback method to extract conversation from logs."""
        # Check for recent log files
        log_files = sorted(
            self.logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        if not log_files:
            return {"messages": [], "metadata": {}}

        latest_log = log_files[0]
        try:
            with open(latest_log) as f:
                content = f.read()
                return {
                    "messages": [{"role": "system", "content": content}],
                    "metadata": {
                        "source": "log_file",
                        "file": str(latest_log),
                        "timestamp": datetime.now().isoformat(),
                    },
                }
        except Exception as e:
            self._log(f"Error reading log file: {e}", "ERROR")
            return {"messages": [], "metadata": {}}

    def create_checkpoint(self, context_level: float, reason: str = "auto") -> Path:
        """Create a checkpoint of the current session.

        Args:
            context_level: Current context usage (0.0 to 1.0)
            reason: Reason for checkpoint (auto, manual, emergency)

        Returns:
            Path to checkpoint file
        """
        self.checkpoint_count += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"checkpoint_{timestamp}_{self.checkpoint_count}"

        self._log(f" Creating checkpoint: {checkpoint_id}", "INFO")

        # Extract current conversation
        conversation = self.get_current_conversation()

        # Create checkpoint data
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "context_level": context_level,
            "reason": reason,
            "session_id": self.session_id,
            "conversation": conversation,
            "metadata": {
                "project_root": str(PROJECT_ROOT),
                "working_directory": os.getcwd(),
                "checkpoint_count": self.checkpoint_count,
            },
        }

        # Save checkpoint file
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f, indent=2)

        # Create summary file (human-readable)
        summary_file = self.checkpoint_dir / f"{checkpoint_id}_summary.md"
        self._create_checkpoint_summary(checkpoint_data, summary_file)

        self._log(f" Checkpoint saved: {checkpoint_file.name}", "SUCCESS")
        self.last_checkpoint_time = datetime.now()

        return checkpoint_file

    def _create_checkpoint_summary(self, checkpoint_data: dict, output_file: Path):
        """Create a human-readable summary of the checkpoint."""
        summary = f"""# Checkpoint Summary

**Checkpoint ID**: {checkpoint_data["checkpoint_id"]}
**Timestamp**: {checkpoint_data["timestamp"]}
**Context Level**: {checkpoint_data["context_level"] * 100:.1f}%
**Reason**: {checkpoint_data["reason"]}
**Session ID**: {checkpoint_data.get("session_id", "N/A")}

## Conversation Snapshot

Messages: {len(checkpoint_data["conversation"].get("messages", []))}
Source: {checkpoint_data["conversation"].get("metadata", {}).get("source", "unknown")}

## Metadata

- Project Root: `{checkpoint_data["metadata"]["project_root"]}`
- Working Directory: `{checkpoint_data["metadata"]["working_directory"]}`
- Checkpoint Count: {checkpoint_data["metadata"]["checkpoint_count"]}

## Recovery Instructions

To resume from this checkpoint:

```bash
# Option 1: Use the checkpoint file
python3 tooling/scripts/context_checkpoint.py --resume {checkpoint_data["checkpoint_id"]}

# Option 2: Manual resume
# The full conversation is in: {checkpoint_data["checkpoint_id"]}.json
```

## Next Steps

After checkpoint, the session should be cleared and restarted with:
1. Current working context
2. Active task description
3. Recent file changes
4. Todo list state
"""

        with open(output_file, "w") as f:
            f.write(summary)

    def clear_session(self):
        """Clear the current Claude session."""
        self._log(" Clearing session...", "INFO")
        try:
            # Try to clear via CLI
            result = subprocess.run(
                [CLAUDE_CLI, "clear"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                self._log(" Session cleared successfully", "SUCCESS")
                return True
            else:
                self._log(f"Warning: Clear command returned {result.returncode}", "WARNING")
                return False

        except Exception as e:
            self._log(f"Error clearing session: {e}", "ERROR")
            return False

    def resume_from_checkpoint(self, checkpoint_id: str) -> bool:
        """Resume a session from a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to resume from

        Returns:
            True if successful
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            self._log(f"Checkpoint not found: {checkpoint_id}", "ERROR")
            return False

        self._log(f" Loading checkpoint: {checkpoint_id}", "INFO")

        try:
            with open(checkpoint_file) as f:
                checkpoint_data = json.load(f)

            # Create resume prompt
            resume_prompt = self._create_resume_prompt(checkpoint_data)

            # Start new session with resume prompt
            self._log("Starting new session with checkpoint context...", "INFO")
            print("\n" + "=" * 80)
            print("RESUME PROMPT (paste this into Claude Code):")
            print("=" * 80 + "\n")
            print(resume_prompt)
            print("\n" + "=" * 80 + "\n")

            return True

        except Exception as e:
            self._log(f"Error resuming from checkpoint: {e}", "ERROR")
            return False

    def _create_resume_prompt(self, checkpoint_data: dict) -> str:
        """Create a prompt to resume from checkpoint."""
        messages = checkpoint_data["conversation"].get("messages", [])

        # Extract key information
        task_context = "Continue previous work"
        recent_files = []

        # Try to extract context from messages
        for msg in messages[-5:]:  # Last 5 messages
            content = msg.get("content", "")
            if "File:" in content or "file_path" in content:
                # Extract file references
                file_matches = re.findall(r'(?:File:|file_path["\']:\s*["\'])([^\'"]+)', content)
                recent_files.extend(file_matches)

        resume_prompt = f"""# Session Resume from Checkpoint

**Checkpoint ID**: {checkpoint_data["checkpoint_id"]}
**Original Timestamp**: {checkpoint_data["timestamp"]}
**Context Level at Checkpoint**: {checkpoint_data["context_level"] * 100:.1f}%

---

## Context Summary

You were working on: {task_context}

### Recent Files
{chr(10).join(f"- `{f}`" for f in recent_files[:10]) if recent_files else "No recent files tracked"}

### Session State
- Checkpoint Count: {checkpoint_data["metadata"]["checkpoint_count"]}
- Working Directory: `{checkpoint_data["metadata"]["working_directory"]}`

---

## Instructions

Please continue from where we left off. The checkpoint was created because the context window was reaching capacity.

**What to do**:
1. Acknowledge that you've resumed from checkpoint {checkpoint_data["checkpoint_id"]}
2. Ask me what specific task I'd like to continue with
3. Use the TodoWrite tool to create a fresh todo list for current work

**Context available**:
- Full checkpoint data is saved in: `tooling/.automation/checkpoints/{checkpoint_data["checkpoint_id"]}.json`
- You can read this file if you need to reference previous conversation details

Ready to continue!
"""

        return resume_prompt

    def watch_log_file(self, log_file: Path):
        """Watch a log file for context warnings and auto-checkpoint.

        Args:
            log_file: Path to log file to monitor
        """
        self._log(f" Watching log file: {log_file}", "INFO")

        try:
            with open(log_file) as f:
                # Seek to end of file
                f.seek(0, 2)

                while self.running:
                    line = f.readline()

                    if not line:
                        time.sleep(0.5)
                        continue

                    # Check for context warnings
                    context_level = self.extract_context_usage(line)

                    if context_level:
                        self._handle_context_level(context_level)

        except FileNotFoundError:
            self._log(f"Log file not found: {log_file}", "ERROR")
        except KeyboardInterrupt:
            self._log("Stopping log watch...", "INFO")
        except Exception as e:
            self._log(f"Error watching log: {e}", "ERROR")

    def _handle_context_level(self, context_level: float):
        """Handle different context levels with appropriate actions."""
        percentage = context_level * 100

        if context_level >= CONTEXT_EMERGENCY_THRESHOLD:
            # EMERGENCY: Force checkpoint immediately
            self._log(f" EMERGENCY: Context at {percentage:.1f}% - Force checkpoint!", "CRITICAL")
            checkpoint_file = self.create_checkpoint(context_level, reason="emergency")
            self._log(
                "  MANUAL ACTION REQUIRED: Clear session and resume from checkpoint", "CRITICAL"
            )
            self._log(
                f"Run: python3 tooling/scripts/context_checkpoint.py --resume {checkpoint_file.stem}",
                "INFO",
            )

        elif context_level >= CONTEXT_CRITICAL_THRESHOLD:
            # CRITICAL: Auto-checkpoint
            self._log(f"  CRITICAL: Context at {percentage:.1f}% - Auto checkpoint", "WARNING")
            checkpoint_file = self.create_checkpoint(context_level, reason="critical")
            self._log(" Consider clearing session soon", "WARNING")

        elif context_level >= CONTEXT_WARNING_THRESHOLD:
            # WARNING: Just notify
            self._log(f" WARNING: Context at {percentage:.1f}%", "WARNING")

    def interactive_monitor(self):
        """Run interactive monitoring mode."""
        self._log("Starting interactive context monitor", "INFO")
        self._log(
            f"Thresholds: Warning={CONTEXT_WARNING_THRESHOLD * 100}%, Critical={CONTEXT_CRITICAL_THRESHOLD * 100}%, Emergency={CONTEXT_EMERGENCY_THRESHOLD * 100}%",
            "INFO",
        )

        print(f"\n{Colors.BOLD}Commands:{Colors.END}")
        print("  - Type 'checkpoint' to manually create checkpoint")
        print("  - Type 'resume <id>' to resume from checkpoint")
        print("  - Type 'list' to list checkpoints")
        print("  - Type 'status' to check current state")
        print("  - Type 'quit' to exit")
        print()

        while self.running:
            try:
                cmd = input(f"{Colors.CYAN}> {Colors.END}").strip().lower()

                if cmd == "checkpoint":
                    self.create_checkpoint(0.0, reason="manual")

                elif cmd.startswith("resume "):
                    checkpoint_id = cmd.split(" ", 1)[1]
                    self.resume_from_checkpoint(checkpoint_id)

                elif cmd == "list":
                    self._list_checkpoints()

                elif cmd == "status":
                    self._show_status()

                elif cmd in ("quit", "exit", "q"):
                    break

                else:
                    print(f"{Colors.YELLOW}Unknown command: {cmd}{Colors.END}")

            except KeyboardInterrupt:
                print()
                break
            except Exception as e:
                self._log(f"Error: {e}", "ERROR")

    def _list_checkpoints(self):
        """List all available checkpoints."""
        checkpoints = sorted(self.checkpoint_dir.glob("checkpoint_*.json"))

        if not checkpoints:
            self._log("No checkpoints found", "INFO")
            return

        print(f"\n{Colors.BOLD}Available Checkpoints:{Colors.END}")
        for cp_file in checkpoints:
            with open(cp_file) as f:
                data = json.load(f)
                timestamp = data["timestamp"]
                context = data["context_level"] * 100
                reason = data["reason"]
                print(f"  • {cp_file.stem} - {timestamp} - {context:.1f}% ({reason})")
        print()

    def _show_status(self):
        """Show current manager status."""
        print(f"\n{Colors.BOLD}Status:{Colors.END}")
        print(f"  Session ID: {self.session_id or 'N/A'}")
        print(f"  Checkpoint Count: {self.checkpoint_count}")
        print(f"  Last Checkpoint: {self.last_checkpoint_time or 'Never'}")
        print(f"  Checkpoint Dir: {self.checkpoint_dir}")
        print(f"  Running: {self.running}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Context Checkpoint Manager for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive monitoring mode
  python3 tooling/scripts/context_checkpoint.py

  # Watch a specific log file
  python3 tooling/scripts/context_checkpoint.py --watch-log tooling/.automation/logs/story.log

  # Resume from checkpoint
  python3 tooling/scripts/context_checkpoint.py --resume checkpoint_20251220_143052_1

  # Manual checkpoint
  python3 tooling/scripts/context_checkpoint.py --checkpoint
        """,
    )

    parser.add_argument("--session-id", help="Claude session ID to monitor")
    parser.add_argument("--watch-log", help="Log file to watch for context warnings")
    parser.add_argument("--resume", help="Resume from checkpoint ID")
    parser.add_argument("--checkpoint", action="store_true", help="Create manual checkpoint")
    parser.add_argument("--list", action="store_true", help="List available checkpoints")

    args = parser.parse_args()

    manager = ContextCheckpointManager(session_id=args.session_id)

    if args.list:
        manager._list_checkpoints()
    elif args.checkpoint:
        manager.create_checkpoint(0.0, reason="manual")
    elif args.resume:
        manager.resume_from_checkpoint(args.resume)
    elif args.watch_log:
        manager.watch_log_file(Path(args.watch_log))
    else:
        # Interactive mode
        manager.interactive_monitor()


if __name__ == "__main__":
    main()
