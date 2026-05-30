#!/usr/bin/env python3
"""
Cross-Platform Documentation Generator

Automatically detects the operating system and runs the appropriate script.
Works on Windows, macOS, and Linux.

Usage:
    python new-doc.py --type <type> --name <name> [--author <name>]

Examples:
    python new-doc.py --type guide --name "setup-guide"
    python new-doc.py --type spec --name "epic-4" --author "SM Agent"
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from lib.platform import get_platform


def run_windows(args):
    """Run PowerShell script on Windows."""
    script = SCRIPT_DIR / "new-doc.ps1"

    if not script.exists():
        print(f"Error: PowerShell script not found: {script}")
        return 1

    # Convert args to PowerShell format
    ps_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            # Convert --type to -Type
            param_name = arg[2:].title()
            ps_args.append(f"-{param_name}")
        else:
            ps_args.append(arg)
        i += 1

    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)] + ps_args
    return subprocess.call(cmd)


def run_unix(args):
    """Run shell script on macOS/Linux."""
    script = SCRIPT_DIR / "new-doc.sh"

    if not script.exists():
        print(f"Error: Shell script not found: {script}")
        return 1

    # Ensure script is executable
    os.chmod(script, 0o755)

    cmd = [str(script)] + args
    return subprocess.call(cmd)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nDetected platform:", get_platform())
        return 1

    args = sys.argv[1:]
    platform = get_platform()

    print(f"Platform: {platform}")
    print()

    if platform == "windows":
        return run_windows(args)
    else:
        return run_unix(args)


if __name__ == "__main__":
    sys.exit(main())
