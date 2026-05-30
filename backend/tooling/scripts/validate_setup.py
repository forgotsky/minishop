#!/usr/bin/env python3
"""
Validate Setup - User-friendly setup verification for Devflow.

Checks that all components are properly configured and working.

Usage:
    python tooling/scripts/validate_setup.py
    python tooling/scripts/validate_setup.py --verbose
    python tooling/scripts/validate_setup.py --fix

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
    2 - Critical error during validation
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from lib.colors import Colors


class CheckStatus(Enum):
    """Status of a validation check."""

    PASS = "[PASS]"
    FAIL = "[FAIL]"
    WARN = "[WARNING]"
    SKIP = "[SKIP]"
    INFO = "[INFO]"


@dataclass
class CheckResult:
    """Result of a validation check."""

    name: str
    status: CheckStatus
    message: str
    details: Optional[str] = None
    fix_command: Optional[str] = None


# Project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
LIB_DIR = SCRIPT_DIR / "lib"
AUTOMATION_DIR = PROJECT_ROOT / "tooling" / ".automation"


class SetupValidator:
    """Validates the Devflow setup."""

    def __init__(self, verbose: bool = False, fix: bool = False):
        self.verbose = verbose
        self.fix = fix
        self.results: list[CheckResult] = []

    def add_result(self, result: CheckResult):
        """Add a check result."""
        self.results.append(result)
        self._print_result(result)

    def _print_result(self, result: CheckResult):
        """Print a check result."""
        status_color = {
            CheckStatus.PASS: Colors.GREEN,
            CheckStatus.FAIL: Colors.RED,
            CheckStatus.WARN: Colors.YELLOW,
            CheckStatus.SKIP: Colors.DIM,
            CheckStatus.INFO: Colors.BLUE,
        }.get(result.status, "")

        print(
            f"  {result.status.value} {status_color}{result.name}{Colors.RESET}: {result.message}"
        )

        if self.verbose and result.details:
            for line in result.details.split("\n"):
                print(f"      {Colors.DIM}{line}{Colors.RESET}")

        if result.status == CheckStatus.FAIL and result.fix_command:
            print(f"      {Colors.CYAN}Fix: {result.fix_command}{Colors.RESET}")

    def check_python_version(self):
        """Check Python version is supported."""
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        if version >= (3, 9):
            self.add_result(
                CheckResult(
                    name="Python Version",
                    status=CheckStatus.PASS,
                    message=f"Python {version_str} is supported",
                )
            )
        elif version >= (3, 7):
            self.add_result(
                CheckResult(
                    name="Python Version",
                    status=CheckStatus.WARN,
                    message=f"Python {version_str} may work but 3.9+ recommended",
                )
            )
        else:
            self.add_result(
                CheckResult(
                    name="Python Version",
                    status=CheckStatus.FAIL,
                    message=f"Python {version_str} is not supported (need 3.9+)",
                    fix_command="pyenv install 3.11 && pyenv local 3.11",
                )
            )

    def check_project_structure(self):
        """Check required project structure exists."""
        required_dirs = [
            PROJECT_ROOT / "tooling",
            PROJECT_ROOT / "tooling" / "scripts",
            PROJECT_ROOT / "tooling" / "scripts" / "lib",
        ]

        optional_dirs = [
            AUTOMATION_DIR,
            AUTOMATION_DIR / "costs",
            AUTOMATION_DIR / "costs" / "sessions",
        ]

        all_exist = True
        missing = []

        for dir_path in required_dirs:
            if not dir_path.exists():
                all_exist = False
                missing.append(str(dir_path.relative_to(PROJECT_ROOT)))

        if all_exist:
            self.add_result(
                CheckResult(
                    name="Project Structure",
                    status=CheckStatus.PASS,
                    message="All required directories exist",
                )
            )
        else:
            self.add_result(
                CheckResult(
                    name="Project Structure",
                    status=CheckStatus.FAIL,
                    message=f"Missing directories: {', '.join(missing)}",
                    fix_command=f"mkdir -p {' '.join(missing)}",
                )
            )

        # Check optional dirs
        for dir_path in optional_dirs:
            if not dir_path.exists():
                if self.fix:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.add_result(
                        CheckResult(
                            name=f"Directory {dir_path.name}",
                            status=CheckStatus.PASS,
                            message="Created missing directory",
                        )
                    )
                else:
                    self.add_result(
                        CheckResult(
                            name=f"Directory {dir_path.name}",
                            status=CheckStatus.WARN,
                            message="Optional directory missing (will be created on first use)",
                            fix_command=f"mkdir -p {dir_path}",
                        )
                    )

    def check_core_modules(self):
        """Check core Python modules exist and are importable."""
        modules = [
            ("cost_tracker", LIB_DIR / "cost_tracker.py"),
            ("cost_config", LIB_DIR / "cost_config.py"),
            ("cost_display", LIB_DIR / "cost_display.py"),
            ("currency_converter", LIB_DIR / "currency_converter.py"),
        ]

        # Add lib to path for imports
        sys.path.insert(0, str(LIB_DIR))

        for module_name, module_path in modules:
            if not module_path.exists():
                self.add_result(
                    CheckResult(
                        name=f"Module {module_name}",
                        status=CheckStatus.FAIL,
                        message=f"File not found: {module_path.name}",
                    )
                )
                continue

            try:
                __import__(module_name)
                self.add_result(
                    CheckResult(
                        name=f"Module {module_name}",
                        status=CheckStatus.PASS,
                        message="Imports successfully",
                    )
                )
            except ImportError as e:
                self.add_result(
                    CheckResult(
                        name=f"Module {module_name}",
                        status=CheckStatus.FAIL,
                        message=f"Import error: {e}",
                        details=str(e),
                    )
                )
            except Exception as e:
                self.add_result(
                    CheckResult(
                        name=f"Module {module_name}",
                        status=CheckStatus.WARN,
                        message=f"Warning during import: {type(e).__name__}",
                        details=str(e),
                    )
                )

    def check_cost_tracker_functionality(self):
        """Test core cost tracker functionality."""
        try:
            sys.path.insert(0, str(LIB_DIR))
            from cost_tracker import PRICING, CostTracker

            # Check pricing is defined
            if not PRICING:
                self.add_result(
                    CheckResult(
                        name="Pricing Configuration",
                        status=CheckStatus.FAIL,
                        message="No pricing data defined",
                    )
                )
            else:
                models = list(PRICING.keys())
                self.add_result(
                    CheckResult(
                        name="Pricing Configuration",
                        status=CheckStatus.PASS,
                        message=f"{len(models)} models configured",
                        details=f"Models: {', '.join(models[:5])}...",
                    )
                )

            # Test cost calculation
            tracker = CostTracker(
                story_key="validation-test", budget_limit_usd=10.00, auto_save=False
            )
            cost = tracker.calculate_cost("sonnet", 1000, 500)

            if cost > 0:
                self.add_result(
                    CheckResult(
                        name="Cost Calculation",
                        status=CheckStatus.PASS,
                        message=f"Calculated ${cost:.6f} for test tokens",
                    )
                )
            else:
                self.add_result(
                    CheckResult(
                        name="Cost Calculation",
                        status=CheckStatus.WARN,
                        message="Cost calculation returned 0",
                    )
                )

            # Test budget checking
            ok, level, msg = tracker.check_budget()
            self.add_result(
                CheckResult(
                    name="Budget Monitoring",
                    status=CheckStatus.PASS,
                    message=f"Budget check working (status: {level})",
                )
            )

        except Exception as e:
            self.add_result(
                CheckResult(
                    name="Cost Tracker",
                    status=CheckStatus.FAIL,
                    message=f"Error testing cost tracker: {e}",
                    details=str(e),
                )
            )

    def check_environment_config(self):
        """Check environment configuration."""
        env_vars = {
            "MAX_BUDGET_CONTEXT": ("Budget for context phase", "3.00"),
            "MAX_BUDGET_DEV": ("Budget for development phase", "15.00"),
            "MAX_BUDGET_REVIEW": ("Budget for review phase", "5.00"),
            "COST_DISPLAY_CURRENCY": ("Display currency", "USD"),
        }

        configured = 0
        for var, (_desc, _default) in env_vars.items():
            value = os.getenv(var)
            if value:
                configured += 1
                if self.verbose:
                    self.add_result(
                        CheckResult(
                            name=f"Env: {var}", status=CheckStatus.INFO, message=f"Set to '{value}'"
                        )
                    )

        if configured > 0:
            self.add_result(
                CheckResult(
                    name="Environment Variables",
                    status=CheckStatus.PASS,
                    message=f"{configured}/{len(env_vars)} custom settings configured",
                )
            )
        else:
            self.add_result(
                CheckResult(
                    name="Environment Variables",
                    status=CheckStatus.INFO,
                    message="Using default configuration (all optional)",
                )
            )

    def check_storage_writable(self):
        """Check that storage directories are writable."""
        test_dirs = [
            AUTOMATION_DIR / "costs" / "sessions",
        ]

        for test_dir in test_dirs:
            test_dir.mkdir(parents=True, exist_ok=True)
            test_file = test_dir / ".write_test"

            try:
                test_file.write_text("test")
                test_file.unlink()
                self.add_result(
                    CheckResult(
                        name=f"Storage: {test_dir.name}",
                        status=CheckStatus.PASS,
                        message="Directory is writable",
                    )
                )
            except PermissionError:
                self.add_result(
                    CheckResult(
                        name=f"Storage: {test_dir.name}",
                        status=CheckStatus.FAIL,
                        message="Directory is not writable",
                        fix_command=f"chmod 755 {test_dir}",
                    )
                )
            except Exception as e:
                self.add_result(
                    CheckResult(
                        name=f"Storage: {test_dir.name}",
                        status=CheckStatus.WARN,
                        message=f"Could not verify: {e}",
                    )
                )

    def check_shell_scripts(self):
        """Check shell scripts are executable."""
        shell_scripts = list(SCRIPT_DIR.glob("*.sh"))

        non_executable = []
        for script in shell_scripts:
            if not os.access(script, os.X_OK):
                non_executable.append(script.name)
                if self.fix:
                    os.chmod(script, 0o755)

        if not shell_scripts:
            self.add_result(
                CheckResult(
                    name="Shell Scripts", status=CheckStatus.INFO, message="No shell scripts found"
                )
            )
        elif non_executable and not self.fix:
            self.add_result(
                CheckResult(
                    name="Shell Scripts",
                    status=CheckStatus.WARN,
                    message=f"{len(non_executable)} scripts not executable",
                    fix_command="chmod +x tooling/scripts/*.sh",
                )
            )
        else:
            self.add_result(
                CheckResult(
                    name="Shell Scripts",
                    status=CheckStatus.PASS,
                    message=f"{len(shell_scripts)} scripts are executable",
                )
            )

    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        print(f"\n{Colors.BOLD}Devflow Setup Validation{Colors.RESET}\n")
        print(f"  Project: {PROJECT_ROOT}")
        print(f"  Python:  {sys.executable}")
        print()

        print(f"{Colors.BOLD}Core Checks:{Colors.RESET}")
        self.check_python_version()
        self.check_project_structure()
        self.check_core_modules()

        print(f"\n{Colors.BOLD}Functionality Checks:{Colors.RESET}")
        self.check_cost_tracker_functionality()

        print(f"\n{Colors.BOLD}Configuration Checks:{Colors.RESET}")
        self.check_environment_config()
        self.check_storage_writable()
        self.check_shell_scripts()

        # Summary
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAIL)
        warned = sum(1 for r in self.results if r.status == CheckStatus.WARN)

        print(f"\n{Colors.BOLD}━━━ Summary ━━━{Colors.RESET}")
        print(f"  {Colors.GREEN}Passed:{Colors.RESET} {passed}")
        if warned:
            print(f"  {Colors.YELLOW}Warnings:{Colors.RESET} {warned}")
        if failed:
            print(f"  {Colors.RED}Failed:{Colors.RESET} {failed}")

        if failed == 0:
            print(
                f"\n{Colors.GREEN}{Colors.BOLD}[OK] All checks passed! Devflow is ready to use.{Colors.RESET}\n"
            )
            return True
        else:
            print(
                f"\n{Colors.RED}{Colors.BOLD}[FAIL] {failed} check(s) failed. Please fix the issues above.{Colors.RESET}"
            )
            if not self.fix:
                print(f"  {Colors.DIM}Run with --fix to auto-fix some issues.{Colors.RESET}\n")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Devflow setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_setup.py           Run basic validation
  python validate_setup.py -v        Run with verbose output
  python validate_setup.py --fix     Auto-fix fixable issues
""",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--fix", action="store_true", help="Attempt to auto-fix issues")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    try:
        validator = SetupValidator(verbose=args.verbose, fix=args.fix)
        success = validator.run_all_checks()

        if args.json:
            results = [
                {
                    "name": r.name,
                    "status": r.status.name,
                    "message": r.message,
                    "details": r.details,
                }
                for r in validator.results
            ]
            print(json.dumps(results, indent=2))

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nValidation cancelled.")
        sys.exit(2)
    except Exception as e:
        print(f"\n{Colors.RED}Critical error during validation: {e}{Colors.RESET}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
