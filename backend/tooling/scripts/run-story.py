#!/usr/bin/env python3
"""
Cross-Platform Story Runner with Cost Tracking

Automatically detects the operating system and runs the appropriate script.
Works on Windows, macOS, and Linux. Includes real-time cost monitoring.

Usage:
    python run-story.py <story-key> [options]

Options:
    --develop, -d     Run development phase only
    --review, -r      Run review phase only
    --context, -c     Run context phase only
    --no-commit       Disable auto-commit
    --with-pr         Create PR after commit
    --model MODEL     Model to use (sonnet, opus, haiku)
    --budget AMOUNT   Budget limit in USD (default: 15.00)
    --show-costs      Show cost dashboard after run
    --native          Run natively with Python (enables cost tracking)

Examples:
    python run-story.py 3-5
    python run-story.py 3-5 --develop
    python run-story.py 3-5 --model opus --budget 20.00
    python run-story.py 3-5 --native --show-costs
"""

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Add lib directory for imports
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from colors import Colors

from lib.platform import IS_WINDOWS, get_platform

# Try to import context monitor
try:
    from context_monitor import ContextMonitor, StatusLine

    HAS_CONTEXT_MONITOR = True
except ImportError:
    HAS_CONTEXT_MONITOR = False

# Try to import validation loop
try:
    from validation_loop import (
        INTER_PHASE_GATES,
        POST_COMPLETION_GATES,
        PREFLIGHT_GATES,
        LoopContext,
        ValidationLoop,
        get_phase_gates,
    )

    HAS_VALIDATION = True
except ImportError:
    HAS_VALIDATION = False


def run_windows(args):
    """Run PowerShell script on Windows."""
    script = SCRIPT_DIR / "run-story.ps1"

    if not script.exists():
        print(f"Error: PowerShell script not found: {script}")
        return 1

    # Convert args to PowerShell format
    ps_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            # Convert --develop to -Develop
            param_name = arg[2:].title()
            ps_args.append(f"-{param_name}")
        elif arg.startswith("-") and len(arg) == 2:
            ps_args.append(arg)
        else:
            ps_args.append(arg)
        i += 1

    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)] + ps_args
    return subprocess.call(cmd)


