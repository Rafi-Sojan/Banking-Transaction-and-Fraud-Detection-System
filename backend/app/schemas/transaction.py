"""Transaction and C++ rule-engine contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionFeatures(BaseModel):
    merchant_category: str = ""
    country: str = ""
    home_country: str = ""
    transaction_count_10m: int = Field(default=0, ge=0)
    failed_attempts_1h: int = Field(default=0, ge=0)
    account_age_days: int = Field(default=-1, ge=-1)
    is_new_device: bool = False
    is_new_location: bool = False


class TransferRequest(BaseModel):
    source_account_id: int = Field(gt=0)
    destination_account_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    currency_code: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    features: TransactionFeatures = Field(default_factory=TransactionFeatures)

    @field_validator("currency_code", mode="before")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()

    def ensure_distinct_accounts(self) -> None:
        if self.source_account_id == self.destination_account_id:
            raise ValueError("source and destination accounts must be different")


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: int
    source_account_id: int
    destination_account_id: int | None = None
    card_id: int | None = None
    merchant_id: int | None = None
    initiated_by_user_id: int | None = None
    amount: Decimal
    currency_code: str
    transaction_type: str
    transaction_timestamp: datetime
    status: str
    idempotency_key: str | None = None
    description: str | None = None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RuleResultRead(BaseModel):
    rule_id: str
    triggered: bool
    risk_contribution: float
    reason: str


class FraudEvaluationRead(BaseModel):
    transaction_id: str
    rule_score: float = Field(ge=0, le=1)
    risk_level: str
    rules: list[RuleResultRead]
    reasons: list[str]


class TransferResponse(BaseModel):
    transaction: TransactionRead
    evaluation: FraudEvaluationRead
    alert_id: int | None = None
