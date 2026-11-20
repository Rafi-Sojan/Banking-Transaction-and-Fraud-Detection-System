"""Authentication request and response contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9_.-]+$")
    password: SecretStr = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    user_id: int
    username: str
    role_name: str
    customer_id: int | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9_.-]+$")
    password: SecretStr = Field(min_length=12, max_length=256)
    role_name: Literal["customer", "investigator", "administrator"] = "customer"
    customer_id: int | None = Field(default=None, gt=0)


class UserListItem(UserResponse):
    status: str
    created_at: datetime
