"""Model registry contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class MLModelCreate(BaseModel):
    model_name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=60)
    model_path: str = Field(min_length=1, max_length=500)
    precision_score: Decimal | None = Field(default=None, ge=0, le=1)
    recall_score: Decimal | None = Field(default=None, ge=0, le=1)
    f1_score: Decimal | None = Field(default=None, ge=0, le=1)
    pr_auc_score: Decimal | None = Field(default=None, ge=0, le=1)
    roc_auc_score: Decimal | None = Field(default=None, ge=0, le=1)
    deployment_status: str = Field(default="offline", pattern=r"^(offline|staged)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class MLModelRead(MLModelCreate):
    model_id: int
    created_at: datetime
    deployment_status: str = Field(pattern=r"^(offline|staged|deployed|retired)$")

