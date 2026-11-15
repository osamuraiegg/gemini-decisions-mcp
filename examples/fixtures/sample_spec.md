# Payment Gateway Client Specification (Draft)

## Overview
`PaymentGatewayClient` handles outbound payment authorization requests with automatic retry logic.

## Configuration Constants
- `REQUEST_TIMEOUT_SECONDS`: `30` seconds
- `MAX_RETRIES`: `3` attempts
- `BACKOFF_BASE_SECONDS`: `1.0` second

## Public API
### `authorize(amount_cents: int, currency: str, idempotency_key: str) -> dict`
- Validates that `amount_cents > 0`.
- Sends authorization payload and returns `{"status": "authorized", "transaction_id": ...}`.
- Raises `GatewayTimeoutError` when upstream does not respond within `REQUEST_TIMEOUT_SECONDS`.
