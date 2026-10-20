"""Fraud-alert and investigation contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class FraudAlertRead(BaseModel):
    alert_id: int
    transaction_id: int
    rule_score: Decimal | None = None
    ml_probability: Decimal | None = None
    combined_risk_score: Decimal
    risk_level: str
    alert_status: str
    reasons: list[Any]
    alert_created_at: datetime
    transaction_timestamp: datetime
    amount: Decimal
    currency_code: str
    transaction_type: str
    source_account_id: int
    source_account_number: str
    merchant_id: int | None = None
    merchant_name: str | None = None
    investigation_id: int | None = None
    investigation_status: str | None = None
    outcome: str | None = None
    assigned_user_id: int | None = None


class InvestigationCreate(BaseModel):
    assigned_user_id: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class InvestigationClose(BaseModel):
    outcome: str = Field(pattern=r"^(confirmed_fraud|legitimate|inconclusive)$")
    notes: str | None = Field(default=None, max_length=2000)


class InvestigationRead(BaseModel):
    investigation_id: int
    alert_id: int
    assigned_user_id: int | None = None
    investigation_status: str
    outcome: str | None = None
    notes: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    updated_at: datetime
