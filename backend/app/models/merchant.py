"""Typed representation of a merchant row."""

from typing import TypedDict


class MerchantRecord(TypedDict):
    merchant_id: int
    category_id: int
    location_id: int | None
    merchant_name: str
    status: str
