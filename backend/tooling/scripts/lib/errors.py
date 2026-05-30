#!/usr/bin/env python3
"""
Error Handling - Enhanced error messages for better debugging.

Provides user-friendly error messages with context and suggested fixes.

Usage:
    from lib.errors import CostTrackingError, handle_error

    try:
        # ... code ...
    except Exception as e:
        handle_error(e, context="loading session")
"""

import json
import sys
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ErrorCode(Enum):
    """Error codes for categorizing issues."""

    # Configuration errors (1xx)
    CONFIG_NOT_FOUND = 101
    CONFIG_PARSE_ERROR = 102
    CONFIG_INVALID_VALUE = 103

    # File/storage errors (2xx)
    FILE_NOT_FOUND = 201
    FILE_READ_ERROR = 202
    FILE_WRITE_ERROR = 203
    DIRECTORY_NOT_FOUND = 204
    PERMISSION_DENIED = 205

    # Session errors (3xx)
    SESSION_NOT_FOUND = 301
    SESSION_CORRUPTED = 302
    SESSION_SAVE_FAILED = 303

    # Budget errors (4xx)
    BUDGET_EXCEEDED = 401
    BUDGET_INVALID = 402

    # Calculation errors (5xx)
    UNKNOWN_MODEL = 501
    INVALID_TOKENS = 502
    CALCULATION_ERROR = 503

    # General errors (9xx)
    UNKNOWN_ERROR = 999


@dataclass
class ErrorContext:
    """Context information for an error."""

    operation: str
    file_path: Optional[Path] = None
    model: Optional[str] = None
    agent: Optional[str] = None
    tokens: Optional[dict[str, int]] = None
    budget: Optional[float] = None
    additional: Optional[dict[str, Any]] = None


class CostTrackingError(Exception):
    """Base exception for cost tracking errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        context: Optional[ErrorContext] = None,
        suggestion: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        self.message = message
        self.code = code
        self.context = context
        self.suggestion = suggestion
        self.cause = cause
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the error message with context."""
        parts = [f"[{self.code.name}] {self.message}"]

        if self.context:
            parts.append(f"\n  Operation: {self.context.operation}")
            if self.context.file_path:
                parts.append(f"  File: {self.context.file_path}")
            if self.context.model:
                parts.append(f"  Model: {self.context.model}")
            if self.context.agent:
                parts.append(f"  Agent: {self.context.agent}")

        if self.suggestion:
            parts.append(f"\n  [TIP] Suggestion: {self.suggestion}")

        if self.cause:
            parts.append(f"\n  Caused by: {type(self.cause).__name__}: {self.cause}")

        return "\n".join(parts)


class ConfigurationError(CostTrackingError):
    """Configuration-related errors."""

    pass


class SessionError(CostTrackingError):
    """Session management errors."""

    pass


class BudgetError(CostTrackingError):
    """Budget-related errors."""

    pass


class CalculationError(CostTrackingError):
    """Calculation-related errors."""

    pass


