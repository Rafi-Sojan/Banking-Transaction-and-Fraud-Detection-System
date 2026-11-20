"""Authoritative PostgreSQL metadata for deployable ML models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from psycopg.types.json import Json

from app.config import get_settings


def list_models(connection: Any) -> list[dict[str, Any]]:
    rows = connection.execute("SELECT * FROM ml_model ORDER BY created_at DESC, model_id DESC").fetchall()
    return [dict(row) for row in rows]


def register_model(connection: Any, payload: Any, actor_user_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        INSERT INTO ml_model (
            model_name, version, model_path, precision_score, recall_score,
            f1_score, pr_auc_score, roc_auc_score, deployment_status, metadata
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            payload.model_name, payload.version, payload.model_path,
            payload.precision_score, payload.recall_score, payload.f1_score,
            payload.pr_auc_score, payload.roc_auc_score, payload.deployment_status,
            Json(payload.metadata),
        ),
    ).fetchone()
    connection.execute(
        "INSERT INTO audit_log (user_id, action, entity_type, entity_id, details) VALUES (%s, 'register_ml_model', 'ml_model', %s, %s)",
        (actor_user_id, row["model_id"], Json({"model_name": payload.model_name, "version": payload.version})),
    )
    return dict(row)


def deploy_model(connection: Any, model_id: int, actor_user_id: int) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM ml_model WHERE model_id = %s", (model_id,)).fetchone()
    if row is None:
        raise ValueError(f"ML model {model_id} does not exist")
    model_path = Path(row["model_path"])
    if not model_path.is_absolute():
        model_path = get_settings().project_root / model_path
    try:
        model_path.resolve().relative_to(get_settings().project_root.resolve())
    except ValueError as exc:
        raise ValueError("model_path must remain inside the project root") from exc
    if not model_path.exists():
        raise ValueError(f"ML model artifact does not exist: {model_path}")
    connection.execute(
        "UPDATE ml_model SET deployment_status = 'retired' WHERE model_name = %s AND deployment_status = 'deployed'",
        (row["model_name"],),
    )
    deployed = connection.execute(
        "UPDATE ml_model SET deployment_status = 'deployed' WHERE model_id = %s RETURNING *",
        (model_id,),
    ).fetchone()
    connection.execute(
        "INSERT INTO audit_log (user_id, action, entity_type, entity_id, details) VALUES (%s, 'deploy_ml_model', 'ml_model', %s, %s)",
        (actor_user_id, model_id, Json({"model_path": str(model_path)})),
    )
    return dict(deployed)
