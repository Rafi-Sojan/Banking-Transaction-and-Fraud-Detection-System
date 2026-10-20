"""Typed representation of a transaction row."""

from datetime import datetime
from decimal import Decimal
from typing import Any, TypedDict


class TransactionRecord(TypedDict):
    transaction_id: int
    source_account_id: int
    destination_account_id: int | None
    amount: Decimal
    currency_code: str
    transaction_type: str
    transaction_timestamp: datetime
    status: str
    idempotency_key: str | None
    metadata: dict[str, Any]
