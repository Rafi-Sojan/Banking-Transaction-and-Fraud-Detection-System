"""Customer contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: int
    full_name: str
    email: str
    phone: str | None = None
    address: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
