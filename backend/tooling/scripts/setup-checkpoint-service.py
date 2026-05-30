#!/usr/bin/env python3
"""
Cross-Platform Checkpoint Service Setup

Automatically detects the operating system and runs the appropriate setup:
- Windows: Task Scheduler
- macOS: LaunchAgent
- Linux: systemd (if available) or cron

Usage:
    python setup-checkpoint-service.py [install|uninstall|status]

Examples:
    python setup-checkpoint-service.py install
    python setup-checkpoint-service.py status
    python setup-checkpoint-service.py uninstall
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from lib.platform import get_platform


def run_windows(action):
    """Run PowerShell script on Windows."""
    script = SCRIPT_DIR / "setup-checkpoint-service.ps1"

    if not script.exists():
        print(f"Error: PowerShell script not found: {script}")
        return 1

    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Action", action]
    return subprocess.call(cmd)


def run_unix(action):
    """Run shell script on macOS/Linux."""
    script = SCRIPT_DIR / "setup-checkpoint-service.sh"

    if not script.exists():
        print(f"Error: Shell script not found: {script}")
        return 1

    # Ensure script is executable
    os.chmod(script, 0o755)

    cmd = [str(script), action]
    return subprocess.call(cmd)


def main():
    action = "install"
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()

    if action not in ["install", "uninstall", "status"]:
        print(__doc__)
        print("\nDetected platform:", get_platform())
        return 1

    platform = get_platform()

    print(f"Platform: {platform}")
    print(f"Action: {action}")
    print()

    if platform == "windows":
        return run_windows(action)
    else:
        return run_unix(action)


if __name__ == "__main__":
    sys.exit(main())
