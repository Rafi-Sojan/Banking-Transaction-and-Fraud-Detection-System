"""Typed representation of an account row returned by PostgreSQL."""

from decimal import Decimal
from typing import TypedDict


class AccountRecord(TypedDict):
    account_id: int
    customer_id: int
    branch_id: int
    account_number: str
    account_type: str
    balance: Decimal
    currency_code: str
    status: str
