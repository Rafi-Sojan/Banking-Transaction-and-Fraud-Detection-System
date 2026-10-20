"""Shared validation helpers for service boundaries."""

import re
from decimal import Decimal


def validate_currency(currency_code: str) -> str:
    value = currency_code.upper()
    if not re.fullmatch(r"[A-Z]{3}", value):
        raise ValueError("currency code must contain three uppercase letters")
    return value


def validate_positive_amount(amount: Decimal) -> Decimal:
    if amount <= 0:
        raise ValueError("amount must be greater than zero")
    return amount