# Error message templates with suggestions
ERROR_MESSAGES = {
    ErrorCode.CONFIG_NOT_FOUND: {
        "message": "Configuration file not found",
        "suggestion": "Create a config.json file or set environment variables. Run 'python validate_setup.py' for guidance.",
    },
    ErrorCode.CONFIG_PARSE_ERROR: {
        "message": "Failed to parse configuration file",
        "suggestion": "Check that your config.json is valid JSON. Use a JSON validator to find syntax errors.",
    },
    ErrorCode.CONFIG_INVALID_VALUE: {
        "message": "Invalid configuration value",
        "suggestion": "Check the configuration documentation for valid values and ranges.",
    },
    ErrorCode.FILE_NOT_FOUND: {
        "message": "Required file not found",
        "suggestion": "Ensure the file exists and the path is correct. Run 'python validate_setup.py' to check your setup.",
    },
    ErrorCode.FILE_READ_ERROR: {
        "message": "Failed to read file",
        "suggestion": "Check file permissions and ensure the file is not corrupted or locked by another process.",
    },
    ErrorCode.FILE_WRITE_ERROR: {
        "message": "Failed to write file",
        "suggestion": "Check directory permissions and ensure there's sufficient disk space.",
    },
    ErrorCode.DIRECTORY_NOT_FOUND: {
        "message": "Required directory not found",
        "suggestion": "The directory will be created automatically. If this persists, check your file system permissions.",
    },
    ErrorCode.PERMISSION_DENIED: {
        "message": "Permission denied",
        "suggestion": "Check file/directory permissions. On Unix, try: chmod 755 <path>",
    },
    ErrorCode.SESSION_NOT_FOUND: {
        "message": "Session not found",
        "suggestion": "The session may have expired or been deleted. Start a new tracking session.",
    },
    ErrorCode.SESSION_CORRUPTED: {
        "message": "Session data is corrupted",
        "suggestion": "The session file may be damaged. Remove the corrupted file and start a new session.",
    },
    ErrorCode.SESSION_SAVE_FAILED: {
        "message": "Failed to save session",
        "suggestion": "Check disk space and permissions. The session data is preserved in memory.",
    },
    ErrorCode.BUDGET_EXCEEDED: {
        "message": "Budget limit exceeded",
        "suggestion": "Increase the budget limit or optimize token usage. Consider using a cheaper model.",
    },
    ErrorCode.BUDGET_INVALID: {
        "message": "Invalid budget value",
        "suggestion": "Budget must be a positive number. Set to 0 for no limit.",
    },
    ErrorCode.UNKNOWN_MODEL: {
        "message": "Unknown model specified",
        "suggestion": "Use a supported model: opus, sonnet, haiku. Defaulting to sonnet pricing.",
    },
    ErrorCode.INVALID_TOKENS: {
        "message": "Invalid token count",
        "suggestion": "Token counts must be non-negative integers.",
    },
    ErrorCode.CALCULATION_ERROR: {
        "message": "Error calculating cost",
        "suggestion": "Check input values. Ensure token counts are valid numbers.",
    },
}


def create_error(
    code: ErrorCode,
    context: Optional[ErrorContext] = None,
    custom_message: Optional[str] = None,
    cause: Optional[Exception] = None,
) -> CostTrackingError:
    """Create an error with appropriate type and message."""
    template = ERROR_MESSAGES.get(code, {"message": "Unknown error", "suggestion": None})
    message = custom_message or template["message"]
    suggestion = template.get("suggestion")

    # Select appropriate error class
    if code.value < 200:
        error_class = ConfigurationError
    elif code.value < 400:
        error_class = SessionError
    elif code.value < 500:
        error_class = BudgetError
    elif code.value < 600:
        error_class = CalculationError
    else:
        error_class = CostTrackingError

    return error_class(
        message=message, code=code, context=context, suggestion=suggestion, cause=cause
    )


def format_error_for_user(error: Exception, verbose: bool = False) -> str:
    """Format an error for user-friendly display."""
    lines = []

    # Header
    lines.append("━" * 60)
    lines.append("[ERROR] Error Occurred")
    lines.append("━" * 60)

    if isinstance(error, CostTrackingError):
        lines.append(f"\n{error.format_message()}")
    else:
        lines.append(f"\n{type(error).__name__}: {error}")

    if verbose:
        lines.append("\n[STACK TRACE]:")
        lines.append(traceback.format_exc())

    lines.append("\n" + "━" * 60)

    return "\n".join(lines)


