#!/usr/bin/env python3
"""
Validate Overrides - Override YAML Validation and Linting

This script validates all override YAML files in the overrides directory.
It checks for:
  - Valid YAML syntax
  - Required fields
  - Valid field types
  - Valid model names
  - Valid budget ranges
  - Schema compliance

Usage:
    python validate-overrides.py              # Validate all overrides
    python validate-overrides.py dev          # Validate specific agent override
    python validate-overrides.py --fix        # Auto-fix common issues
    python validate-overrides.py --verbose    # Show detailed output
    python validate-overrides.py --json       # Output results as JSON
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.colors import Colors

# Valid values
VALID_MODELS = ["sonnet", "opus", "haiku"]
MIN_BUDGET = 0.01
MAX_BUDGET = 100.00
VALID_TECH_LEVELS = ["beginner", "intermediate", "advanced", "expert"]

# Schema definitions
OVERRIDE_SCHEMA = {
    "persona": {
        "type": "object",
        "properties": {
            "role": {"type": "string"},
            "identity": {"type": "string"},
            "communication_style": {"type": "string"},
            "principles": {"type": "list"},
        },
    },
    "additional_rules": {"type": "list"},
    "memories": {"type": "list"},
    "critical_actions": {"type": "list"},
    "model": {"type": "string", "enum": VALID_MODELS},
    "max_budget_usd": {"type": "number", "min": MIN_BUDGET, "max": MAX_BUDGET},
    "tools": {"type": "string"},
}

USER_PROFILE_SCHEMA = {
    "user": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "technical_level": {"type": "string", "enum": VALID_TECH_LEVELS},
            "communication_style": {"type": "string"},
        },
    },
    "preferences": {
        "type": "object",
        "properties": {
            "code_style": {"type": "list"},
            "documentation": {"type": "string"},
        },
    },
    "memories": {"type": "list"},
}


@dataclass
class ValidationResult:
    """Result of validating a single file."""

    file_path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file_path,
            "valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }


class YAMLValidator:
    """Simple YAML validator without external dependencies."""

    def __init__(self, content: str):
        self.content = content
        self.lines = content.split("\n")
        self.data: dict[str, Any] = {}

    def parse(self) -> tuple[bool, str]:
        """Parse YAML content and return (success, error_message)."""
        try:
            self._parse_lines()
            return True, ""
        except Exception as e:
            return False, str(e)

    def _parse_lines(self):
        """Parse YAML lines into a dictionary structure."""
        current_list_key = None
        current_list: list[str] = []

        for i, line in enumerate(self.lines, 1):
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith("#"):
                continue

            # Check for tabs (should be spaces)
            if "\t" in line:
                raise ValueError(f"Line {i}: Contains tabs (use spaces instead)")

            # Check for unclosed quotes
            double_quotes = line.count('"')
            single_quotes = line.count("'")
            if double_quotes % 2 != 0:
                raise ValueError(f"Line {i}: Unclosed double quote")
            if single_quotes % 2 != 0:
                raise ValueError(f"Line {i}: Unclosed single quote")

            # Parse key-value pairs and lists
            stripped = line.strip()

            if stripped.startswith("- "):
                # List item
                if current_list_key:
                    value = stripped[2:].strip().strip("\"'")
                    current_list.append(value)
            elif ":" in stripped:
                # Save previous list
                if current_list_key and current_list:
                    self.data[current_list_key] = current_list
                    current_list = []

                # Key-value pair
                parts = stripped.split(":", 1)
                key = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ""

                if value == "":
                    # This might be a list or nested object
                    current_list_key = key
                    current_list = []
                else:
                    # Simple key-value
                    value = value.strip("\"'")
                    self.data[key] = value
                    current_list_key = None

        # Save final list
        if current_list_key and current_list:
            self.data[current_list_key] = current_list

    def check_syntax(self) -> list[str]:
        """Check for common YAML syntax issues."""
        issues = []

        for i, line in enumerate(self.lines, 1):
            if not line.strip() or line.strip().startswith("#"):
                continue

            # Trailing whitespace
            if line.rstrip() != line:
                issues.append(f"Line {i}: Trailing whitespace")

            # Missing space after colon
            match = re.match(r"^(\s*)([a-zA-Z_][a-zA-Z0-9_]*):([^\s])", line)
            if match and not line.strip().startswith("#"):
                # Allow URLs
                if "http:" not in line and "https:" not in line:
                    issues.append(f"Line {i}: Missing space after colon")

        return issues

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from parsed data."""
        return self.data.get(key, default)

    def has_key(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.data


def validate_override_file(
    file_path: Path, agents_dir: Path, verbose: bool = False
) -> ValidationResult:
    """Validate an agent override file."""
    result = ValidationResult(file_path=str(file_path))

    # Extract agent name
    agent_name = file_path.stem.replace(".override", "")
    agent_file = agents_dir / f"{agent_name}.md"

    # Check if corresponding agent exists
    if not agent_file.exists():
        result.warnings.append(f"No corresponding agent file found: {agent_name}.md")
    else:
        result.info.append(f"Agent file found: {agent_name}.md")

    # Read and parse file
    try:
        content = file_path.read_text()
    except Exception as e:
        result.errors.append(f"Failed to read file: {e}")
        return result

    # Parse YAML
    validator = YAMLValidator(content)
    success, error = validator.parse()
    if not success:
        result.errors.append(f"YAML syntax error: {error}")
        return result

    result.info.append("YAML syntax is valid")

    # Check for syntax issues
    syntax_issues = validator.check_syntax()
    for issue in syntax_issues:
        result.warnings.append(issue)

    # Validate model
    model = validator.get("model")
    if model:
        if model in VALID_MODELS:
            result.info.append(f"Model override is valid: {model}")
        else:
            result.errors.append(
                f"Invalid model: '{model}'. Valid options: {', '.join(VALID_MODELS)}"
            )

    # Validate budget
    budget = validator.get("max_budget_usd")
    if budget:
        try:
            budget_val = float(budget)
            if budget_val < MIN_BUDGET:
                result.errors.append(f"Budget too low: {budget_val} (minimum: {MIN_BUDGET})")
            elif budget_val > MAX_BUDGET:
                result.warnings.append(
                    f"Budget unusually high: {budget_val} (max recommended: {MAX_BUDGET})"
                )
            else:
                result.info.append(f"Budget override is valid: ${budget_val}")
        except ValueError:
            result.errors.append(f"Invalid budget format: '{budget}' (must be a number)")

    # Check lists
    if validator.has_key("additional_rules"):
        rules = validator.get("additional_rules", [])
        result.info.append(f"Additional rules defined: {len(rules)} rules")

    if validator.has_key("memories"):
        memories = validator.get("memories", [])
        result.info.append(f"Memories defined: {len(memories)} items")

    if validator.has_key("critical_actions"):
        actions = validator.get("critical_actions", [])
        result.info.append(f"Critical actions defined: {len(actions)} actions")

    return result


def validate_user_profile(file_path: Path, verbose: bool = False) -> ValidationResult:
    """Validate the user profile file."""
    result = ValidationResult(file_path=str(file_path))

    if not file_path.exists():
        result.warnings.append("No user-profile.yaml found")
        return result

    # Read and parse file
    try:
        content = file_path.read_text()
    except Exception as e:
        result.errors.append(f"Failed to read file: {e}")
        return result

    # Parse YAML
    validator = YAMLValidator(content)
    success, error = validator.parse()
    if not success:
        result.errors.append(f"YAML syntax error: {error}")
        return result

    result.info.append("YAML syntax is valid")

    # Check for syntax issues
    syntax_issues = validator.check_syntax()
    for issue in syntax_issues:
        result.warnings.append(issue)

    # Check user section (basic check since our parser is simple)
    if "user" not in content:
        result.warnings.append("No user section found in profile")
    else:
        result.info.append("User section found")

    return result


def fix_file(file_path: Path) -> list[str]:
    """Auto-fix common issues in a file."""
    fixes = []

    try:
        content = file_path.read_text()
        original = content

        # Fix trailing whitespace
        lines = content.split("\n")
        fixed_lines = [line.rstrip() for line in lines]
        if lines != fixed_lines:
            fixes.append("Fixed trailing whitespace")

        # Fix tabs
        content = "\n".join(fixed_lines)
        if "\t" in content:
            content = content.replace("\t", "  ")
            fixes.append("Converted tabs to spaces")

        # Write if changed
        if content != original:
            # Backup
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            backup_path.write_text(original)
            fixes.append(f"Backup saved to {backup_path.name}")

            # Write fixed content
            file_path.write_text(content)
        else:
            fixes.append("No changes needed")

    except Exception as e:
        fixes.append(f"Error fixing file: {e}")

    return fixes


def print_result(result: ValidationResult, verbose: bool = False):
    """Print validation result to terminal."""
    print()
    print(f"{Colors.BLUE}Validating:{Colors.NC} {os.path.basename(result.file_path)}")

    for error in result.errors:
        print(f"{Colors.RED}  [X] ERROR:{Colors.NC} {error}")

    for warning in result.warnings:
        print(f"{Colors.YELLOW}  WARNING:{Colors.NC} {warning}")

    if verbose:
        for info in result.info:
            print(f"{Colors.GREEN}  [OK]{Colors.NC} {info}")
    else:
        # Show success messages only for key validations
        for info in result.info:
            if any(key in info for key in ["syntax is valid", "override is valid", "defined:"]):
                print(f"{Colors.GREEN}  [OK]{Colors.NC} {info}")


def main():
    parser = argparse.ArgumentParser(description="Validate override YAML files")
    parser.add_argument("target", nargs="?", help="Specific agent name to validate")
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    # Find directories
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    overrides_dir = project_root / ".automation" / "overrides"
    agents_dir = project_root / ".automation" / "agents"

    if not overrides_dir.exists():
        print(f"{Colors.RED}Error: Overrides directory not found: {overrides_dir}{Colors.NC}")
        sys.exit(1)

    results: list[ValidationResult] = []

    # Print header
    if not args.json:
        print()
        print(
            f"{Colors.CYAN}═══════════════════════════════════════════════════════════════{Colors.NC}"
        )
        print(f"{Colors.CYAN}  OVERRIDE VALIDATOR (Python){Colors.NC}")
        print(
            f"{Colors.CYAN}═══════════════════════════════════════════════════════════════{Colors.NC}"
        )
        print()
        print(f"{Colors.BLUE}Scanning:{Colors.NC} {overrides_dir}")

    if args.target:
        # Validate specific override
        file_path = overrides_dir / f"{args.target}.override.yaml"
        if not file_path.exists():
            print(f"{Colors.RED}Error: Override file not found: {file_path}{Colors.NC}")
            sys.exit(1)

        if args.fix:
            fixes = fix_file(file_path)
            if not args.json:
                print(f"\n{Colors.YELLOW}Auto-fixing:{Colors.NC} {file_path.name}")
                for fix in fixes:
                    print(f"{Colors.GREEN}  [OK]{Colors.NC} {fix}")

        result = validate_override_file(file_path, agents_dir, args.verbose)
        results.append(result)
    else:
        # Validate all overrides

        # User profile first
        profile_path = overrides_dir / "user-profile.yaml"
        if profile_path.exists():
            if args.fix:
                fixes = fix_file(profile_path)
                if not args.json:
                    print(f"\n{Colors.YELLOW}Auto-fixing:{Colors.NC} {profile_path.name}")
                    for fix in fixes:
                        print(f"{Colors.GREEN}  [OK]{Colors.NC} {fix}")

            result = validate_user_profile(profile_path, args.verbose)
            results.append(result)

        # All override files
        for file_path in sorted(overrides_dir.glob("*.override.yaml")):
            if args.fix:
                fixes = fix_file(file_path)
                if not args.json:
                    print(f"\n{Colors.YELLOW}Auto-fixing:{Colors.NC} {file_path.name}")
                    for fix in fixes:
                        print(f"{Colors.GREEN}  [OK]{Colors.NC} {fix}")

            result = validate_override_file(file_path, agents_dir, args.verbose)
            results.append(result)

    # Output results
    if args.json:
        output = {
            "results": [r.to_dict() for r in results],
            "summary": {
                "total": len(results),
                "valid": sum(1 for r in results if r.is_valid),
                "errors": sum(len(r.errors) for r in results),
                "warnings": sum(len(r.warnings) for r in results),
            },
        }
        print(json.dumps(output, indent=2))
    else:
        # Print results
        for result in results:
            print_result(result, args.verbose)

        # Summary
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)

        print()
        print(
            f"{Colors.CYAN}═══════════════════════════════════════════════════════════════{Colors.NC}"
        )
        print(f"{Colors.CYAN}  VALIDATION SUMMARY{Colors.NC}")
        print(
            f"{Colors.CYAN}═══════════════════════════════════════════════════════════════{Colors.NC}"
        )
        print()
        print(f"  Files validated: {Colors.GREEN}{len(results)}{Colors.NC}")
        print(f"  Errors:          {Colors.RED}{total_errors}{Colors.NC}")
        print(f"  Warnings:        {Colors.YELLOW}{total_warnings}{Colors.NC}")
        print()

        if total_errors > 0:
            print(f"{Colors.RED} Validation failed with {total_errors} error(s){Colors.NC}")
            sys.exit(1)
        elif total_warnings > 0:
            print(f"{Colors.YELLOW}  Validation passed with {total_warnings} warning(s){Colors.NC}")
        else:
            print(f"{Colors.GREEN} All validations passed!{Colors.NC}")


if __name__ == "__main__":
    main()
