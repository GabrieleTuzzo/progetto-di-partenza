"""Read-only review tools for the local LipariBank API."""

from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("finbank-mcp")

BASE_URL = os.environ.get("FINBANK_BASE_URL", "http://localhost:8080").rstrip("/")
RESOURCE_DIR = Path(__file__).parent / "resources"
REQUEST_TIMEOUT = httpx.Timeout(5.0, connect=2.0)
MAX_MOVEMENTS = 10
AMOUNT_PATTERN = re.compile(r"^(?:0|[1-9]\d{0,16})(?:\.\d{1,2})?$")
_client = httpx.Client(timeout=REQUEST_TIMEOUT)
_access_token: str | None = None


def _login() -> str:
    username = os.environ.get("FINBANK_USERNAME")
    password = os.environ.get("FINBANK_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "Set FINBANK_USERNAME and FINBANK_PASSWORD to read the protected backend."
        )

    try:
        response = _client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": username, "password": password},
        )
    except httpx.RequestError as error:
        raise RuntimeError("LipariBank authentication endpoint is unavailable.") from error

    if response.is_error:
        raise RuntimeError(
            f"LipariBank authentication failed with HTTP {response.status_code}."
        )
    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("LipariBank returned invalid authentication data.") from error
    token = payload.get("token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise RuntimeError("LipariBank authentication response contains no token.")
    return token


def _api_get(path: str, params: dict[str, int] | None = None) -> Any:
    global _access_token
    if _access_token is None:
        _access_token = _login()

    for attempt in range(2):
        try:
            response = _client.get(
                f"{BASE_URL}{path}",
                params=params,
                headers={"Authorization": f"Bearer {_access_token}"},
            )
        except httpx.RequestError as error:
            raise RuntimeError("LipariBank backend is unavailable.") from error

        if response.status_code == 401 and attempt == 0:
            _access_token = _login()
            continue
        if response.is_error:
            raise RuntimeError(
                f"LipariBank returned HTTP {response.status_code} for {path}."
            )
        try:
            return response.json()
        except ValueError as error:
            raise RuntimeError(f"LipariBank returned invalid JSON for {path}.") from error

    raise RuntimeError("LipariBank authentication failed after token refresh.")


def _read_account(account_id: int) -> dict[str, Any]:
    payload = _api_get(f"/api/accounts/{account_id}")
    if not isinstance(payload, dict):
        raise RuntimeError("LipariBank returned an invalid account record.")
    try:
        balance = Decimal(str(payload["balance"]))
        currency = payload["currency"]
        status = payload["status"]
    except (KeyError, InvalidOperation, TypeError) as error:
        raise RuntimeError("LipariBank account record is missing required fields.") from error
    if not balance.is_finite() or not isinstance(currency, str) or not isinstance(status, str):
        raise RuntimeError("LipariBank returned invalid account data.")
    return {
        "account_id": account_id,
        "balance": format(balance, ".2f"),
        "currency": currency,
        "status": status,
        "_balance": balance,
    }


def _money(amount: str) -> Decimal:
    if not AMOUNT_PATTERN.fullmatch(amount):
        raise ValueError("Amount must be a positive decimal with at most two decimals.")
    try:
        value = Decimal(amount)
    except InvalidOperation as error:
        raise ValueError("Amount is not a valid decimal.") from error
    if value <= 0:
        raise ValueError("Amount must be greater than zero.")
    return value


@mcp.tool()
def get_account_balance(
    account_id: Annotated[int, Field(gt=0, description="ID of the account to inspect.")],
) -> dict[str, int | str]:
    """Read the live balance, currency, and status for one account.

    Use during movement reviews when reasoning depends on the current account
    state. Returns only fields relevant to the review; it never changes data.
    """
    account = _read_account(account_id)
    return {key: value for key, value in account.items() if not key.startswith("_")}


@mcp.tool()
def get_recent_movements(
    account_id: Annotated[int, Field(gt=0, description="ID of the account to inspect.")],
    limit: Annotated[
        int,
        Field(ge=1, le=MAX_MOVEMENTS, description=f"Number of recent entries, at most {MAX_MOVEMENTS}."),
    ] = 5,
) -> dict[str, int | list[dict[str, int | str | None]]]:
    """Read a bounded number of recent movements for one account.

    Results are ordered newest first. The server enforces a maximum of 10,
    irrespective of caller input; descriptions and customer identifiers are
    not returned.
    """
    payload = _api_get(
        "/api/movements",
        params={"accountId": account_id},
    )
    if not isinstance(payload, list):
        raise RuntimeError("LipariBank returned an invalid movement list.")

    movements: list[dict[str, int | str | None]] = []
    for movement in payload[: min(limit, MAX_MOVEMENTS)]:
        if not isinstance(movement, dict):
            raise RuntimeError("LipariBank returned an invalid movement record.")
        try:
            movement_id = movement["id"]
            movement_type = movement["type"]
            amount = Decimal(str(movement["amount"]))
            counterparty = movement.get("counterpartyAccountId")
            executed_at = movement["executedAt"]
        except (KeyError, InvalidOperation, TypeError) as error:
            raise RuntimeError("Movement record is missing required fields.") from error
        if (
            not isinstance(movement_id, int)
            or not isinstance(movement_type, str)
            or not amount.is_finite()
            or (counterparty is not None and not isinstance(counterparty, int))
            or not isinstance(executed_at, str)
        ):
            raise RuntimeError("LipariBank returned invalid movement data.")
        movements.append(
            {
                "movement_id": movement_id,
                "type": movement_type,
                "amount": format(amount, ".2f"),
                "counterparty_account_id": counterparty,
                "executed_at": executed_at,
            }
        )
    return {"account_id": account_id, "count": len(movements), "movements": movements}


@mcp.tool()
def simulate_transfer(
    source_account_id: Annotated[int, Field(gt=0, description="Account to debit.")],
    target_account_id: Annotated[int, Field(gt=0, description="Account to credit.")],
    amount: Annotated[
        str,
        Field(
            pattern=r"^(?:0|[1-9]\d{0,16})(?:\.\d{1,2})?$",
            description=(
                "Positive amount as a decimal string, up to 17 integer and 2 decimal "
                "digits, for example '25.00'."
            ),
        ),
    ],
) -> dict[str, Any]:
    """Simulate a transfer against current balances without executing it.

    Reads both accounts and applies the backend's known checks: distinct
    accounts and sufficient source funds. This tool makes GET requests only;
    it never calls the transfer endpoint or changes account state.
    """
    if source_account_id == target_account_id:
        raise ValueError("Source and target accounts must be different.")
    transfer_amount = _money(amount)
    source = _read_account(source_account_id)
    target = _read_account(target_account_id)
    if source["currency"] != target["currency"]:
        raise ValueError("Accounts use different currencies; simulation is unsupported.")

    before_source = source["_balance"]
    before_target = target["_balance"]
    can_transfer = before_source >= transfer_amount
    return {
        "simulation_only": True,
        "would_succeed": can_transfer,
        "consistency_note": (
            "Account balances were read separately and may change before any later transfer."
        ),
        "currency": source["currency"],
        "amount": format(transfer_amount, ".2f"),
        "source": {
            "account_id": source_account_id,
            "balance_before": format(before_source, ".2f"),
            "balance_after": (
                format(before_source - transfer_amount, ".2f") if can_transfer else None
            ),
        },
        "target": {
            "account_id": target_account_id,
            "balance_before": format(before_target, ".2f"),
            "balance_after": (
                format(before_target + transfer_amount, ".2f") if can_transfer else None
            ),
        },
        "reason": None if can_transfer else "insufficient_funds",
    }


@mcp.resource(
    "finbank://regulations/psd2-payment-authorization",
    name="PSD2 payment authorization reference",
    mime_type="text/markdown",
)
def payment_authorization_reference() -> str:
    """Read the locally maintained source note for payment authorization."""
    return (RESOURCE_DIR / "psd2-payment-authorization.md").read_text(encoding="utf-8")


@mcp.resource(
    "finbank://reference/liparibank-api",
    name="LipariBank API contract",
    mime_type="text/markdown",
)
def liparibank_api_reference() -> str:
    """Read the local API contract used by the review tools."""
    return (RESOURCE_DIR / "liparibank-api.md").read_text(encoding="utf-8")


@mcp.prompt(
    name="review_movement_change",
    description="Review movement changes using live account data and the supplied source reference.",
)
def review_movement_change(change_summary: str) -> str:
    """Create a movement-review request grounded in tools and resources."""
    return f"""Review this movement-related change: {change_summary}

Before concluding:
1. Read finbank://reference/liparibank-api to understand the available data and limits.
2. Read finbank://regulations/psd2-payment-authorization and cite its exact source and
   article in any applicable compliance observation. Do not claim it governs balance
   arithmetic; state when its scope is not applicable.
3. Use get_account_balance and/or get_recent_movements when the changed behavior
   depends on current account state. Use simulate_transfer to test concrete transfer
   amounts. Do not infer that a tool was called; rely on its returned data.
4. Report tool failures explicitly. A simulation is not an executed or guaranteed
   transfer, and no finding may suggest that money was moved for this review.
"""


if __name__ == "__main__":
    mcp.run()
