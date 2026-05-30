#!/usr/bin/env python3
"""
Cost Configuration - Settings for cost tracking system.

Loads configuration from environment variables and config files.

Usage:
    from lib.cost_config import CostConfig, get_config

    config = get_config()
    print(config.budget_limit)
    print(config.currency_rates)
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Default values
DEFAULT_BUDGET_LIMIT = 15.00
DEFAULT_WARNING_PERCENT = 75
DEFAULT_CRITICAL_PERCENT = 90
DEFAULT_AUTO_STOP = True

# Subscription defaults (monthly token limits)
# Set to 0 to disable subscription tracking
DEFAULT_SUBSCRIPTION_TOKEN_LIMIT = 0  # No default limit - user must configure
DEFAULT_SUBSCRIPTION_BILLING_PERIOD_DAYS = 30

# Common subscription plan presets (tokens per month)
# Based on typical Anthropic API plans as of December 2025
SUBSCRIPTION_PLANS = {
    "free": {
        "token_limit": 100_000,  # 100K tokens/month
        "description": "Free tier / Trial",
    },
    "developer": {
        "token_limit": 1_000_000,  # 1M tokens/month
        "description": "Developer plan",
    },
    "pro": {
        "token_limit": 5_000_000,  # 5M tokens/month
        "description": "Pro / Team plan",
    },
    "scale": {
        "token_limit": 20_000_000,  # 20M tokens/month
        "description": "Scale plan",
    },
    "enterprise": {
        "token_limit": 100_000_000,  # 100M tokens/month
        "description": "Enterprise plan",
    },
}

DEFAULT_CURRENCY_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "BRL": 6.10,
    "CAD": 1.36,
    "AUD": 1.53,
    "JPY": 149.50,
}

DEFAULT_DISPLAY_CURRENCIES = ["USD", "EUR", "GBP", "BRL"]


@dataclass
class CostConfig:
    """Cost tracking configuration."""

    # Budget settings
    budget_context: float = 3.00
    budget_dev: float = 15.00
    budget_review: float = 5.00

    # Alert thresholds
    warning_percent: int = DEFAULT_WARNING_PERCENT
    critical_percent: int = DEFAULT_CRITICAL_PERCENT
    auto_stop: bool = DEFAULT_AUTO_STOP

    # Subscription settings (for tracking usage against API plan limits)
    subscription_token_limit: int = DEFAULT_SUBSCRIPTION_TOKEN_LIMIT
    subscription_billing_period_days: int = DEFAULT_SUBSCRIPTION_BILLING_PERIOD_DAYS
    subscription_plan: str = (
        ""  # Plan name if using preset (free, developer, pro, scale, enterprise)
    )

    # Currency settings
    display_currency: str = "USD"
    currency_rates: dict[str, float] = field(default_factory=lambda: DEFAULT_CURRENCY_RATES.copy())
    display_currencies: list[str] = field(default_factory=lambda: DEFAULT_DISPLAY_CURRENCIES.copy())

    @classmethod
    def from_env(cls) -> "CostConfig":
        """Load configuration from environment variables."""
        config = cls()

        def _safe_float(env_var: str, default: float) -> float:
            """Safely convert env var to float, returning default on failure."""
            value = os.getenv(env_var)
            if not value:
                return default
            try:
                return float(value)
            except ValueError:
                print(f"Warning: Invalid float value for {env_var}: '{value}', using default")
                return default

        def _safe_int(env_var: str, default: int) -> int:
            """Safely convert env var to int, returning default on failure."""
            value = os.getenv(env_var)
            if not value:
                return default
            try:
                return int(value)
            except ValueError:
                print(f"Warning: Invalid int value for {env_var}: '{value}', using default")
                return default

        # Budget limits
        if os.getenv("MAX_BUDGET_CONTEXT"):
            config.budget_context = _safe_float("MAX_BUDGET_CONTEXT", config.budget_context)
        if os.getenv("MAX_BUDGET_DEV"):
            config.budget_dev = _safe_float("MAX_BUDGET_DEV", config.budget_dev)
        if os.getenv("MAX_BUDGET_REVIEW"):
            config.budget_review = _safe_float("MAX_BUDGET_REVIEW", config.budget_review)

        # Alert thresholds
        if os.getenv("COST_WARNING_PERCENT"):
            config.warning_percent = _safe_int("COST_WARNING_PERCENT", config.warning_percent)
        if os.getenv("COST_CRITICAL_PERCENT"):
            config.critical_percent = _safe_int("COST_CRITICAL_PERCENT", config.critical_percent)
        if os.getenv("COST_AUTO_STOP"):
            config.auto_stop = os.getenv("COST_AUTO_STOP").lower() in ("true", "1", "yes")

        # Subscription settings
        # Check for plan preset first (e.g., SUBSCRIPTION_PLAN=pro)
        if os.getenv("SUBSCRIPTION_PLAN"):
            plan_name = os.getenv("SUBSCRIPTION_PLAN").lower()
            if plan_name in SUBSCRIPTION_PLANS:
                config.subscription_plan = plan_name
                config.subscription_token_limit = SUBSCRIPTION_PLANS[plan_name]["token_limit"]
            else:
                print(
                    f"Warning: Unknown subscription plan '{plan_name}'. "
                    f"Valid plans: {', '.join(SUBSCRIPTION_PLANS.keys())}"
                )

        # Direct token limit overrides plan preset
        if os.getenv("SUBSCRIPTION_TOKEN_LIMIT"):
            config.subscription_token_limit = _safe_int(
                "SUBSCRIPTION_TOKEN_LIMIT", config.subscription_token_limit
            )
        if os.getenv("SUBSCRIPTION_BILLING_PERIOD_DAYS"):
            config.subscription_billing_period_days = _safe_int(
                "SUBSCRIPTION_BILLING_PERIOD_DAYS", config.subscription_billing_period_days
            )

        # Currency settings
        if os.getenv("COST_DISPLAY_CURRENCY"):
            config.display_currency = os.getenv("COST_DISPLAY_CURRENCY")

        # Currency rates from environment
        if os.getenv("CURRENCY_RATE_EUR"):
            config.currency_rates["EUR"] = _safe_float(
                "CURRENCY_RATE_EUR", config.currency_rates["EUR"]
            )
        if os.getenv("CURRENCY_RATE_GBP"):
            config.currency_rates["GBP"] = _safe_float(
                "CURRENCY_RATE_GBP", config.currency_rates["GBP"]
            )
        if os.getenv("CURRENCY_RATE_BRL"):
            config.currency_rates["BRL"] = _safe_float(
                "CURRENCY_RATE_BRL", config.currency_rates["BRL"]
            )

        return config

    @classmethod
    def from_file(cls, config_path: Path) -> "CostConfig":
        """Load configuration from JSON file."""
        config = cls()

        if not config_path.exists():
            return config

        try:
            with open(config_path) as f:
                data = json.load(f)

            # Budget limits
            if "budget_context" in data:
                config.budget_context = float(data["budget_context"])
            if "budget_dev" in data:
                config.budget_dev = float(data["budget_dev"])
            if "budget_review" in data:
                config.budget_review = float(data["budget_review"])

            # Alert thresholds
            if "warning_percent" in data:
                config.warning_percent = int(data["warning_percent"])
            if "critical_percent" in data:
                config.critical_percent = int(data["critical_percent"])
            if "auto_stop" in data:
                config.auto_stop = bool(data["auto_stop"])

            # Subscription settings
            # Check for plan preset first
            if "subscription_plan" in data:
                plan_name = data["subscription_plan"].lower()
                if plan_name in SUBSCRIPTION_PLANS:
                    config.subscription_plan = plan_name
                    config.subscription_token_limit = SUBSCRIPTION_PLANS[plan_name]["token_limit"]
            # Direct token limit overrides plan preset
            if "subscription_token_limit" in data:
                config.subscription_token_limit = int(data["subscription_token_limit"])
            if "subscription_billing_period_days" in data:
                config.subscription_billing_period_days = int(
                    data["subscription_billing_period_days"]
                )

            # Currency settings
            if "display_currency" in data:
                config.display_currency = data["display_currency"]
            if "currency_rates" in data:
                config.currency_rates.update(data["currency_rates"])
            if "display_currencies" in data:
                config.display_currencies = data["display_currencies"]

        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in config file: {e}")
        except OSError as e:
            print(f"Warning: Could not read config file: {e}")

        return config

    def save(self, config_path: Path):
        """Save configuration to JSON file."""
        data = {
            "budget_context": self.budget_context,
            "budget_dev": self.budget_dev,
            "budget_review": self.budget_review,
            "warning_percent": self.warning_percent,
            "critical_percent": self.critical_percent,
            "auto_stop": self.auto_stop,
            "subscription_plan": self.subscription_plan,
            "subscription_token_limit": self.subscription_token_limit,
            "subscription_billing_period_days": self.subscription_billing_period_days,
            "display_currency": self.display_currency,
            "currency_rates": self.currency_rates,
            "display_currencies": self.display_currencies,
        }

        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_budget_for_phase(self, phase: str) -> float:
        """Get budget limit for a specific phase."""
        phase = phase.lower()
        if phase in ("context", "sm"):
            return self.budget_context
        elif phase in ("dev", "development", "implement"):
            return self.budget_dev
        elif phase in ("review", "qa"):
            return self.budget_review
        return self.budget_dev  # Default

    def get_thresholds(self) -> dict[str, float]:
        """Get budget thresholds as decimal values."""
        return {
            "warning": self.warning_percent / 100.0,
            "critical": self.critical_percent / 100.0,
            "stop": 1.0,
        }

    def set_subscription_plan(self, plan_name: str) -> bool:
        """
        Set subscription based on a plan preset.

        Args:
            plan_name: One of: free, developer, pro, scale, enterprise

        Returns:
            True if plan was set successfully, False otherwise.
        """
        plan_name = plan_name.lower()
        if plan_name not in SUBSCRIPTION_PLANS:
            return False

        self.subscription_plan = plan_name
        self.subscription_token_limit = SUBSCRIPTION_PLANS[plan_name]["token_limit"]
        return True

    def get_subscription_plan_info(self) -> dict:
        """Get information about the current subscription plan."""
        if self.subscription_plan and self.subscription_plan in SUBSCRIPTION_PLANS:
            plan = SUBSCRIPTION_PLANS[self.subscription_plan]
            return {
                "plan": self.subscription_plan,
                "description": plan["description"],
                "token_limit": self.subscription_token_limit,
                "billing_period_days": self.subscription_billing_period_days,
            }
        elif self.subscription_token_limit > 0:
            return {
                "plan": "custom",
                "description": "Custom token limit",
                "token_limit": self.subscription_token_limit,
                "billing_period_days": self.subscription_billing_period_days,
            }
        return {
            "plan": "none",
            "description": "Not configured",
            "token_limit": 0,
            "billing_period_days": self.subscription_billing_period_days,
        }

    @staticmethod
    def get_available_plans() -> dict:
        """Get all available subscription plan presets."""
        return SUBSCRIPTION_PLANS.copy()

    def auto_detect_plan(self, model: str = "sonnet") -> str:
        """
        Auto-detect subscription plan based on model usage.

        Args:
            model: The model being used (opus, sonnet, haiku)

        Returns:
            Detected plan name (free, developer, pro, scale, enterprise)
        """
        model_lower = model.lower()

        # If already configured, return existing plan
        if self.subscription_plan:
            return self.subscription_plan

        # Infer plan from model
        if "opus" in model_lower:
            # Opus users are typically on pro or higher
            detected = "pro"
        elif "sonnet" in model_lower:
            # Sonnet could be developer or higher
            detected = "developer"
        elif "haiku" in model_lower:
            # Haiku might be free tier
            detected = "free"
        else:
            detected = "developer"

        # Set and return the detected plan
        self.set_subscription_plan(detected)
        return detected

    def ensure_plan_configured(
        self, model: str = "sonnet", config_path: Optional[Path] = None
    ) -> str:
        """
        Ensure a subscription plan is configured, auto-detecting if needed.

        Args:
            model: The model being used for auto-detection
            config_path: Optional path to save config

        Returns:
            The configured or detected plan name
        """
        if self.subscription_plan and self.subscription_token_limit > 0:
            return self.subscription_plan

        plan = self.auto_detect_plan(model)

        # Save to config file if path provided
        if config_path:
            self.save(config_path)

        return plan


# Global configuration instance
_config: Optional[CostConfig] = None


def get_config() -> CostConfig:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        # Try to load from file first, then overlay with env vars
        config_file = Path(__file__).parent.parent.parent / ".automation" / "costs" / "config.json"
        if config_file.exists():
            _config = CostConfig.from_file(config_file)
        else:
            _config = CostConfig.from_env()
    return _config


def set_config(config: CostConfig):
    """Set the global configuration instance."""
    global _config
    _config = config


def reset_config():
    """Reset the global configuration instance."""
    global _config
    _config = None


if __name__ == "__main__":
    # Demo/test
    config = get_config()

    print("Cost Configuration")
    print("=" * 40)
    print(f"Budget - Context: ${config.budget_context:.2f}")
    print(f"Budget - Dev:     ${config.budget_dev:.2f}")
    print(f"Budget - Review:  ${config.budget_review:.2f}")
    print()
    print(f"Warning at:  {config.warning_percent}%")
    print(f"Critical at: {config.critical_percent}%")
    print(f"Auto-stop:   {config.auto_stop}")
    print()
    print("Subscription Settings:")
    if config.subscription_token_limit > 0:
        print(f"  Token Limit:    {config.subscription_token_limit:,} tokens")
        print(f"  Billing Period: {config.subscription_billing_period_days} days")
    else:
        print("  Not configured (set SUBSCRIPTION_TOKEN_LIMIT to enable)")
    print()
    print(f"Display Currency: {config.display_currency}")
    print(f"Display Currencies: {config.display_currencies}")
    print()
    print("Currency Rates:")
    for code, rate in config.currency_rates.items():
        print(f"  {code}: {rate}")