def run_unix(args):
    """Run shell script on macOS/Linux."""
    script = SCRIPT_DIR / "run-story.sh"

    if not script.exists():
        print(f"Error: Shell script not found: {script}")
        return 1

    # Ensure script is executable
    os.chmod(script, 0o755)

    cmd = [str(script)] + args
    return subprocess.call(cmd)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run story automation with cost tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run-story.py 3-5                     # Full pipeline
  python run-story.py 3-5 --develop           # Development only
  python run-story.py 3-5 --native            # Native Python with cost tracking
  python run-story.py 3-5 --budget 20.00      # Custom budget
        """,
    )

    parser.add_argument("story_key", help="Story key (e.g., 3-5)")
    parser.add_argument("--develop", "-d", action="store_true", help="Development phase only")
    parser.add_argument("--review", "-r", action="store_true", help="Review phase only")
    parser.add_argument("--context", "-c", action="store_true", help="Context phase only")
    parser.add_argument("--no-commit", action="store_true", help="Disable auto-commit")
    parser.add_argument("--with-pr", action="store_true", help="Create PR after commit")
    parser.add_argument(
        "--model", choices=["sonnet", "opus", "haiku"], default="sonnet", help="Model to use"
    )
    parser.add_argument("--budget", type=float, default=15.00, help="Budget limit in USD")
    parser.add_argument("--show-costs", action="store_true", help="Show cost dashboard after run")
    parser.add_argument(
        "--native", action="store_true", help="Run natively with Python (enables cost tracking)"
    )
    parser.add_argument("--no-monitor", action="store_true", help="Disable live monitoring display")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Enable validation loop (pre-flight, inter-phase, post-completion)",
    )
    parser.add_argument("--no-validate", action="store_true", help="Disable validation loop")
    parser.add_argument(
        "--validation-tier",
        type=int,
        choices=[1, 2, 3],
        help="Run specific validation tier only (1=preflight, 2=inter-phase, 3=post-completion)",
    )

    return parser.parse_args()


class NativeRunner:
    """Native Python runner with cost tracking, context monitoring, and validation."""

    def __init__(self, args):
        self.args = args
        self.tracker = None
        self.display = None
        self.context_monitor = None
        self.status_line = None
        self.monitor_thread = None
        self.running = False
        self.validation_loop = None
        self.validation_context = None

        # Import cost modules
        try:
            from cost_display import CompactCostDisplay, CostDisplay
            from cost_tracker import CostTracker

            self.CostTracker = CostTracker
            self.CostDisplay = CostDisplay
            self.CompactCostDisplay = CompactCostDisplay
            self.cost_available = True
        except ImportError as e:
            print(f"Warning: Cost tracking not available: {e}")
            self.cost_available = False

        # Initialize context monitor if available
        if HAS_CONTEXT_MONITOR:
            self.context_monitor = ContextMonitor(
                story_key=args.story_key,
                model=args.model,
                on_threshold=self._on_context_threshold,
            )
        else:
            self.context_monitor = None

        # Initialize validation if available and enabled
        self.validation_enabled = (
            HAS_VALIDATION and (args.validate or not args.no_validate) and not args.no_validate
        )
        if self.validation_enabled:
            self._init_validation()

    def _on_context_threshold(self, level, state):
        """Handle context threshold crossing."""
        from context_monitor import ContextLevel

        if level == ContextLevel.EMERGENCY:
            print(f"\n{Colors.BG_RED}{Colors.WHITE} CONTEXT EMERGENCY {Colors.RESET}")
            print(f"Context at {state.context_usage_percent:.0f}% - compaction imminent!")
            print("Recommendation: Save checkpoint NOW and clear session.")
            self._trigger_auto_checkpoint("emergency")
        elif level == ContextLevel.CRITICAL:
            print(
                f"\n{Colors.BOLD_RED}[CRITICAL]{Colors.RESET} Context at {state.context_usage_percent:.0f}%"
            )
            print("Recommendation: Consider wrapping up and checkpointing soon.")
            self._trigger_auto_checkpoint("critical")
        elif level == ContextLevel.WARNING:
            print(
                f"\n{Colors.YELLOW}[WARNING]{Colors.RESET} Context at {state.context_usage_percent:.0f}%"
            )
            print(f"~{state.exchanges_remaining} exchanges remaining before compaction.")

    def _trigger_auto_checkpoint(self, reason: str):
        """Trigger automatic checkpoint at critical thresholds."""
        try:
            # Import checkpoint manager
            sys.path.insert(0, str(SCRIPT_DIR))
            from context_checkpoint import ContextCheckpointManager

            manager = ContextCheckpointManager()
            context_level = (
                self.context_monitor.state.context_usage_ratio if self.context_monitor else 0.0
            )
            checkpoint_file = manager.create_checkpoint(context_level, reason=reason)
            print(f"[CHECKPOINT] Saved to: {checkpoint_file.name}")

            if self.context_monitor:
                self.context_monitor.record_checkpoint()
        except Exception as e:
            print(f"{Colors.YELLOW}[WARN] Could not create auto-checkpoint: {e}{Colors.RESET}")

    def _init_validation(self):
        """Initialize validation loop."""
        all_gates = PREFLIGHT_GATES + INTER_PHASE_GATES + POST_COMPLETION_GATES
        self.validation_loop = ValidationLoop(
            gates=all_gates,
            config={"auto_fix_enabled": True},
            story_key=self.args.story_key,
        )
        self.validation_context = LoopContext(
            story_key=self.args.story_key,
            max_iterations=3,
        )

    def run_preflight_validation(self) -> bool:
        """Run pre-flight validation. Returns True if passed."""
        if not self.validation_enabled or not self.validation_loop:
            return True

        print("[VALIDATION] Running pre-flight checks...")
        self.validation_context.phase = "preflight"
        report = self.validation_loop.run_preflight(self.validation_context)

        if report.passed:
            print(f"[PASS] Pre-flight validation passed ({len(report.gate_results)} gates)")
            return True
        else:
            print(f"{Colors.RED}[FAIL] Pre-flight validation failed{Colors.RESET}")
            for failure in report.failures:
                print(f"  - {failure.gate_name}: {failure.message}")
            return False

    def run_phase_validation(self, from_phase: str, to_phase: str) -> bool:
        """Run inter-phase validation. Returns True if passed."""
        if not self.validation_enabled or not self.validation_loop:
            return True

        phase_gates = get_phase_gates(from_phase, to_phase)
        if not phase_gates:
            return True  # No gates for this transition

        print(f"[VALIDATION] Checking {from_phase} -> {to_phase} transition...")
        self.validation_context.phase = f"{from_phase}_to_{to_phase}"
        self.validation_context.from_agent = from_phase
        self.validation_context.to_agent = to_phase

        # Create a temporary loop with just the phase gates
        phase_loop = ValidationLoop(
            gates=phase_gates,
            config={"auto_fix_enabled": True},
            story_key=self.args.story_key,
        )
        report = phase_loop.run_gates(self.validation_context, tier=2)

        if report.passed:
            print("[PASS] Phase transition validated")
            return True
        else:
            print(f"{Colors.YELLOW}[WARN] Phase validation issues:{Colors.RESET}")
            for failure in report.failures:
                print(f"  - {failure.gate_name}: {failure.message}")
            # Don't block on inter-phase, just warn
            return True

    def run_post_validation(self) -> bool:
        """Run post-completion validation. Returns True if passed."""
        if not self.validation_enabled or not self.validation_loop:
            return True

        print("\n[VALIDATION] Running post-completion checks...")
        self.validation_context.phase = "post-completion"
        report = self.validation_loop.run_post_completion(self.validation_context)

        if report.passed:
            print("[PASS] Post-completion validation passed")
            if report.warnings:
                print(f"{Colors.YELLOW}[WARN] {len(report.warnings)} warning(s):{Colors.RESET}")
                for warn in report.warnings:
                    print(f"  - {warn.gate_name}: {warn.message}")
            return True
        else:
            print(f"{Colors.YELLOW}[WARN] Post-completion validation issues:{Colors.RESET}")
            for failure in report.failures:
                print(f"  - {failure.gate_name}: {failure.message}")
            # Warn but don't fail the overall run
            return True

    def start_tracking(self):
        """Initialize cost tracking and status line."""
        if not self.cost_available:
            return

        self.tracker = self.CostTracker(
            story_key=self.args.story_key, budget_limit_usd=self.args.budget
        )
        self.display = self.CompactCostDisplay(self.tracker)

        # Create unified status line with context + cost
        if HAS_CONTEXT_MONITOR and self.context_monitor:
            self.status_line = StatusLine(
                context_monitor=self.context_monitor,
                cost_tracker=self.tracker,
            )

    def start_monitor(self):
        """Start the monitoring display thread."""
        if not self.cost_available or self.args.no_monitor:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def _monitor_loop(self):
        """Monitor loop for live display updates."""
        while self.running:
            # Use unified status line if available, otherwise fall back to cost display
            if self.status_line:
                self.status_line.print(newline=False)
            elif self.tracker:
                self.display.print()
            time.sleep(2)

    def stop_monitor(self):
        """Stop the monitoring display."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

    def run_claude(self, agent: str, model: str, prompt: str, timeout: int = 300) -> tuple:
        """Run Claude CLI and capture output."""
        cli = "claude.cmd" if IS_WINDOWS else "claude"

        cmd = [cli, "--print", "--model", model, "-p", prompt]

        # Set current agent for display
        if self.tracker:
            self.tracker.set_current_agent(agent, model)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(SCRIPT_DIR.parent.parent),  # Project root
            )

            output = result.stdout + result.stderr

            # Parse token usage from output (if available)
            tokens = self._parse_tokens(output)
            if tokens:
                # Update cost tracker
                if self.tracker:
                    self.tracker.log_usage(agent, model, tokens[0], tokens[1])
                # Update context monitor
                if self.context_monitor:
                    self.context_monitor.update_from_tokens(tokens[0], tokens[1])

            return (result.returncode == 0, output)

        except subprocess.TimeoutExpired:
            return (False, "Timeout expired")
        except Exception as e:
            return (False, str(e))

    def _parse_tokens(self, output: str) -> tuple:
        """Parse token usage from Claude output."""
        import re

        # Try to find token patterns
        # Pattern: "Token usage: X/Y"
        match = re.search(r"Token usage:\s*(\d+)/(\d+)", output)
        if match:
            total = int(match.group(1))
            return (int(total * 0.8), int(total * 0.2))

        # Pattern: "X in / Y out"
        match = re.search(r"(\d+)\s*in\s*/\s*(\d+)\s*out", output, re.IGNORECASE)
        if match:
            return (int(match.group(1)), int(match.group(2)))

        # Default estimate based on output length
        output_tokens = len(output.split()) * 1.3
        input_tokens = output_tokens * 0.3
        return (int(input_tokens), int(output_tokens))

    def check_budget(self) -> bool:
        """Check if budget is OK to continue."""
        if not self.tracker:
            return True

        ok, level, msg = self.tracker.check_budget()

        if level == "critical":
            print(f"\n{Colors.RED}{msg}{Colors.RESET}")
        elif level == "warning":
            print(f"\n{Colors.YELLOW}{msg}{Colors.RESET}")

        return ok

    def run(self) -> int:
        """Run the story automation."""
        # Print header with status line
        print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}")
        print(f"{Colors.BOLD}DEVFLOW STORY RUNNER{Colors.RESET}")
        print(
            f"Story: {self.args.story_key} | Model: {self.args.model} | Budget: ${self.args.budget:.2f}"
        )
        if self.validation_enabled:
            print("Validation: Enabled")
        if self.context_monitor:
            print(
                f"Context Monitor: Active (window: {self.context_monitor.state.context_window:,} tokens)"
            )
        print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}")
        print()

        # Run pre-flight validation
        if not self.run_preflight_validation():
            print(f"\n{Colors.RED}[BLOCKED] Pre-flight validation failed. Aborting.{Colors.RESET}")
            return 1

        self.start_tracking()
        self.start_monitor()

        # Print initial status line
        if self.status_line:
            self.status_line.print()

        try:
            # Determine which phases to run
            run_context = self.args.context or (not self.args.develop and not self.args.review)
            run_develop = self.args.develop or (not self.args.context and not self.args.review)
            run_review = self.args.review or (not self.args.context and not self.args.develop)

            # Calculate total phases
            total_phases = sum([run_context, run_develop, run_review])
            phases_completed = 0

            # Set initial activity state
            if self.context_monitor:
                self.context_monitor.set_current_activity(
                    total_phases=total_phases, phases_completed=0
                )

            # Context phase
            if run_context:
                print("\n[1/3] Context Phase...")
                if self.context_monitor:
                    self.context_monitor.set_current_activity(
                        agent="SM",
                        phase="Context Analysis",
                        task="Preparing development context",
                        phases_completed=phases_completed,
                    )
                success, output = self.run_claude(
                    "SM",
                    "sonnet",
                    f"Analyze story {self.args.story_key} and prepare context for development",
                )
                if not success:
                    print(f"Context phase failed: {output[:200]}")
                    return 1

                phases_completed += 1
                if self.context_monitor:
                    self.context_monitor.set_current_activity(phases_completed=phases_completed)

                if not self.check_budget():
                    return 1

                # Validate context -> dev transition
                if run_develop:
                    self.run_phase_validation("CONTEXT", "DEV")

            # Development phase
            if run_develop:
                print("\n[2/3] Development Phase...")
                if self.context_monitor:
                    self.context_monitor.set_current_activity(
                        agent="DEV",
                        phase="Development",
                        task="Implementing story",
                        phases_completed=phases_completed,
                    )
                success, output = self.run_claude(
                    "DEV",
                    self.args.model,
                    f"Implement story {self.args.story_key} following the context and specifications",
                )
                if not success:
                    print(f"Development phase failed: {output[:200]}")
                    return 1

                phases_completed += 1
                if self.context_monitor:
                    self.context_monitor.set_current_activity(phases_completed=phases_completed)

                if not self.check_budget():
                    return 1

                # Validate dev -> review transition
                if run_review:
                    self.run_phase_validation("DEV", "REVIEW")

            # Review phase
            if run_review and not self.args.context and not self.args.develop:
                print("\n[3/3] Review Phase...")
                if self.context_monitor:
                    self.context_monitor.set_current_activity(
                        agent="REVIEWER",
                        phase="Code Review",
                        task="Reviewing implementation",
                        phases_completed=phases_completed,
                    )
                success, output = self.run_claude(
                    "SM", "sonnet", f"Review the implementation of story {self.args.story_key}"
                )
                if not success:
                    print(f"Review phase failed: {output[:200]}")
                    return 1

                phases_completed += 1
                if self.context_monitor:
                    self.context_monitor.set_current_activity(phases_completed=phases_completed)

                # Validate review -> complete transition
                self.run_phase_validation("REVIEW", "COMPLETE")

            # Clear activity when done
            if self.context_monitor:
                self.context_monitor.clear_current_activity()

            print("\n[OK] Story automation complete!")

            # Run post-completion validation
            self.run_post_validation()

            # Show final costs
            if self.tracker:
                print()
                self.display.print()
                print()

                summary = self.tracker.get_session_summary()
                print(f"Final Cost: ${summary['totals']['cost_usd']:.2f}")
                print(f"Tokens Used: {summary['totals']['total_tokens']:,}")

            return 0

        finally:
            self.stop_monitor()

            # Save session
            if self.tracker:
                self.tracker.end_session()

            # Show cost dashboard if requested
            if self.args.show_costs:
                print("\n" + "=" * 60)
                try:
                    from cost_dashboard import CostDashboard

                    dashboard = CostDashboard()
                    if self.tracker:
                        dashboard.show_session(self.tracker.session)
                except ImportError:
                    print("Cost dashboard not available")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nDetected platform:", get_platform())
        return 1

    args = parse_args()
    platform = get_platform()

    print(f"Platform: {platform}")

    # Use native runner if --native flag is set
    if args.native:
        print("Mode: Native Python with cost tracking")
        print()
        runner = NativeRunner(args)
        return runner.run()

    # Otherwise, delegate to platform-specific scripts
    # Build args list for subprocess
    script_args = [args.story_key]

    if args.develop:
        script_args.append("--develop")
    if args.review:
        script_args.append("--review")
    if args.context:
        script_args.append("--context")
    if args.no_commit:
        script_args.append("--no-commit")
    if args.with_pr:
        script_args.append("--with-pr")
    if args.model != "sonnet":
        script_args.extend(["--model", args.model])

    print(f"Running: run-story with args: {' '.join(script_args)}")
    print()

    if platform == "windows":
        return run_windows(script_args)
    else:
        return run_unix(script_args)


if __name__ == "__main__":
    sys.exit(main())
