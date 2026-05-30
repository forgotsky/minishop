#!/usr/bin/env python3
"""
Validation Loop CLI - Standalone validation runner for CI/CD and CLI usage.

Runs the three-tier validation system:
- Tier 1: Pre-flight (story exists, budget, dependencies)
- Tier 2: Inter-phase (code compiles, lint, transitions)
- Tier 3: Post-completion (tests, types, version sync)

Usage:
    python validate_loop.py [options]

Options:
    --story, -s     Story key to validate
    --tier, -t      Validation tier (1, 2, 3) or omit for all
    --all, -a       Run all tiers
    --auto-fix      Attempt automatic fixes
    --json          Output as JSON
    --quiet, -q     Minimal output
    --check         Exit with non-zero if any failures (for CI)

Examples:
    python validate_loop.py --story 3-5 --tier 3
    python validate_loop.py --all --json
    python validate_loop.py --tier 3 --auto-fix --check
"""

import argparse
import json
import sys
from pathlib import Path

# Add lib directory
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from validation_loop import (
    INTER_PHASE_GATES,
    POST_COMPLETION_GATES,
    PREFLIGHT_GATES,
    LoopContext,
    ValidationLoop,
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run validation loop checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_loop.py --story 3-5 --tier 3
  python validate_loop.py --all --json
  python validate_loop.py --tier 3 --auto-fix --check
        """,
    )

    parser.add_argument("--story", "-s", default="validation-check", help="Story key to validate")
    parser.add_argument(
        "--tier",
        "-t",
        type=int,
        choices=[1, 2, 3],
        help="Validation tier (1=preflight, 2=inter-phase, 3=post-completion)",
    )
    parser.add_argument("--all", "-a", action="store_true", help="Run all tiers")
    parser.add_argument("--auto-fix", action="store_true", help="Attempt automatic fixes")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    parser.add_argument(
        "--check", action="store_true", help="Exit with non-zero if any failures (for CI)"
    )

    return parser.parse_args()


def run_tier(tier: int, story_key: str, auto_fix: bool, quiet: bool):
    """Run a specific validation tier."""
    if tier == 1:
        gates = PREFLIGHT_GATES
        tier_name = "Pre-flight"
    elif tier == 2:
        gates = INTER_PHASE_GATES
        tier_name = "Inter-phase"
    else:
        gates = POST_COMPLETION_GATES
        tier_name = "Post-completion"

    if not quiet:
        print(f"\n[VALIDATION] Running {tier_name} checks (Tier {tier})...")

    loop = ValidationLoop(
        gates=gates,
        config={"auto_fix_enabled": auto_fix},
        story_key=story_key,
    )
    context = LoopContext(story_key=story_key, phase=f"tier_{tier}")

    if tier == 1:
        report = loop.run_preflight(context)
    elif tier == 2:
        report = loop.run_inter_phase(context)
    else:
        report = loop.run_post_completion(context)

    return report


def main():
    args = parse_args()

    reports = []
    overall_passed = True

    if args.all or args.tier is None:
        # Run all tiers
        for tier in [1, 2, 3]:
            report = run_tier(tier, args.story, args.auto_fix, args.quiet)
            reports.append(report)
            if report.failed:
                overall_passed = False
    else:
        # Run specific tier
        report = run_tier(args.tier, args.story, args.auto_fix, args.quiet)
        reports.append(report)
        if report.failed:
            overall_passed = False

    # Output results
    if args.json:
        output = {
            "story_key": args.story,
            "overall_passed": overall_passed,
            "reports": [r.to_dict() for r in reports],
        }
        print(json.dumps(output, indent=2))
    elif not args.quiet:
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        for report in reports:
            print(f"\nTier {report.tier}: {report.overall_result.value.upper()}")
            print(report.to_summary())

        print("\n" + "=" * 60)
        if overall_passed:
            print("[PASS] All validation checks passed")
        else:
            print("[FAIL] Some validation checks failed")
        print("=" * 60)

    # Exit code for CI
    if args.check:
        sys.exit(0 if overall_passed else 1)

    return 0 if overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
