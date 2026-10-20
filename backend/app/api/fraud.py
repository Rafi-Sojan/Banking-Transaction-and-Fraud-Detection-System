"""Fraud alert and investigation endpoints."""

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_db
from app.schemas.fraud import FraudAlertRead, InvestigationClose, InvestigationCreate, InvestigationRead
from app.services.fraud_service import get_alert, list_alerts
from app.services.investigation_service import close_investigation, create_investigation
from app.utils.security import get_current_user, require_roles

router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.get("/alerts", response_model=list[FraudAlertRead])
def get_alerts(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    connection=Depends(get_db),
    user=Depends(get_current_user),
) -> list[FraudAlertRead]:
    return [FraudAlertRead.model_validate(row) for row in list_alerts(connection, user, limit, offset)]


@router.get("/alerts/{alert_id}", response_model=FraudAlertRead)
def get_alert_endpoint(alert_id: int, connection=Depends(get_db), user=Depends(get_current_user)) -> FraudAlertRead:
    row = get_alert(connection, alert_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fraud alert not found")
    if user["role_name"] == "customer":
        owner = connection.execute(
            "SELECT c.customer_id FROM fraud_alert fa JOIN transactions t ON t.transaction_id = fa.transaction_id JOIN account a ON a.account_id = t.source_account_id JOIN customer c ON c.customer_id = a.customer_id WHERE fa.alert_id = %s",
            (alert_id,),
        ).fetchone()
        if owner is None or owner["customer_id"] != user.get("customer_id"):
            raise HTTPException(status_code=404, detail="Fraud alert not found")
    return FraudAlertRead.model_validate(row)


@router.post("/alerts/{alert_id}/investigations", response_model=InvestigationRead, status_code=201)
def open_investigation(
    alert_id: int,
    request: InvestigationCreate,
    connection=Depends(get_db),
    user=Depends(require_roles("investigator", "administrator")),
) -> InvestigationRead:
    try:
        row = create_investigation(
            connection,
            alert_id,
            request.assigned_user_id or user["user_id"],
            request.notes,
            user["user_id"],
        )
        connection.commit()
        return InvestigationRead.model_validate(row)
    except psycopg.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/investigations/{investigation_id}/close", response_model=InvestigationRead)
def close_investigation_endpoint(
    investigation_id: int,
    request: InvestigationClose,
    connection=Depends(get_db),
    user=Depends(require_roles("investigator", "administrator")),
) -> InvestigationRead:
    try:
        row = close_investigation(connection, investigation_id, user["user_id"], request.outcome, request.notes)
        connection.commit()
        return InvestigationRead.model_validate(row)
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
