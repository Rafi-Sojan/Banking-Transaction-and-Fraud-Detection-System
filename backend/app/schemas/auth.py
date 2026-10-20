"""Authentication request and response contracts."""

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
