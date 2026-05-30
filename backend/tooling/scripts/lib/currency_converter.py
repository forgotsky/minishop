#!/usr/bin/env python3
"""
Currency Converter - Multi-currency support for cost display.

Converts USD amounts to other currencies and formats them appropriately.

Usage:
    from lib.currency_converter import CurrencyConverter

    converter = CurrencyConverter()
    print(converter.format(1.77, "EUR"))  # €1.63
    print(converter.format_all(1.77))     # $1.77 | €1.63 | £1.40 | R$10.80

Exchange Rate Notice:
    Default exchange rates are STATIC approximations and will become stale.
    Last updated: December 2025

    For accurate conversions, you should:
    1. Use a config file with current rates:
       converter = CurrencyConverter(config_path=Path("currency_config.json"))

    2. Set custom rates directly:
       converter.set_rates({"EUR": 0.95, "GBP": 0.82})

    3. Use environment variables:
       export CURRENCY_RATE_EUR=0.95
       export CURRENCY_RATE_GBP=0.82
"""

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional


class CurrencyConverter:
    """
    Convert and format USD amounts to multiple currencies.

    Supports customizable exchange rates via config file or direct setting.

    Warning:
        Default exchange rates are static approximations from December 2025.
        For production use, provide current rates via config file or set_rates().
    """

    # Default exchange rates (USD to target currency)
    # WARNING: These are approximate rates from December 2025
    # Update via config file or set_rates() for accurate values
    # Source: Approximate market rates - NOT suitable for financial calculations
    DEFAULT_RATES = {
        "USD": 1.0,
        "EUR": 0.92,
        "GBP": 0.79,
        "BRL": 6.10,
        "CAD": 1.36,
        "AUD": 1.53,
        "JPY": 149.50,
        "CNY": 7.24,
        "INR": 83.50,
        "MXN": 17.20,
    }

    # Currency symbols
    SYMBOLS = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "BRL": "R$",
        "CAD": "C$",
        "AUD": "A$",
        "JPY": "¥",
        "CNY": "¥",
        "INR": "₹",
        "MXN": "$",
    }

    # Currency names
    NAMES = {
        "USD": "US Dollar",
        "EUR": "Euro",
        "GBP": "British Pound",
        "BRL": "Brazilian Real",
        "CAD": "Canadian Dollar",
        "AUD": "Australian Dollar",
        "JPY": "Japanese Yen",
        "CNY": "Chinese Yuan",
        "INR": "Indian Rupee",
        "MXN": "Mexican Peso",
    }

    def __init__(
        self,
        rates: Optional[dict[str, float]] = None,
        display_currencies: Optional[list[str]] = None,
        config_path: Optional[Path] = None,
    ):
        """
        Initialize converter.

        Args:
            rates: Custom exchange rates (USD to target)
            display_currencies: List of currencies to show in format_all()
            config_path: Path to config file with rates
        """
        self.rates = self.DEFAULT_RATES.copy()

        # Load from config file if provided
        if config_path and config_path.exists():
            self._load_config(config_path)

        # Override with provided rates
        if rates:
            self.rates.update(rates)

        # Currencies to display by default
        self.display_currencies = display_currencies or ["USD", "EUR", "GBP", "BRL"]

    def _load_config(self, config_path: Path):
        """Load exchange rates from config file."""
        try:
            with open(config_path) as f:
                config = json.load(f)

            if "currency_rates" in config:
                self.rates.update(config["currency_rates"])

            if "display_currencies" in config:
                self.display_currencies = config["display_currencies"]

        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in currency config: {e}")
        except OSError as e:
            print(f"Warning: Could not read currency config: {e}")

    def convert(self, amount_usd: float, currency: str) -> float:
        """
        Convert USD to target currency.

        Args:
            amount_usd: Amount in USD
            currency: Target currency code (e.g., "EUR")

        Returns:
            Amount in target currency
        """
        currency = currency.upper()
        rate = self.rates.get(currency, 1.0)
        return amount_usd * rate

    def format(
        self, amount_usd: float, currency: str, include_symbol: bool = True, decimal_places: int = 2
    ) -> str:
        """
        Format amount in target currency.

        Args:
            amount_usd: Amount in USD
            currency: Target currency code
            include_symbol: Include currency symbol
            decimal_places: Number of decimal places

        Returns:
            Formatted string (e.g., "€1.63")
        """
        currency = currency.upper()
        converted = self.convert(amount_usd, currency)

        # Special case for JPY (no decimals typically)
        if currency == "JPY":
            decimal_places = 0

        formatted = f"{converted:,.{decimal_places}f}"

        if include_symbol:
            symbol = self.SYMBOLS.get(currency, currency)
            return f"{symbol}{formatted}"

        return formatted

    def format_all(
        self, amount_usd: float, separator: str = " | ", currencies: Optional[list[str]] = None
    ) -> str:
        """
        Format amount in all display currencies.

        Args:
            amount_usd: Amount in USD
            separator: Separator between currencies
            currencies: Override list of currencies to display

        Returns:
            Formatted string (e.g., "$1.77 | €1.63 | £1.40")
        """
        currencies = currencies or self.display_currencies
        parts = [self.format(amount_usd, c) for c in currencies]
        return separator.join(parts)

    def format_compact(self, amount_usd: float) -> str:
        """
        Format amount in compact style for terminal display.

        Returns:
            Compact format (e.g., "$1.77/€1.63/£1.40")
        """
        return self.format_all(amount_usd, separator="/")

    def format_table_row(self, amount_usd: float) -> dict[str, str]:
        """
        Get formatted amounts as dictionary for table display.

        Returns:
            Dictionary of currency code -> formatted amount
        """
        return {currency: self.format(amount_usd, currency) for currency in self.display_currencies}

    def set_rates(self, rates: dict[str, float]):
        """Update exchange rates."""
        self.rates.update(rates)

    def set_display_currencies(self, currencies: list[str]):
        """Set which currencies to display."""
        self.display_currencies = [c.upper() for c in currencies]

    def get_rate(self, currency: str) -> float:
        """Get exchange rate for a currency."""
        return self.rates.get(currency.upper(), 1.0)

    def list_currencies(self) -> list[dict]:
        """List all supported currencies with their rates."""
        return [
            {
                "code": code,
                "name": self.NAMES.get(code, code),
                "symbol": self.SYMBOLS.get(code, code),
                "rate": rate,
            }
            for code, rate in sorted(self.rates.items())
        ]

    def save_config(self, config_path: Path):
        """Save current rates to config file (atomic write).

        Uses a temporary file and rename to prevent corruption on write failure.
        """
        config = {
            "currency_rates": self.rates,
            "display_currencies": self.display_currencies,
        }

        # Ensure parent directory exists
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first, then atomic rename
        fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp", prefix=config_path.stem, dir=config_path.parent
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(config, f, indent=2)
            # Atomic rename (works on POSIX, best-effort on Windows)
            os.replace(tmp_path, config_path)
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise


