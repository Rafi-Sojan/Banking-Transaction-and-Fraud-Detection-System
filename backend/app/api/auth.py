"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.utils.security import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, connection=Depends(get_db)) -> TokenResponse:
    row = connection.execute(
        """
        SELECT u.user_id, u.username, u.password_hash, u.customer_id, u.status, r.role_name
        FROM app_user u
        JOIN role r ON r.role_id = u.role_id
        WHERE u.username = %s
        """,
        (request.username,),
    ).fetchone()
    if row is None or row["status"] != "active" or not verify_password(
        request.password.get_secret_value(), row["password_hash"]
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token, expires_in = create_access_token(dict(row))
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse)
def current_user(user=Depends(get_current_user)) -> UserResponse:
    return UserResponse(**{key: user[key] for key in ("user_id", "username", "role_name", "customer_id")})
