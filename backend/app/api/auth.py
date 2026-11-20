"""Authentication endpoints."""

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg.types.json import Json

from app.api.dependencies import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserListItem, UserResponse
from app.utils.security import create_access_token, get_current_user, hash_password, require_roles, verify_password

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


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    request: UserCreate,
    connection=Depends(get_db),
    actor=Depends(require_roles("administrator")),
) -> UserResponse:
    if request.role_name == "customer" and request.customer_id is None:
        raise HTTPException(status_code=422, detail="customer_id is required for customer users")
    try:
        role = connection.execute("SELECT role_id FROM role WHERE role_name = %s", (request.role_name,)).fetchone()
        if role is None:
            raise HTTPException(status_code=400, detail="Role is not configured")
        row = connection.execute(
            """
            INSERT INTO app_user (customer_id, username, password_hash, role_id)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id, username, customer_id, status
            """,
            (request.customer_id, request.username, hash_password(request.password.get_secret_value()), role["role_id"]),
        ).fetchone()
        connection.execute(
            "INSERT INTO audit_log (user_id, action, entity_type, entity_id, details) VALUES (%s, 'create_user', 'app_user', %s, %s)",
            (actor["user_id"], row["user_id"], Json({"role_name": request.role_name})),
        )
        connection.commit()
        return UserResponse(user_id=row["user_id"], username=row["username"], role_name=request.role_name, customer_id=row["customer_id"])
    except HTTPException:
        raise
    except psycopg.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/users", response_model=list[UserListItem])
def list_users(
    connection=Depends(get_db),
    _actor=Depends(require_roles("investigator", "administrator")),
) -> list[UserListItem]:
    rows = connection.execute(
        """
        SELECT u.user_id, u.username, u.customer_id, u.status, u.created_at, r.role_name
        FROM app_user u JOIN role r ON r.role_id = u.role_id
        ORDER BY u.user_id
        """
    ).fetchall()
    return [UserListItem.model_validate(dict(row)) for row in rows]
