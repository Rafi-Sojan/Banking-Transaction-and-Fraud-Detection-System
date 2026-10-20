"""Typed representation of a card row."""

from datetime import date
from typing import TypedDict


class CardRecord(TypedDict):
    card_id: int
    account_id: int
    card_number_hash: str
    card_type: str
    expiry_date: date
    status: str
