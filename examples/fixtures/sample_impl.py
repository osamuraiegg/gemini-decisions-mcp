"""Sample payment gateway implementation with intentional spec drift for demo purposes."""

from __future__ import annotations

REQUEST_TIMEOUT_SECONDS = 15  # Spec says 30s
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0


class GatewayTimeoutError(Exception):
    """Raised when the payment gateway times out."""


class InvalidCurrencyError(Exception):
    """Raised when an unsupported currency code is supplied (undocumented in spec)."""


SUPPORTED_CURRENCIES = {"USD", "JPY", "EUR"}


def authorize(
    amount_cents: int,
    currency: str,
    idempotency_key: str,
    dry_run: bool = False,
) -> dict[str, str | int | bool]:
    """Authorize a payment amount."""
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if currency not in SUPPORTED_CURRENCIES:
        raise InvalidCurrencyError(f"Unsupported currency: {currency}")

    return {
        "status": "dry_run" if dry_run else "authorized",
        "amount_cents": amount_cents,
        "currency": currency,
        "idempotency_key": idempotency_key,
    }
