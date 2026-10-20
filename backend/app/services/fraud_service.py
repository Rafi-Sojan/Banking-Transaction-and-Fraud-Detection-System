"""Deterministic C++ fraud-engine adapter and fraud persistence helpers."""

from __future__ import annotations

import json
import subprocess
from decimal import Decimal
from typing import Any

from psycopg.types.json import Json

from app.config import get_settings
from app.schemas.transaction import FraudEvaluationRead, TransactionFeatures


class FraudEngineError(RuntimeError):
    """Base class for controlled rule-engine failures."""


class FraudEngineUnavailable(FraudEngineError):
    """Raised when the configured C++ executable cannot be used."""


class FraudEngineClient:
    def evaluate(
        self,
        transaction_reference: str,
        amount: Decimal,
        transaction_type: str,
        features: TransactionFeatures,
    ) -> FraudEvaluationRead:
        settings = get_settings()
        executable = settings.fraud_engine_path
        if not executable.exists():
            raise FraudEngineUnavailable(f"Fraud engine executable not found: {executable}")

        payload = {
            "transaction_id": transaction_reference,
            "amount": float(amount),
            "transaction_type": transaction_type,
            **features.model_dump(),
        }
        try:
            completed = subprocess.run(
                [str(executable)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=settings.fraud_engine_timeout_seconds,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise FraudEngineUnavailable("Unable to execute the C++ fraud engine") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "unknown engine error"
            raise FraudEngineError(f"C++ fraud engine rejected the request: {detail}")
        try:
            return FraudEvaluationRead.model_validate(json.loads(completed.stdout))
        except (ValueError, TypeError) as exc:
            raise FraudEngineError("C++ fraud engine returned invalid JSON") from exc


def persist_fraud_alert(connection: Any, transaction_id: int, evaluation: FraudEvaluationRead) -> int:
    alert_row = connection.execute(
        """
        SELECT create_fraud_alert(%s, %s, NULL, %s, %s, NULL, %s) AS alert_id
        """,
        (
            transaction_id,
            evaluation.rule_score,
            evaluation.rule_score,
            evaluation.risk_level,
            Json(evaluation.reasons),
        ),
    ).fetchone()
    alert_id = int(alert_row["alert_id"])

    for rule in evaluation.rules:
        connection.execute(
            """
            INSERT INTO fraud_rule (rule_name, description, configuration)
            VALUES (%s, %s, %s)
            ON CONFLICT (rule_name, version) DO NOTHING
            """,
            (
                rule.rule_id,
                f"Deterministic C++ rule: {rule.rule_id}",
                Json({"risk_contribution": rule.risk_contribution}),
            ),
        )
        rule_row = connection.execute(
            "SELECT rule_id FROM fraud_rule WHERE rule_name = %s AND version = 1",
            (rule.rule_id,),
        ).fetchone()
        if rule_row is None:
            raise FraudEngineError(f"Unable to persist rule result for {rule.rule_id}")
        connection.execute(
            """
            INSERT INTO fraud_rule_result
                (alert_id, rule_id, triggered, risk_contribution, reason)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (alert_id, rule_row["rule_id"], rule.triggered, rule.risk_contribution, rule.reason or None),
        )
    return alert_id


def list_alerts(
    connection: Any,
    user: dict[str, Any],
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    params: list[Any] = [limit, offset]
    restriction = ""
    if user["role_name"] == "customer" and user.get("customer_id") is not None:
        restriction = "WHERE source_account.customer_id = %s"
        params = [user["customer_id"], limit, offset]
    rows = connection.execute(
        f"""
        SELECT fr.*
        FROM fraud_reports fr
        JOIN account source_account ON source_account.account_id = fr.source_account_id
        {restriction}
        ORDER BY fr.alert_created_at DESC, fr.alert_id DESC
        LIMIT %s OFFSET %s
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def get_alert(connection: Any, alert_id: int) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM fraud_reports WHERE alert_id = %s", (alert_id,)).fetchone()
    return dict(row) if row else None
