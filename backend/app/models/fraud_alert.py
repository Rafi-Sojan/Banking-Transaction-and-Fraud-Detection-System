"""Typed representation of a fraud-alert row."""

from decimal import Decimal
from typing import Any, TypedDict


class FraudAlertRecord(TypedDict):
    alert_id: int
    transaction_id: int
    rule_score: Decimal | None
    ml_probability: Decimal | None
    combined_risk_score: Decimal
    risk_level: str
    alert_status: str
    reasons: list[Any]
