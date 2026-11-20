"""Supporting event contracts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventRead(BaseModel):
    event_type: str
    occurred_at: datetime
    payload: dict[str, Any]
