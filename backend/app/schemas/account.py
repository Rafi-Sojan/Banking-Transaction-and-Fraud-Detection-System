"""Account contracts."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    customer_id: int
    branch_id: int
    account_number: str
    account_type: str
    balance: Decimal
    currency_code: str
    status: str
    created_at: datetime
    updated_at: datetime