def handle_error(
    error: Exception,
    context: str = "unknown operation",
    exit_on_error: bool = False,
    verbose: bool = False,
) -> None:
    """
    Handle an error with user-friendly output.

    Args:
        error: The exception that occurred
        context: Description of what was being done
        exit_on_error: Whether to exit the program
        verbose: Whether to show stack trace
    """
    # Create context if not a CostTrackingError
    if not isinstance(error, CostTrackingError):
        error_context = ErrorContext(operation=context)

        # Try to determine error type
        if isinstance(error, FileNotFoundError):
            error = create_error(ErrorCode.FILE_NOT_FOUND, context=error_context, cause=error)
        elif isinstance(error, PermissionError):
            error = create_error(ErrorCode.PERMISSION_DENIED, context=error_context, cause=error)
        elif isinstance(error, json.JSONDecodeError):
            error = create_error(ErrorCode.CONFIG_PARSE_ERROR, context=error_context, cause=error)

    # Output error
    print(format_error_for_user(error, verbose=verbose), file=sys.stderr)

    if exit_on_error:
        sys.exit(1)


def wrap_errors(operation: str):
    """
    Decorator to wrap function errors with context.

    Usage:
        @wrap_errors("loading session")
        def load_session(path):
            ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except CostTrackingError:
                raise
            except Exception as e:
                context = ErrorContext(operation=operation)
                raise create_error(
                    ErrorCode.UNKNOWN_ERROR, context=context, custom_message=str(e), cause=e
                ) from e

        return wrapper

    return decorator


class ErrorReporter:
    """Collect and report multiple errors."""

    def __init__(self):
        self.errors: list = []
        self.warnings: list = []

    def add_error(self, error: Exception, context: str = ""):
        """Add an error to the collection."""
        self.errors.append((error, context))

    def add_warning(self, message: str, context: str = ""):
        """Add a warning to the collection."""
        self.warnings.append((message, context))

    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were recorded."""
        return len(self.warnings) > 0

    def format_report(self) -> str:
        """Format all errors and warnings as a report."""
        lines = []

        if self.errors:
            lines.append(f"\n[ERROR] {len(self.errors)} Error(s):")
            for i, (error, context) in enumerate(self.errors, 1):
                lines.append(f"  {i}. [{context}] {error}")

        if self.warnings:
            lines.append(f"\n[WARNING] {len(self.warnings)} Warning(s):")
            for i, (message, context) in enumerate(self.warnings, 1):
                lines.append(f"  {i}. [{context}] {message}")

        return "\n".join(lines)

    def print_report(self):
        """Print the error report."""
        if self.errors or self.warnings:
            print(self.format_report(), file=sys.stderr)

    def clear(self):
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()


# Logging helpers
def log_debug(message: str, **kwargs):
    """Log a debug message (only in verbose mode)."""
    if _verbose_mode:
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        print(f"[DEBUG] {message} {extra}", file=sys.stderr)


def log_info(message: str):
    """Log an info message."""
    print(f"[INFO] {message}")


def log_warning(message: str):
    """Log a warning message."""
    print(f"[WARNING] {message}", file=sys.stderr)


def log_error(message: str):
    """Log an error message."""
    print(f"[ERROR] {message}", file=sys.stderr)


def log_success(message: str):
    """Log a success message."""
    print(f"[OK] {message}")


# Verbose mode flag
_verbose_mode = False


def set_verbose(enabled: bool):
    """Enable or disable verbose mode."""
    global _verbose_mode
    _verbose_mode = enabled


def is_verbose() -> bool:
    """Check if verbose mode is enabled."""
    return _verbose_mode


if __name__ == "__main__":
    # Demo error handling
    print("Error Handling Demo\n")

    # Create and display different error types
    errors = [
        create_error(
            ErrorCode.BUDGET_EXCEEDED,
            context=ErrorContext(
                operation="logging usage", model="opus", agent="DEV", budget=15.00
            ),
        ),
        create_error(
            ErrorCode.SESSION_CORRUPTED,
            context=ErrorContext(
                operation="loading session", file_path=Path("/path/to/session.json")
            ),
        ),
        create_error(
            ErrorCode.UNKNOWN_MODEL,
            context=ErrorContext(
                operation="calculating cost",
                model="gpt-4",  # Wrong model
            ),
        ),
    ]

    for error in errors:
        print(format_error_for_user(error))
        print()
