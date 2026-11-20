"""Versioned ML inference engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

from ml.src.features import FEATURE_COLUMNS, online_features


@dataclass(frozen=True)
class Prediction:
    """Model output returned by the inference engine."""

    fraud_probability: float
    model_name: str
    version: str
    model_id: int | None = None


class ModelLoadError(RuntimeError):
    """Raised when a persisted model cannot be loaded safely."""


class MLInferenceEngine:
    """Load a versioned Joblib bundle and score one transaction at a time."""

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise ModelLoadError(f"ML model not found: {self.model_path}")
        try:
            bundle = joblib.load(self.model_path)
        except Exception as exc:  # pragma: no cover - serializer-specific failures
            raise ModelLoadError(f"Unable to load ML model: {self.model_path}") from exc
        if not isinstance(bundle, dict) or "pipeline" not in bundle:
            raise ModelLoadError("ML model bundle must contain a pipeline")
        if tuple(bundle.get("feature_columns", ())) != FEATURE_COLUMNS:
            raise ModelLoadError("ML model feature schema does not match the engine contract")
        self._pipeline = bundle["pipeline"]
        self.model_name = str(bundle.get("model_name", "paysim-baseline"))
        self.version = str(bundle.get("version", "unknown"))

    def predict(self, payload: dict[str, Any]) -> Prediction:
        """Return a fraud probability for one validated JSON payload."""

        frame = online_features(payload)
        try:
            probabilities = self._pipeline.predict_proba(frame)
            probability = float(probabilities[0][1])
        except Exception as exc:
            raise ModelLoadError("ML pipeline could not score the transaction") from exc
        return Prediction(
            fraud_probability=max(0.0, min(probability, 1.0)),
            model_name=self.model_name,
            version=self.version,
        )

