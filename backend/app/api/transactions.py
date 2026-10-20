"""Transaction endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg

from app.api.dependencies import get_db
from app.schemas.transaction import TransferRequest, TransferResponse
from app.services.fraud_service import FraudEngineError, FraudEngineUnavailable
from app.services.transaction_services import create_transfer, list_transactions
from app.utils.security import get_current_user

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
