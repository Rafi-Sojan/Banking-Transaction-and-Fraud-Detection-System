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
        "SELECT close_investigation(%s::BIGINT, %s::BIGINT, %s::VARCHAR, %s::TEXT)",
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


def list_investigations(connection: Any, limit: int, offset: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM investigation ORDER BY opened_at DESC, investigation_id DESC LIMIT %s OFFSET %s",
        (limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]


def get_investigation(connection: Any, investigation_id: int) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM investigation WHERE investigation_id = %s", (investigation_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    actions = connection.execute(
        "SELECT * FROM investigation_action WHERE investigation_id = %s ORDER BY action_timestamp, action_id",
        (investigation_id,),
    ).fetchall()
    result["actions"] = [dict(action) for action in actions]
    return result


def assign_investigation(
    connection: Any,
    investigation_id: int,
    assigned_user_id: int | None,
    investigation_status: str,
    actor_user_id: int,
) -> dict[str, Any]:
    row = connection.execute(
        """
        UPDATE investigation
        SET assigned_user_id = %s, investigation_status = %s, updated_at = CURRENT_TIMESTAMP
        WHERE investigation_id = %s
        RETURNING *
        """,
        (assigned_user_id, investigation_status, investigation_id),
    ).fetchone()
    if row is None:
        raise ValueError(f"Investigation {investigation_id} does not exist")
    connection.execute(
        "INSERT INTO audit_log (user_id, action, entity_type, entity_id, details) VALUES (%s, 'assign_investigation', 'investigation', %s, %s)",
        (actor_user_id, investigation_id, Json({"assigned_user_id": assigned_user_id, "status": investigation_status})),
    )
    return dict(row)


def add_investigation_action(
    connection: Any,
    investigation_id: int,
    actor_user_id: int,
    action_type: str,
    notes: str | None,
) -> dict[str, Any]:
    row = connection.execute(
        "INSERT INTO investigation_action (investigation_id, user_id, action_type, notes) VALUES (%s, %s, %s, %s) RETURNING *",
        (investigation_id, actor_user_id, action_type, notes),
    ).fetchone()
    if row is None:
        raise ValueError(f"Investigation {investigation_id} does not exist")
    connection.execute(
        "INSERT INTO audit_log (user_id, action, entity_type, entity_id, details) VALUES (%s, 'investigation_action', 'investigation', %s, %s)",
        (actor_user_id, investigation_id, Json({"action_type": action_type})),
    )
    return dict(row)
