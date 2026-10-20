"""Typed representation of a customer row."""

from typing import TypedDict


class CustomerRecord(TypedDict):
    customer_id: int
    full_name: str
    email: str
    phone: str | None
    address: str | None
    status: str
