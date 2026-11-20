"""Controlled subprocess adapter for the Python ML inference engine."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal
from typing import Any

from app.config import get_settings
from app.schemas.transaction import MLPredictionRead, TransactionFeatures


class MLEngineError(RuntimeError):
    """Base class for controlled ML-engine failures."""


class MLEngineUnavailable(MLEngineError):
    """Raised when the configured model or Python engine cannot be used."""


class MLInferenceClient:
    """Invoke ``ml.src.main`` without shell-string interpolation."""

    def predict(
        self,
        transaction_reference: str,
        amount: Decimal,
        transaction_type: str,
        features: TransactionFeatures,
    ) -> MLPredictionRead:
        settings = get_settings()
        if not settings.ml_model_path.exists():
            raise MLEngineUnavailable(f"ML model not found: {settings.ml_model_path}")
        payload: dict[str, Any] = {
            "transaction_id": transaction_reference,
            "amount": float(amount),
            "transaction_type": transaction_type,
            **features.model_dump(),
        }
        environment = os.environ.copy()
        environment.setdefault("PYTHONPATH", str(settings.project_root))
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ml.src.main",
                    "--model",
                    str(settings.ml_model_path),
                ],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=settings.ml_engine_timeout_seconds,
                check=False,
                shell=False,
                cwd=settings.project_root,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MLEngineUnavailable("Unable to execute the Python ML engine") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "unknown ML engine error"
            raise MLEngineError(f"Python ML engine rejected the request: {detail}")
        try:
            return MLPredictionRead.model_validate(json.loads(completed.stdout))
        except (ValueError, TypeError) as exc:
            raise MLEngineError("Python ML engine returned invalid JSON") from exc


def combine_risk_scores(rule_score: float, ml_probability: float | None) -> tuple[float, str]:
    """Apply the configured rule/model weighting and return a risk label."""

    settings = get_settings()
    if ml_probability is None:
        combined = rule_score
    else:
        combined = (settings.ml_rule_weight * rule_score) + (settings.ml_model_weight * ml_probability)
    combined = max(0.0, min(float(combined), 1.0))
    if combined >= 0.85:
        return combined, "critical"
    if combined >= 0.60:
        return combined, "high"
    if combined >= 0.30:
        return combined, "medium"
    return combined, "low"


def deployed_model_id(connection: Any, prediction: MLPredictionRead) -> int | None:
    """Resolve the authoritative PostgreSQL model metadata ID, if registered."""

    row = connection.execute(
        """
        SELECT model_id
        FROM ml_model
        WHERE model_name = %s AND version = %s AND deployment_status = 'deployed'
        LIMIT 1
        """,
        (prediction.model_name, prediction.version),
    ).fetchone()
    return int(row["model_id"]) if row else None

