"""PostgreSQL-backed transaction lifecycle operations."""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Json


def _load_transaction(connection: Any, transaction_id: int) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,)).fetchone()
    if row is None:
        raise ValueError(f"Transaction {transaction_id} does not exist")
    return dict(row)


def _audit(connection: Any, user_id: int, action: str, transaction_id: int, details: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
        VALUES (%s, %s, 'transaction', %s, %s)
        """,
        (user_id, action, transaction_id, Json(details)),
    )


def approve_held_transfer(connection: Any, transaction_id: int, user_id: int) -> dict[str, Any]:
    connection.execute("SELECT approve_held_transfer(%s::BIGINT, %s::BIGINT)", (transaction_id, user_id))
    _audit(connection, user_id, "approve_held_transfer", transaction_id, {"status": "completed"})
    return _load_transaction(connection, transaction_id)


def decline_held_transfer(connection: Any, transaction_id: int, user_id: int, reason: str | None) -> dict[str, Any]:
    connection.execute("SELECT decline_held_transfer(%s::BIGINT, %s::BIGINT, %s::TEXT)", (transaction_id, user_id, reason))
    _audit(connection, user_id, "decline_held_transfer", transaction_id, {"reason": reason})
    return _load_transaction(connection, transaction_id)


def reverse_completed_transfer(
    connection: Any,
    transaction_id: int,
    user_id: int,
    idempotency_key: str,
    reason: str | None,
) -> dict[str, Any]:
    row = connection.execute(
        "SELECT reverse_completed_transfer(%s::BIGINT, %s::BIGINT, %s::VARCHAR, %s::TEXT) AS reversal_id",
        (transaction_id, user_id, idempotency_key, reason),
    ).fetchone()
    reversal_id = int(row["reversal_id"])
    _audit(
        connection,
        user_id,
        "reverse_transfer",
        transaction_id,
        {"reversal_transaction_id": reversal_id, "reason": reason},
    )
    return _load_transaction(connection, reversal_id)