# Thread-safe global converter storage
_converter_lock = threading.Lock()
_converter: Optional[CurrencyConverter] = None


def get_converter() -> CurrencyConverter:
    """
    Get or create the global converter instance (thread-safe).

    Returns:
        A shared CurrencyConverter instance.

    Note:
        The converter is shared across threads since exchange rates
        are read-only after initialization. If you need to modify
        rates for a specific thread, create a new instance instead.
    """
    global _converter
    if _converter is None:
        with _converter_lock:
            # Double-check pattern for thread safety
            if _converter is None:
                _converter = CurrencyConverter()
    return _converter


def set_converter(converter: CurrencyConverter):
    """
    Set the global converter instance (thread-safe).

    Args:
        converter: The CurrencyConverter instance to use globally.
    """
    global _converter
    with _converter_lock:
        _converter = converter


# Convenience functions
def convert(amount_usd: float, currency: str) -> float:
    """Convert USD to target currency using global converter."""
    return get_converter().convert(amount_usd, currency)


def format_currency(amount_usd: float, currency: str = "USD") -> str:
    """Format amount using global converter."""
    return get_converter().format(amount_usd, currency)


def format_all_currencies(amount_usd: float) -> str:
    """Format amount in all display currencies using global converter."""
    return get_converter().format_all(amount_usd)


if __name__ == "__main__":
    # Demo/test
    converter = CurrencyConverter()

    amount = 15.77

    print(f"Amount: ${amount:.2f} USD\n")

    print("Individual currencies:")
    for currency in ["USD", "EUR", "GBP", "BRL", "JPY"]:
        print(f"  {currency}: {converter.format(amount, currency)}")

    print("\nAll display currencies:")
    print(f"  {converter.format_all(amount)}")

    print("\nCompact format:")
    print(f"  {converter.format_compact(amount)}")

    print("\nTable row:")
    for code, formatted in converter.format_table_row(amount).items():
        print(f"  {code}: {formatted}")

    print("\nSupported currencies:")
    for curr in converter.list_currencies():
        print(f"  {curr['code']}: {curr['name']} ({curr['symbol']}) - Rate: {curr['rate']}")
