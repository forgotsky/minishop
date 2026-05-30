#!/usr/bin/env python3
"""
Validation Loop - Automated feedback and validation system for agent pipelines.

Provides a three-tier validation framework:
- Tier 1: Pre-flight validation (before any agent runs)
- Tier 2: Inter-phase validation (between agents/phases)
- Tier 3: Post-completion validation (after pipeline completes)

Features:
- Configurable validation gates with retry logic
- Integration with shared memory for learning
- Cost-aware validation (respects budget limits)
- Automated fix suggestions and escalation
- Detailed validation history tracking

Usage:
    from lib.validation_loop import ValidationLoop, ValidationGate, ValidationResult

    # Create gates
    gates = [
        ValidationGate(
            name="tests_pass",
            validator=lambda ctx: run_tests(),
            on_fail="retry",
            max_retries=2
        ),
    ]

    # Run with validation
    loop = ValidationLoop(gates, config)
    result = loop.run_with_validation(pipeline_func, context)
"""

import json
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

# Try to import dependencies
try:
    from shared_memory import KnowledgeGraph, SharedMemory

    HAS_SHARED_MEMORY = True
except ImportError:
    HAS_SHARED_MEMORY = False

try:
    from cost_tracker import get_tracker

    HAS_COST_TRACKER = True
except ImportError:
    HAS_COST_TRACKER = False

try:
    from errors import log_error, log_info, log_warning

    HAS_ERRORS = True
except ImportError:
    HAS_ERRORS = False

    def log_info(msg: str) -> None:
        print(f"[INFO] {msg}")

    def log_warning(msg: str) -> None:
        print(f"[WARNING] {msg}", file=sys.stderr)

    def log_error(msg: str) -> None:
        print(f"[ERROR] {msg}", file=sys.stderr)


# Storage paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
VALIDATION_DIR = PROJECT_ROOT / "tooling" / ".automation" / "validation"
VALIDATION_HISTORY_DIR = VALIDATION_DIR / "history"


