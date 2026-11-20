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


@router.get("/audit", response_model=list[dict])
def audit_report(
    action: str | None = None,
    entity_type: str | None = None,
    user_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    connection=Depends(get_db),
    _user=Depends(require_roles("investigator", "administrator")),
) -> list[dict]:
    filters: list[str] = []
    params: list[object] = []
    if action:
        filters.append("action = %s")
        params.append(action)
    if entity_type:
        filters.append("entity_type = %s")
        params.append(entity_type)
    if user_id is not None:
        filters.append("user_id = %s")
        params.append(user_id)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    params.extend([limit, offset])
    rows = connection.execute(
        f"SELECT * FROM audit_log {where} ORDER BY event_timestamp DESC, audit_id DESC LIMIT %s OFFSET %s",
        params,
    ).fetchall()
    return [dict(row) for row in rows]
