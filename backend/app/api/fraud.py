"""Fraud alert and investigation endpoints."""

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.types.json import Json

from app.api.dependencies import get_db
from app.schemas.fraud import (
    FraudAlertRead, FraudAlertStatusUpdate, InvestigationActionCreate, InvestigationActionRead,
    InvestigationAssignment, InvestigationClose, InvestigationCreate, InvestigationDetailRead, InvestigationRead,
)
from app.services.fraud_service import get_alert, list_alerts
from app.services.investigation_service import (
    add_investigation_action, assign_investigation, close_investigation, create_investigation,
    get_investigation, list_investigations,
)
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


@router.get("/investigations", response_model=list[InvestigationRead])
def get_investigations(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    connection=Depends(get_db),
    _user=Depends(require_roles("investigator", "administrator")),
) -> list[InvestigationRead]:
    return [InvestigationRead.model_validate(row) for row in list_investigations(connection, limit, offset)]


@router.get("/investigations/{investigation_id}", response_model=InvestigationDetailRead)
def get_investigation_endpoint(
    investigation_id: int,
    connection=Depends(get_db),
    _user=Depends(require_roles("investigator", "administrator")),
) -> InvestigationDetailRead:
    row = get_investigation(connection, investigation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return InvestigationDetailRead.model_validate(row)


@router.patch("/investigations/{investigation_id}/assignment", response_model=InvestigationRead)
def assign_investigation_endpoint(
    investigation_id: int,
    request: InvestigationAssignment,
    connection=Depends(get_db),
    user=Depends(require_roles("investigator", "administrator")),
) -> InvestigationRead:
    try:
        row = assign_investigation(connection, investigation_id, request.assigned_user_id, request.investigation_status, user["user_id"])
        connection.commit()
        return InvestigationRead.model_validate(row)
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/investigations/{investigation_id}/actions", response_model=InvestigationActionRead, status_code=201)
def add_action_endpoint(
    investigation_id: int,
    request: InvestigationActionCreate,
    connection=Depends(get_db),
    user=Depends(require_roles("investigator", "administrator")),
) -> InvestigationActionRead:
    try:
        row = add_investigation_action(connection, investigation_id, user["user_id"], request.action_type, request.notes)
        connection.commit()
        return InvestigationActionRead.model_validate(row)
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/alerts/{alert_id}/status", response_model=FraudAlertRead)
def update_alert_status(
    alert_id: int,
    request: FraudAlertStatusUpdate,
    connection=Depends(get_db),
    user=Depends(require_roles("investigator", "administrator")),
) -> FraudAlertRead:
    try:
        row = connection.execute(
            "UPDATE fraud_alert SET alert_status = %s, updated_at = CURRENT_TIMESTAMP WHERE alert_id = %s RETURNING alert_id",
            (request.alert_status, alert_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Fraud alert not found")
        connection.execute(
            "INSERT INTO audit_log (user_id, action, entity_type, entity_id, details) VALUES (%s, 'update_alert_status', 'fraud_alert', %s, %s)",
            (user["user_id"], alert_id, Json({"alert_status": request.alert_status})),
        )
        connection.commit()
        return FraudAlertRead.model_validate(get_alert(connection, alert_id))
    except HTTPException:
        raise
    except psycopg.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