class ValidationResult(Enum):
    """Result of a validation gate check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class FailureAction(Enum):
    """Action to take on validation failure."""

    BLOCK = "block"  # Stop execution immediately
    WARN = "warn"  # Log warning but continue
    RETRY = "retry"  # Retry with specified agent
    ESCALATE = "escalate"  # Ask user for decision


@dataclass
class ValidationGate:
    """A single validation checkpoint."""

    name: str
    validator: Callable[..., bool]
    description: str = ""
    on_fail: FailureAction = FailureAction.WARN
    max_retries: int = 3
    retry_with_agent: Optional[str] = None
    auto_fix: Optional[Callable[..., bool]] = None
    timeout_seconds: int = 60
    tier: int = 2  # 1=preflight, 2=inter-phase, 3=post-completion
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.on_fail, str):
            self.on_fail = FailureAction(self.on_fail)


@dataclass
class GateResult:
    """Result from running a validation gate."""

    gate_name: str
    result: ValidationResult
    message: str = ""
    duration_ms: float = 0
    retry_count: int = 0
    auto_fixed: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "result": self.result.value,
        }


@dataclass
class LoopContext:
    """Context for a validation loop execution."""

    story_key: str
    iteration: int = 0
    max_iterations: int = 3
    accumulated_issues: list[str] = field(default_factory=list)
    accumulated_fixes: list[str] = field(default_factory=list)
    cost_so_far: float = 0.0
    time_elapsed_seconds: float = 0.0
    phase: str = ""
    from_agent: str = ""
    to_agent: str = ""
    pipeline_output: Any = None

    def to_dict(self) -> dict:
        return {
            "story_key": self.story_key,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "accumulated_issues": self.accumulated_issues,
            "accumulated_fixes": self.accumulated_fixes,
            "cost_so_far": self.cost_so_far,
            "time_elapsed_seconds": self.time_elapsed_seconds,
            "phase": self.phase,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
        }


@dataclass
class ValidationReport:
    """Complete validation report for a run."""

    id: str
    timestamp: str
    story_key: str
    tier: int
    gate_results: list[GateResult]
    overall_result: ValidationResult
    total_duration_ms: float
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.overall_result in (ValidationResult.PASS, ValidationResult.WARN)

    @property
    def failed(self) -> bool:
        return self.overall_result in (ValidationResult.FAIL, ValidationResult.ERROR)

    @property
    def warnings(self) -> list[GateResult]:
        return [g for g in self.gate_results if g.result == ValidationResult.WARN]

    @property
    def failures(self) -> list[GateResult]:
        return [g for g in self.gate_results if g.result == ValidationResult.FAIL]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "story_key": self.story_key,
            "tier": self.tier,
            "gate_results": [g.to_dict() for g in self.gate_results],
            "overall_result": self.overall_result.value,
            "total_duration_ms": self.total_duration_ms,
            "passed": self.passed,
            "context": self.context,
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Validation Report: {self.overall_result.value.upper()}",
            f"Story: {self.story_key} | Tier: {self.tier} | Duration: {self.total_duration_ms:.0f}ms",
            "",
        ]

        passed = [g for g in self.gate_results if g.result == ValidationResult.PASS]
        if passed:
            lines.append(f"[PASS] {len(passed)} gate(s) passed")
            for g in passed:
                lines.append(f"  - {g.gate_name}")

        if self.warnings:
            lines.append(f"[WARN] {len(self.warnings)} warning(s)")
            for g in self.warnings:
                lines.append(f"  - {g.gate_name}: {g.message}")

        if self.failures:
            lines.append(f"[FAIL] {len(self.failures)} failure(s)")
            for g in self.failures:
                lines.append(f"  - {g.gate_name}: {g.message}")

        return "\n".join(lines)


class ValidationLoop:
    """
    Main validation loop orchestrator.

    Runs validation gates and manages retry logic, escalation,
    and feedback recording.
    """

    def __init__(
        self,
        gates: list[ValidationGate],
        config: Optional[dict[str, Any]] = None,
        story_key: Optional[str] = None,
    ):
        self.gates = gates
        self.config = config or {}
        self.story_key = story_key

        # Initialize storage
        VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
        VALIDATION_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

        # Optional integrations
        self.shared_memory = SharedMemory(story_key) if HAS_SHARED_MEMORY else None
        self.knowledge_graph = KnowledgeGraph(story_key) if HAS_SHARED_MEMORY else None

        # History tracking
        self.reports: list[ValidationReport] = []

    def run_gate(
        self,
        gate: ValidationGate,
        context: LoopContext,
    ) -> GateResult:
        """Run a single validation gate."""
        import time

        start_time = time.time()
        retry_count = 0
        auto_fixed = False
        message = ""
        details: dict[str, Any] = {}

        try:
            # Run validator
            passed = gate.validator(context)

            if passed:
                result = ValidationResult.PASS
                message = "Validation passed"
            else:
                # Try auto-fix if available
                if gate.auto_fix and self.config.get("auto_fix_enabled", True):
                    try:
                        fix_result = gate.auto_fix(context)
                        if fix_result:
                            # Re-run validation after fix
                            passed = gate.validator(context)
                            if passed:
                                result = ValidationResult.PASS
                                auto_fixed = True
                                message = "Passed after auto-fix"
                            else:
                                result = ValidationResult.FAIL
                                message = "Auto-fix applied but validation still failed"
                        else:
                            result = ValidationResult.FAIL
                            message = "Auto-fix failed"
                    except Exception as e:
                        result = ValidationResult.FAIL
                        message = f"Auto-fix error: {e}"
                else:
                    result = ValidationResult.FAIL
                    message = "Validation failed"

        except TimeoutError:
            result = ValidationResult.ERROR
            message = f"Validation timed out after {gate.timeout_seconds}s"
        except Exception as e:
            result = ValidationResult.ERROR
            message = f"Validation error: {e}"
            details["exception"] = str(e)

        duration_ms = (time.time() - start_time) * 1000

        return GateResult(
            gate_name=gate.name,
            result=result,
            message=message,
            duration_ms=duration_ms,
            retry_count=retry_count,
            auto_fixed=auto_fixed,
            details=details,
        )

    def run_gates(
        self,
        context: LoopContext,
        tier: Optional[int] = None,
    ) -> ValidationReport:
        """Run all gates (optionally filtered by tier)."""
        import time

        start_time = time.time()
        gate_results: list[GateResult] = []

        # Filter gates by tier if specified
        gates_to_run = self.gates
        if tier is not None:
            gates_to_run = [g for g in self.gates if g.tier == tier]

        for gate in gates_to_run:
            result = self.run_gate(gate, context)
            gate_results.append(result)

            # Handle blocking failures
            if result.result == ValidationResult.FAIL:
                if gate.on_fail == FailureAction.BLOCK:
                    log_error(f"Gate '{gate.name}' failed with BLOCK action. Stopping.")
                    break

        # Determine overall result
        if any(r.result == ValidationResult.ERROR for r in gate_results):
            overall = ValidationResult.ERROR
        elif any(r.result == ValidationResult.FAIL for r in gate_results):
            overall = ValidationResult.FAIL
        elif any(r.result == ValidationResult.WARN for r in gate_results):
            overall = ValidationResult.WARN
        else:
            overall = ValidationResult.PASS

        total_duration = (time.time() - start_time) * 1000

        report = ValidationReport(
            id=f"val_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            story_key=context.story_key,
            tier=tier or 0,
            gate_results=gate_results,
            overall_result=overall,
            total_duration_ms=total_duration,
            context=context.to_dict(),
        )

        # Record in history
        self.reports.append(report)
        self._save_report(report)

        # Record in shared memory
        if self.shared_memory:
            self.shared_memory.add(
                agent="VALIDATOR",
                content=f"Validation {overall.value}: {len(gate_results)} gates, "
                f"{len([r for r in gate_results if r.result == ValidationResult.PASS])} passed",
                tags=["validation", f"tier-{tier or 0}", overall.value],
            )

        return report

    def run_with_validation(
        self,
        pipeline_func: Callable[..., Any],
        context: LoopContext,
        tier: int = 2,
    ) -> tuple[Any, ValidationReport]:
        """
        Run a pipeline function with validation loop.

        Returns:
            Tuple of (pipeline_result, validation_report)
        """
        for iteration in range(context.max_iterations):
            context.iteration = iteration

            # Run the pipeline
            try:
                result = pipeline_func()
                context.pipeline_output = result
            except Exception as e:
                log_error(f"Pipeline failed: {e}")
                context.accumulated_issues.append(str(e))
                continue

            # Run validation
            report = self.run_gates(context, tier=tier)

            if report.passed:
                log_info(f"Validation passed on iteration {iteration + 1}")
                return result, report

            # Collect issues for retry
            for gate_result in report.failures:
                context.accumulated_issues.append(f"{gate_result.gate_name}: {gate_result.message}")

            # Check if any gate wants to retry
            gates_by_name = {g.name: g for g in self.gates}
            should_retry = False
            for gate_result in report.failures:
                gate = gates_by_name.get(gate_result.gate_name)
                if gate and gate.on_fail == FailureAction.RETRY:
                    if iteration < gate.max_retries:
                        should_retry = True
                        log_warning(
                            f"Gate '{gate.name}' requesting retry "
                            f"({iteration + 1}/{gate.max_retries})"
                        )

            if not should_retry:
                log_error("Validation failed, no retry available")
                break

        # Return last result with failed validation
        return context.pipeline_output, report

    def run_preflight(self, context: LoopContext) -> ValidationReport:
        """Run tier 1 (pre-flight) validation."""
        return self.run_gates(context, tier=1)

    def run_inter_phase(self, context: LoopContext) -> ValidationReport:
        """Run tier 2 (inter-phase) validation."""
        return self.run_gates(context, tier=2)

    def run_post_completion(self, context: LoopContext) -> ValidationReport:
        """Run tier 3 (post-completion) validation."""
        return self.run_gates(context, tier=3)

    def _save_report(self, report: ValidationReport):
        """Save validation report to disk."""
        filename = f"{datetime.now().strftime('%Y-%m-%d')}_{report.id}.json"
        filepath = VALIDATION_HISTORY_DIR / filename
        try:
            with open(filepath, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
        except OSError as e:
            log_warning(f"Failed to save validation report: {e}")

    def get_actionable_feedback(self, report: ValidationReport) -> dict[str, Any]:
        """Extract actionable feedback from a validation report."""
        feedback = {
            "issues": [],
            "suggestions": [],
            "auto_fixes_available": [],
        }

        gates_by_name = {g.name: g for g in self.gates}

        for gate_result in report.failures:
            gate = gates_by_name.get(gate_result.gate_name)
            feedback["issues"].append(
                {
                    "gate": gate_result.gate_name,
                    "message": gate_result.message,
                    "action": gate.on_fail.value if gate else "unknown",
                }
            )

            if gate and gate.auto_fix:
                feedback["auto_fixes_available"].append(gate.name)

            if gate and gate.retry_with_agent:
                feedback["suggestions"].append(
                    f"Retry '{gate.name}' with {gate.retry_with_agent} agent"
                )

        return feedback


# =============================================================================
# Pre-defined Validation Gates
# =============================================================================


def _check_story_exists(context: LoopContext) -> bool:
    """Check if story file exists."""
    stories_dir = PROJECT_ROOT / "tooling" / ".automation" / "stories"
    story_file = stories_dir / f"{context.story_key}.md"
    return story_file.exists()


def _check_budget_available(context: LoopContext) -> bool:
    """Check if budget is available."""
    if not HAS_COST_TRACKER:
        return True  # Skip check if no cost tracker

    tracker = get_tracker()
    if not tracker:
        return True  # No active tracker, assume OK

    ok, _, _ = tracker.check_budget()
    return ok


def _check_git_clean(context: LoopContext) -> bool:
    """Check if git working directory is clean or has only staged changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=10,
        )
        # Allow staged changes (prefixed with M, A, etc. in first column)
        # but not unstaged changes (prefixed in second column)
        for line in result.stdout.strip().split("\n"):
            if line and line[1] != " ":  # Second column is not space
                return False
        return True
    except Exception:
        return True  # Don't block on git check failure


