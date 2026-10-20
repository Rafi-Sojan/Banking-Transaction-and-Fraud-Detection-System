"""Fraud investigation workflow services."""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Json


def create_investigation(
    connection: Any,
    alert_id: int,
    assigned_user_id: int | None,
    notes: str | None,
    actor_user_id: int | None = None,
) -> dict[str, Any]:
    row = connection.execute(
        """
        INSERT INTO investigation (alert_id, assigned_user_id, investigation_status, notes)
        VALUES (%s, %s, 'open', %s)
        RETURNING *
        """,
        (alert_id, assigned_user_id, notes),
    ).fetchone()
    connection.execute(
        "UPDATE fraud_alert SET alert_status = 'under_review' WHERE alert_id = %s AND alert_status = 'open'",
        (alert_id,),
    )
    connection.execute(
        """
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
        VALUES (%s, 'open_investigation', 'investigation', %s, %s)
        """,
        (actor_user_id, row["investigation_id"], Json({"alert_id": alert_id})),
    )
    return dict(row)


def close_investigation(
    connection: Any,
    investigation_id: int,
    user_id: int,
    outcome: str,
    notes: str | None,
) -> dict[str, Any]:
    connection.execute(
        "SELECT close_investigation(%s, %s, %s, %s)",
        (investigation_id, user_id, outcome, notes),
    )
    row = connection.execute(
        "SELECT * FROM investigation WHERE investigation_id = %s",
        (investigation_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Investigation {investigation_id} does not exist")
    connection.execute(
        """
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
        VALUES (%s, 'close_investigation', 'investigation', %s, %s)
        """,
        (user_id, investigation_id, Json({"outcome": outcome})),
    )
    return dict(row)
