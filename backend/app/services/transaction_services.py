"""Transaction application service."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Json

from app.config import get_settings
from app.databases.mongodb import get_event_store
from app.schemas.transaction import TransferRequest, TransferResponse, TransactionRead
from app.services.fraud_service import FraudEngineClient, persist_fraud_alert
from app.utils.validators import validate_currency, validate_positive_amount


def _latest_alert_id(connection: Any, transaction_id: int) -> int | None:
    row = connection.execute(
        "SELECT alert_id FROM fraud_alert WHERE transaction_id = %s ORDER BY created_at DESC, alert_id DESC LIMIT 1",
        (transaction_id,),
    ).fetchone()
    return int(row["alert_id"]) if row else None


def _load_transaction(connection: Any, transaction_id: int) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,)).fetchone()
    if row is None:
        raise ValueError(f"Transaction {transaction_id} does not exist")
    return dict(row)


def create_transfer(
    connection: Any,
    request: TransferRequest,
    initiated_by_user_id: int | None,
    engine: FraudEngineClient | None = None,
) -> TransferResponse:
    request.ensure_distinct_accounts()
    validate_currency(request.currency_code)
    validate_positive_amount(request.amount)
    transaction_reference = request.idempotency_key or f"backend-{uuid4()}"
    evaluator = engine or FraudEngineClient()
    evaluation = evaluator.evaluate(transaction_reference, request.amount, "transfer", request.features)
    settings = get_settings()

    existing = None
    if request.idempotency_key:
        existing = connection.execute(
            "SELECT transaction_id FROM transactions WHERE idempotency_key = %s",
            (request.idempotency_key,),
        ).fetchone()
    if existing:
        transaction = _load_transaction(connection, int(existing["transaction_id"]))
        response = TransferResponse(
            transaction=TransactionRead.model_validate(transaction),
            evaluation=evaluation,
            alert_id=_latest_alert_id(connection, transaction["transaction_id"]),
        )
        connection.commit()
        return response

    hold = evaluation.rule_score >= settings.hold_threshold
    should_alert = evaluation.rule_score >= settings.alert_threshold
    if hold:
        account_rows = connection.execute(
            """
            SELECT account_id, status, currency_code
            FROM account
            WHERE account_id IN (%s, %s)
            FOR SHARE
            """,
            (request.source_account_id, request.destination_account_id),
        ).fetchall()
        if len(account_rows) != 2:
            raise ValueError("both source and destination accounts must exist")
        if any(row["status"] != "active" for row in account_rows):
            raise ValueError("both source and destination accounts must be active")
        if any(row["currency_code"] != request.currency_code for row in account_rows):
            raise ValueError(f"both accounts must use currency {request.currency_code}")
        transaction_row = connection.execute(
            """
            INSERT INTO transactions (
                source_account_id, destination_account_id, initiated_by_user_id,
                amount, currency_code, transaction_type, status, idempotency_key,
                description, metadata
            ) VALUES (%s, %s, %s, %s, %s, 'transfer', 'pending', %s, %s, %s)
            RETURNING *
            """,
            (
                request.source_account_id,
                request.destination_account_id,
                initiated_by_user_id,
                request.amount,
                request.currency_code,
                request.idempotency_key,
                request.description,
                Json(request.metadata),
            ),
        ).fetchone()
        transaction_id = int(transaction_row["transaction_id"])
    else:
        transaction_row = connection.execute(
            """
            SELECT process_transfer(%s, %s, %s, %s, %s, %s, %s, %s) AS transaction_id
            """,
            (
                request.source_account_id,
                request.destination_account_id,
                request.amount,
                request.currency_code,
                request.idempotency_key,
                initiated_by_user_id,
                request.description,
                Json(request.metadata),
            ),
        ).fetchone()
        transaction_id = int(transaction_row["transaction_id"])
        transaction_row = _load_transaction(connection, transaction_id)

    alert_id = persist_fraud_alert(connection, transaction_id, evaluation) if should_alert else None
    connection.execute(
        """
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
        VALUES (%s, %s, 'transaction', %s, %s)
        """,
        (
            initiated_by_user_id,
            "hold_transfer" if hold else "create_transfer",
            transaction_id,
            Json({
                "status": "held" if hold else "completed",
                "risk_level": evaluation.risk_level,
                "rule_score": evaluation.rule_score,
                "alert_id": alert_id,
            }),
        ),
    )
    transaction = _load_transaction(connection, transaction_id)
    response = TransferResponse(
        transaction=TransactionRead.model_validate(transaction),
        evaluation=evaluation,
        alert_id=alert_id,
    )
    connection.commit()
    get_event_store().record_event(
        "transaction_processed",
        {
            "transaction_id": transaction_id,
            "status": transaction["status"],
            "risk_level": evaluation.risk_level,
            "rule_score": evaluation.rule_score,
        },
    )
    return response


def list_transactions(connection: Any, user: dict[str, Any], limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    filters = []
    params: list[Any] = []
    if user["role_name"] == "customer" and user.get("customer_id") is not None:
        filters.append("source_account.customer_id = %s")
        params.append(user["customer_id"])
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.extend([limit, offset])
    rows = connection.execute(
        f"""
        SELECT tr.* FROM transaction_reports tr
        JOIN account source_account ON source_account.account_id = tr.source_account_id
        {where}
        ORDER BY tr.transaction_timestamp DESC, tr.transaction_id DESC
        LIMIT %s OFFSET %s
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]