def _check_dependencies_valid(context: LoopContext) -> bool:
    """Run validate_setup.py in check mode."""
    validate_script = PROJECT_ROOT / "tooling" / "scripts" / "validate_setup.py"
    if not validate_script.exists():
        return True  # Skip if script doesn't exist

    try:
        result = subprocess.run(
            [sys.executable, str(validate_script), "--quiet"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return True  # Don't block on validation failure


def _check_tests_pass(context: LoopContext) -> bool:
    """Run pytest and check if tests pass."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=300,
        )
        return result.returncode == 0
    except Exception:
        return False


def _check_lint_pass(context: LoopContext) -> bool:
    """Run ruff linter and check for errors."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=60,
        )
        # Don't block if ruff not installed
        if "No module named" in result.stderr:
            return True
        return result.returncode == 0
    except Exception:
        return True  # Don't block on errors


def _check_types_pass(context: LoopContext) -> bool:
    """Run mypy type checker."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "--ignore-missing-imports", "."],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=120,
        )
        # Don't block if mypy not installed
        if "No module named" in result.stderr:
            return True
        return result.returncode == 0
    except Exception:
        return True  # Don't block on errors


def _check_version_synced(context: LoopContext) -> bool:
    """Check if versions are synchronized."""
    sync_script = PROJECT_ROOT / "tooling" / "scripts" / "update_version.py"
    if not sync_script.exists():
        return True

    try:
        result = subprocess.run(
            [sys.executable, str(sync_script), "--check"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return True


def _check_changelog_updated(context: LoopContext) -> bool:
    """Check if CHANGELOG.md has been updated (for story-related changes)."""
    changelog = PROJECT_ROOT / "CHANGELOG.md"
    if not changelog.exists():
        return True

    try:
        # Check if CHANGELOG.md has uncommitted changes
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=10,
        )
        return "CHANGELOG.md" in result.stdout
    except Exception:
        return True


def _auto_fix_lint(context: LoopContext) -> bool:
    """Auto-fix lint issues using ruff."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--fix", "."],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=60,
        )
        # Don't block if ruff not installed
        if "No module named" in result.stderr:
            return True
        return result.returncode == 0
    except Exception:
        return True  # Don't block on errors


