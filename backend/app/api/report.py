"""Read-only reporting endpoints."""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_db
from app.utils.security import require_roles

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/transactions", response_model=list[dict])
def transaction_report(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    connection=Depends(get_db),
    _user=Depends(require_roles("investigator", "administrator")),
) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM transaction_reports ORDER BY transaction_timestamp DESC, transaction_id DESC LIMIT %s OFFSET %s",
        (limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]


@router.get("/fraud", response_model=list[dict])
def fraud_report(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    connection=Depends(get_db),
    _user=Depends(require_roles("investigator", "administrator")),
) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM fraud_reports ORDER BY alert_created_at DESC, alert_id DESC LIMIT %s OFFSET %s",
        (limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]
