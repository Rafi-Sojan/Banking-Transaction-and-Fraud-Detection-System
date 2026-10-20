"""Typed representation of an investigation row."""

from datetime import datetime
from typing import TypedDict


class InvestigationRecord(TypedDict):
    investigation_id: int
    alert_id: int
    assigned_user_id: int | None
    investigation_status: str
    outcome: str | None
    notes: str | None
    opened_at: datetime
    closed_at: datetime | None