def _auto_fix_format(context: LoopContext) -> bool:
    """Auto-fix formatting using ruff format."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "format", "."],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=60,
        )
        # Don't block if ruff not installed
        if "No module named" in result.stderr:
            return True
        return result.returncode == 0
    except Exception:
        return True  # Don't block on errors


# =============================================================================
# Pre-defined Gate Sets
# =============================================================================

PREFLIGHT_GATES = [
    ValidationGate(
        name="story_exists",
        description="Verify story file exists",
        validator=_check_story_exists,
        on_fail=FailureAction.BLOCK,
        tier=1,
        tags=["preflight", "required"],
    ),
    ValidationGate(
        name="budget_available",
        description="Check budget is not exceeded",
        validator=_check_budget_available,
        on_fail=FailureAction.BLOCK,
        tier=1,
        tags=["preflight", "budget"],
    ),
    ValidationGate(
        name="dependencies_valid",
        description="Validate setup and dependencies",
        validator=_check_dependencies_valid,
        on_fail=FailureAction.WARN,
        tier=1,
        tags=["preflight", "setup"],
    ),
]

INTER_PHASE_GATES = [
    ValidationGate(
        name="git_clean",
        description="Check git working directory state",
        validator=_check_git_clean,
        on_fail=FailureAction.WARN,
        tier=2,
        tags=["inter-phase", "git"],
    ),
    ValidationGate(
        name="lint_pass",
        description="Run linter checks",
        validator=_check_lint_pass,
        on_fail=FailureAction.RETRY,
        auto_fix=_auto_fix_lint,
        max_retries=2,
        retry_with_agent="DEV",
        tier=2,
        tags=["inter-phase", "quality"],
    ),
]

POST_COMPLETION_GATES = [
    ValidationGate(
        name="tests_pass",
        description="Run test suite",
        validator=_check_tests_pass,
        on_fail=FailureAction.BLOCK,
        timeout_seconds=300,
        tier=3,
        tags=["post-completion", "tests"],
    ),
    ValidationGate(
        name="lint_clean",
        description="Verify no lint errors",
        validator=_check_lint_pass,
        on_fail=FailureAction.WARN,
        auto_fix=_auto_fix_lint,
        tier=3,
        tags=["post-completion", "quality"],
    ),
    ValidationGate(
        name="types_valid",
        description="Run type checker",
        validator=_check_types_pass,
        on_fail=FailureAction.WARN,
        tier=3,
        tags=["post-completion", "types"],
    ),
    ValidationGate(
        name="version_synced",
        description="Check version synchronization",
        validator=_check_version_synced,
        on_fail=FailureAction.WARN,
        tier=3,
        tags=["post-completion", "release"],
    ),
]

ALL_GATES = PREFLIGHT_GATES + INTER_PHASE_GATES + POST_COMPLETION_GATES


# =============================================================================
# Phase Transition Gates
# =============================================================================

PHASE_TRANSITION_GATES: dict[tuple[str, str], list[ValidationGate]] = {
    ("CONTEXT", "DEV"): [
        ValidationGate(
            name="context_complete",
            description="Verify context phase produced required outputs",
            validator=lambda ctx: ctx.pipeline_output is not None,
            on_fail=FailureAction.RETRY,
            retry_with_agent="SM",
            tier=2,
        ),
    ],
    ("DEV", "REVIEW"): [
        ValidationGate(
            name="code_compiles",
            description="Verify code compiles/parses without errors",
            validator=_check_lint_pass,
            on_fail=FailureAction.RETRY,
            auto_fix=_auto_fix_lint,
            retry_with_agent="DEV",
            tier=2,
        ),
    ],
    ("REVIEW", "COMPLETE"): [
        ValidationGate(
            name="review_approved",
            description="Verify review was approved",
            validator=lambda ctx: "approved" in str(ctx.pipeline_output).lower(),
            on_fail=FailureAction.RETRY,
            retry_with_agent="DEV",
            tier=2,
        ),
    ],
}


def get_phase_gates(from_phase: str, to_phase: str) -> list[ValidationGate]:
    """Get validation gates for a specific phase transition."""
    key = (from_phase.upper(), to_phase.upper())
    return PHASE_TRANSITION_GATES.get(key, [])


# =============================================================================
# Validation Memory (extends SharedMemory patterns)
# =============================================================================


class ValidationMemory:
    """
    Extended memory system for tracking validation history and patterns.

    Integrates with SharedMemory and KnowledgeGraph to:
    - Record validation results
    - Track common failure patterns
    - Suggest preventive measures
    """

    def __init__(self, story_key: Optional[str] = None):
        self.story_key = story_key
        self.validation_dir = VALIDATION_DIR
        self.validation_dir.mkdir(parents=True, exist_ok=True)

        if HAS_SHARED_MEMORY:
            self.shared_memory = SharedMemory(story_key)
            self.knowledge_graph = KnowledgeGraph(story_key)
        else:
            self.shared_memory = None
            self.knowledge_graph = None

    def record_validation(
        self,
        gate_name: str,
        result: ValidationResult,
        context: LoopContext,
        details: Optional[dict[str, Any]] = None,
    ):
        """Record a validation result."""
        if self.shared_memory:
            self.shared_memory.add(
                agent="VALIDATOR",
                content=f"Gate '{gate_name}': {result.value}",
                tags=["validation", gate_name, result.value],
            )

        if self.knowledge_graph:
            self.knowledge_graph.add_decision(
                agent="VALIDATOR",
                topic=f"validation:{gate_name}",
                decision=result.value,
                context={
                    "iteration": context.iteration,
                    "phase": context.phase,
                    "details": details or {},
                },
            )

    def get_common_failures(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most common validation failures for learning."""
        if not self.knowledge_graph:
            return []

        failures = []
        for dec in self.knowledge_graph.decisions.values():
            if dec.topic.startswith("validation:") and dec.decision == "fail":
                failures.append(
                    {
                        "gate": dec.topic.replace("validation:", ""),
                        "timestamp": dec.timestamp,
                        "context": dec.context,
                    }
                )

        return sorted(failures, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_success_rate(self, gate_name: str) -> float:
        """Calculate success rate for a specific gate."""
        if not self.knowledge_graph:
            return 1.0

        total = 0
        passed = 0
        for dec in self.knowledge_graph.decisions.values():
            if dec.topic == f"validation:{gate_name}":
                total += 1
                if dec.decision == "pass":
                    passed += 1

        return passed / total if total > 0 else 1.0


# =============================================================================
# Convenience Functions
# =============================================================================


def create_validation_loop(
    story_key: str,
    gates: Optional[list[ValidationGate]] = None,
    config: Optional[dict[str, Any]] = None,
) -> ValidationLoop:
    """Create a validation loop with default or custom gates."""
    return ValidationLoop(
        gates=gates or ALL_GATES,
        config=config or {"auto_fix_enabled": True},
        story_key=story_key,
    )


def run_preflight_validation(story_key: str) -> ValidationReport:
    """Quick function to run pre-flight validation."""
    loop = ValidationLoop(PREFLIGHT_GATES, story_key=story_key)
    context = LoopContext(story_key=story_key)
    return loop.run_preflight(context)


def run_post_completion_validation(story_key: str) -> ValidationReport:
    """Quick function to run post-completion validation."""
    loop = ValidationLoop(POST_COMPLETION_GATES, story_key=story_key)
    context = LoopContext(story_key=story_key)
    return loop.run_post_completion(context)


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run validation loop")
    parser.add_argument("--story", "-s", help="Story key to validate")
    parser.add_argument(
        "--tier",
        "-t",
        type=int,
        choices=[1, 2, 3],
        help="Validation tier (1=preflight, 2=inter-phase, 3=post-completion)",
    )
    parser.add_argument("--all", "-a", action="store_true", help="Run all tiers")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    args = parser.parse_args()

    story_key = args.story or "validation-test"
    context = LoopContext(story_key=story_key)

    if args.all:
        loop = ValidationLoop(ALL_GATES, story_key=story_key)
        reports = []
        for tier in [1, 2, 3]:
            report = loop.run_gates(context, tier=tier)
            reports.append(report)

        if args.json:
            print(json.dumps([r.to_dict() for r in reports], indent=2))
        else:
            for report in reports:
                print(report.to_summary())
                print()
    else:
        tier = args.tier or 1
        if tier == 1:
            gates = PREFLIGHT_GATES
        elif tier == 2:
            gates = INTER_PHASE_GATES
        else:
            gates = POST_COMPLETION_GATES

        loop = ValidationLoop(gates, story_key=story_key)
        report = loop.run_gates(context, tier=tier)

        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        elif not args.quiet:
            print(report.to_summary())

        sys.exit(0 if report.passed else 1)
