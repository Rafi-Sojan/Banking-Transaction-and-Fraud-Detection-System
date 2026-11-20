"""Transaction endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query
import psycopg

from app.api.dependencies import get_db
from app.schemas.transaction import HeldTransactionDecision, TransactionLifecycleResponse, TransferRequest, TransferResponse
from app.services.fraud_service import FraudEngineError, FraudEngineUnavailable
from app.services.ml_service import MLEngineError, MLEngineUnavailable
from app.services.transaction_services import create_transfer, list_transactions
from app.services.transaction_lifecycle_service import approve_held_transfer, decline_held_transfer, reverse_completed_transfer
from app.utils.security import get_current_user, require_roles

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/transfers", response_model=TransferResponse, status_code=201)
def create_transfer_endpoint(
    request: TransferRequest,
    connection=Depends(get_db),
    user=Depends(get_current_user),
) -> TransferResponse:
    try:
        return create_transfer(connection, request, user["user_id"] or None)
    except FraudEngineUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FraudEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except MLEngineUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except MLEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[dict])
def get_transactions(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    connection=Depends(get_db),
    user=Depends(get_current_user),
) -> list[dict]:
    return list_transactions(connection, user, limit, offset)


@router.get("/{transaction_id}", response_model=dict)
def get_transaction(transaction_id: int, connection=Depends(get_db), user=Depends(get_current_user)) -> dict:
    row = connection.execute(
        """
        SELECT tr.*, source_account.customer_id AS source_customer_id
        FROM transaction_reports tr
        JOIN account source_account ON source_account.account_id = tr.source_account_id
        WHERE tr.transaction_id = %s
        """,
        (transaction_id,),
    ).fetchone()
    if row is None or (
        user["role_name"] == "customer" and row["source_customer_id"] != user.get("customer_id")
    ):
        raise HTTPException(status_code=404, detail="Transaction not found")
    result = dict(row)
    result.pop("source_customer_id", None)
    return result


@router.post("/{transaction_id}/approve", response_model=TransactionLifecycleResponse)
def approve_transaction(
    transaction_id: int,
    connection=Depends(get_db),
    user=Depends(require_roles("investigator", "administrator")),
) -> TransactionLifecycleResponse:
    try:
        transaction = approve_held_transfer(connection, transaction_id, user["user_id"])
        connection.commit()
        return TransactionLifecycleResponse(transaction=transaction, action="approved")
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{transaction_id}/decline", response_model=TransactionLifecycleResponse)
def decline_transaction(
    transaction_id: int,
    request: HeldTransactionDecision,
    connection=Depends(get_db),
    user=Depends(require_roles("investigator", "administrator")),
) -> TransactionLifecycleResponse:
    try:
        transaction = decline_held_transfer(connection, transaction_id, user["user_id"], request.reason)
        connection.commit()
        return TransactionLifecycleResponse(transaction=transaction, action="declined")
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{transaction_id}/reverse", response_model=TransactionLifecycleResponse)
def reverse_transaction(
    transaction_id: int,
    request: HeldTransactionDecision,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=160),
    connection=Depends(get_db),
    user=Depends(require_roles("investigator", "administrator")),
) -> TransactionLifecycleResponse:
    try:
        transaction = reverse_completed_transfer(
            connection, transaction_id, user["user_id"], idempotency_key, request.reason
        )
        connection.commit()
        return TransactionLifecycleResponse(transaction=transaction, action="reversed")
    except (ValueError, psycopg.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
