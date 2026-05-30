#!/usr/bin/env python3
"""
Shared Platform Detection Module for Devflow.

Provides consistent platform detection across all scripts.

Usage:
    from lib.platform import get_platform, IS_WINDOWS, IS_MACOS, IS_LINUX
"""

import sys

# Platform constants
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def get_platform() -> str:
    """
    Detect the current platform.

    Returns:
        str: One of 'windows', 'macos', or 'linux'
    """
    if IS_WINDOWS:
        return "windows"
    elif IS_MACOS:
        return "macos"
    else:
        return "linux"


def get_shell() -> str:
    """
    Get the appropriate shell for the current platform.

    Returns:
        str: Shell command ('powershell' on Windows, 'bash' otherwise)
    """
    if IS_WINDOWS:
        return "powershell"
    return "bash"


def get_path_separator() -> str:
    """
    Get the path separator for the current platform.

    Returns:
        str: Path separator ('\\' on Windows, '/' otherwise)
    """
    if IS_WINDOWS:
        return "\\"
    return "/"
