#!/usr/bin/env python3
"""
Sync version across all project files from CHANGELOG.md.

This script extracts the latest version from CHANGELOG.md and updates
all version references throughout the project. Run this after updating
the changelog, or use the pre-commit hook to automate it.

Files updated:
    - package.json (version field) - FIRST, to include in commit
    - README.md (version block)
    - pyproject.toml (version field)
    - tooling/scripts/lib/__init__.py (__version__ variable)

Usage:
    python update_version.py                    # Sync all versions from CHANGELOG
    python update_version.py --check            # Check if versions are in sync
    python update_version.py --version 1.8.0    # Set specific version everywhere
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent


def get_changelog_version(changelog_path: Path) -> str | None:
    """Extract the latest version from CHANGELOG.md."""
    if not changelog_path.exists():
        print(f"Error: CHANGELOG.md not found at {changelog_path}")
        return None

    content = changelog_path.read_text()
    # Match version pattern like [1.6.0] - 2025-12-21
    match = re.search(r"## \[(\d+\.\d+\.\d+)\]", content)
    if match:
        return match.group(1)
    return None


def get_readme_version(readme_path: Path) -> str | None:
    """Extract the current version from README.md."""
    if not readme_path.exists():
        print(f"Error: README.md not found at {readme_path}")
        return None

    content = readme_path.read_text()
    match = re.search(r"\*\*Version\*\*: (\d+\.\d+\.\d+)", content)
    if match:
        return match.group(1)
    return None


def get_pyproject_version(pyproject_path: Path) -> str | None:
    """Extract the current version from pyproject.toml."""
    if not pyproject_path.exists():
        return None

    content = pyproject_path.read_text()
    match = re.search(r'version = "(\d+\.\d+\.\d+)"', content)
    if match:
        return match.group(1)
    return None


def get_init_version(init_path: Path) -> str | None:
    """Extract the current version from __init__.py."""
    if not init_path.exists():
        return None

    content = init_path.read_text()
    match = re.search(r'__version__ = "(\d+\.\d+\.\d+)"', content)
    if match:
        return match.group(1)
    return None


def get_package_json_version(package_path: Path) -> str | None:
    """Extract the current version from package.json."""
    if not package_path.exists():
        return None

    try:
        data = json.loads(package_path.read_text())
        return data.get("version")
    except json.JSONDecodeError:
        return None


def update_package_json_version(package_path: Path, version: str) -> bool:
    """Update the version in package.json."""
    if not package_path.exists():
        print(f"Error: package.json not found at {package_path}")
        return False

    try:
        content = package_path.read_text()
        data = json.loads(content)
        old_version = data.get("version")

        if old_version == version:
            print(f"package.json already at version {version}")
            return True

        data["version"] = version
        package_path.write_text(json.dumps(data, indent=2) + "\n")
        return True
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in package.json: {e}")
        return False


def update_readme_version(readme_path: Path, version: str) -> bool:
    """Update the version in README.md."""
    if not readme_path.exists():
        print(f"Error: README.md not found at {readme_path}")
        return False

    content = readme_path.read_text()
    today = date.today().isoformat()

    # Pattern to match the version block (with or without markers)
    pattern = r"(<!-- VERSION_START.*?-->.*?)?\*\*Version\*\*: \d+\.\d+\.\d+\n\*\*Status\*\*: ([^\n]+)\n\*\*Last Updated\*\*: \d{4}-\d{2}-\d{2}(.*?<!-- VERSION_END -->)?"

    # Check if markers exist
    if "<!-- VERSION_START" in content:
        replacement = f"""<!-- VERSION_START - Auto-updated by update_version.py -->
**Version**: {version}
**Status**: \\2
**Last Updated**: {today}
<!-- VERSION_END -->"""
    else:
        replacement = f"""**Version**: {version}
**Status**: \\2
**Last Updated**: {today}"""

    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count == 0:
        print("Error: Could not find version block in README.md")
        return False

    readme_path.write_text(new_content)
    return True


def update_pyproject_version(pyproject_path: Path, version: str) -> bool:
    """Update the version in pyproject.toml."""
    if not pyproject_path.exists():
        print(f"Warning: pyproject.toml not found at {pyproject_path}")
        return False

    content = pyproject_path.read_text()
    pattern = r'version = "\d+\.\d+\.\d+"'
    replacement = f'version = "{version}"'

    new_content, count = re.subn(pattern, replacement, content, count=1)

    if count == 0:
        print("Warning: Could not find version in pyproject.toml")
        return False

    pyproject_path.write_text(new_content)
    return True


def update_init_version(init_path: Path, version: str) -> bool:
    """Update the version in __init__.py."""
    if not init_path.exists():
        print(f"Warning: __init__.py not found at {init_path}")
        return False

    content = init_path.read_text()
    pattern = r'__version__ = "\d+\.\d+\.\d+"'
    replacement = f'__version__ = "{version}"'

    new_content, count = re.subn(pattern, replacement, content, count=1)

    if count == 0:
        print("Warning: Could not find __version__ in __init__.py")
        return False

    init_path.write_text(new_content)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Sync version across all project files from CHANGELOG.md"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if versions are in sync without updating",
    )
    parser.add_argument(
        "--version",
        type=str,
        help="Set a specific version instead of reading from CHANGELOG",
    )
    args = parser.parse_args()

    root = get_project_root()
    changelog_path = root / "CHANGELOG.md"
    package_path = root / "package.json"
    readme_path = root / "README.md"
    pyproject_path = root / "pyproject.toml"
    init_path = root / "tooling" / "scripts" / "lib" / "__init__.py"

    # Get versions from all sources
    changelog_version = get_changelog_version(changelog_path)
    package_version = get_package_json_version(package_path)
    readme_version = get_readme_version(readme_path)
    pyproject_version = get_pyproject_version(pyproject_path)
    init_version = get_init_version(init_path)

    if args.version:
        target_version = args.version
    elif changelog_version:
        target_version = changelog_version
    else:
        print("Error: Could not determine version from CHANGELOG.md")
        sys.exit(1)

    print(f"CHANGELOG version:   {changelog_version or 'not found'}")
    print(f"package.json:        {package_version or 'not found'}")
    print(f"README version:      {readme_version or 'not found'}")
    print(f"pyproject version:   {pyproject_version or 'not found'}")
    print(f"__init__ version:    {init_version or 'not found'}")
    print(f"Target version:      {target_version}")
    print()

    if args.check:
        all_match = all(
            v == target_version
            for v in [package_version, readme_version, pyproject_version, init_version]
            if v is not None
        )
        if all_match:
            print("[OK] All versions are in sync")
            sys.exit(0)
        else:
            print("[X] Versions are out of sync")
            sys.exit(1)

    # Update all files (package.json first so it's included in commit)
    success = True

    if update_package_json_version(package_path, target_version):
        print(f"[OK] Updated package.json to version {target_version}")
    else:
        print("[X] Failed to update package.json")
        success = False

    if update_readme_version(readme_path, target_version):
        print(f"[OK] Updated README.md to version {target_version}")
    else:
        print("[X] Failed to update README.md")
        success = False

    if update_pyproject_version(pyproject_path, target_version):
        print(f"[OK] Updated pyproject.toml to version {target_version}")
    else:
        print("[X] Failed to update pyproject.toml")
        success = False

    if update_init_version(init_path, target_version):
        print(f"[OK] Updated __init__.py to version {target_version}")
    else:
        print("[X] Failed to update __init__.py")
        success = False

    if success:
        print("\n[OK] All versions synced successfully!")
        print("  Don't forget to commit the changes.")
    else:
        print("\nSome updates failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
