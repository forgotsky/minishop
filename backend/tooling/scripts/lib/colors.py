#!/usr/bin/env python3
"""
Shared Colors Module for Devflow.

Provides consistent ANSI color codes for terminal output across all scripts.

Usage:
    from lib.colors import Colors

    print(f"{Colors.GREEN}Success!{Colors.RESET}")
    print(f"{Colors.BOLD_RED}Error!{Colors.RESET}")
"""

import os
import sys


def _supports_color() -> bool:
    """Check if the terminal supports color output."""
    # Check for explicit NO_COLOR environment variable
    if os.getenv("NO_COLOR"):
        return False

    # Check for explicit FORCE_COLOR
    if os.getenv("FORCE_COLOR"):
        return True

    # Check if output is a TTY
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    # Windows-specific handling
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            # Enable ANSI escape sequences on Windows 10+
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False

    return True


class Colors:
    """ANSI color codes for terminal output."""

    _USE_COLORS = _supports_color()

    # Reset
    RESET = "\033[0m" if _USE_COLORS else ""
    END = RESET  # Alias for compatibility

    # Regular colors
    BLACK = "\033[30m" if _USE_COLORS else ""
    RED = "\033[31m" if _USE_COLORS else ""
    GREEN = "\033[32m" if _USE_COLORS else ""
    YELLOW = "\033[33m" if _USE_COLORS else ""
    BLUE = "\033[34m" if _USE_COLORS else ""
    MAGENTA = "\033[35m" if _USE_COLORS else ""
    CYAN = "\033[36m" if _USE_COLORS else ""
    WHITE = "\033[37m" if _USE_COLORS else ""

    # Bold colors
    BOLD = "\033[1m" if _USE_COLORS else ""
    BOLD_RED = "\033[1;31m" if _USE_COLORS else ""
    BOLD_GREEN = "\033[1;32m" if _USE_COLORS else ""
    BOLD_YELLOW = "\033[1;33m" if _USE_COLORS else ""
    BOLD_BLUE = "\033[1;34m" if _USE_COLORS else ""
    BOLD_MAGENTA = "\033[1;35m" if _USE_COLORS else ""
    BOLD_CYAN = "\033[1;36m" if _USE_COLORS else ""
    BOLD_WHITE = "\033[1;37m" if _USE_COLORS else ""

    # Background colors
    BG_RED = "\033[41m" if _USE_COLORS else ""
    BG_GREEN = "\033[42m" if _USE_COLORS else ""
    BG_YELLOW = "\033[43m" if _USE_COLORS else ""
    BG_BLUE = "\033[44m" if _USE_COLORS else ""

    # Styles
    DIM = "\033[2m" if _USE_COLORS else ""
    UNDERLINE = "\033[4m" if _USE_COLORS else ""

    # Common aliases used across codebase
    HEADER = BOLD_MAGENTA
    OKBLUE = BLUE
    OKCYAN = CYAN
    OKGREEN = GREEN
    WARNING = YELLOW
    FAIL = RED
    ENDC = RESET
    NC = RESET  # No Color alias

    @staticmethod
    def strip(text: str) -> str:
        """Remove ANSI codes from text."""
        import re

        return re.sub(r"\033\[[0-9;]*m", "", text)

    @classmethod
    def enabled(cls) -> bool:
        """Check if colors are enabled."""
        return cls._USE_COLORS
