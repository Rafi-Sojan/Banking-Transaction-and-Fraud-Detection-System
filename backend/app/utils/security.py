"""Password hashing and JWT authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.api.dependencies import get_db

_bearer = HTTPBearer(auto_error=False)
_SCRYPT_N = 16384
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${encode(salt)}${encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_encoded, digest_encoded = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_encoded.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_encoded.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user: dict[str, Any]) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_expiry_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["user_id"]),
        "username": user["username"],
        "role": user["role_name"],
        "customer_id": user.get("customer_id"),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), expires_in


def _anonymous_user() -> dict[str, Any]:
    return {"user_id": 0, "username": "anonymous", "role_name": "anonymous", "customer_id": None}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    connection=Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.auth_required and credentials is None:
        return _anonymous_user()
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    row = connection.execute(
        """
        SELECT u.user_id, u.username, u.customer_id, u.status, r.role_name
        FROM app_user u
        JOIN role r ON r.role_id = u.role_id
        WHERE u.user_id = %s
        """,
        (user_id,),
    ).fetchone()
    if row is None or row["status"] != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing")
    return dict(row)


def require_roles(*allowed_roles: str) -> Callable[..., dict[str, Any]]:
    def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if user["role_name"] not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency
