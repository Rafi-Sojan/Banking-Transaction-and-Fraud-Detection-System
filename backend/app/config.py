"""Environment-backed application configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Small configuration object that does not require a settings plugin."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]
        self.app_name = os.getenv("APP_NAME", "Banking Fraud Detection API")
        self.environment = os.getenv("APP_ENV", "development")
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://banking_app:change_this_for_local_development@localhost:5432/banking_fraud",
        )
        self.postgres_connect_timeout = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "5"))
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.mongo_database = os.getenv("MONGO_DATABASE", "banking_fraud_events")
        self.mongo_timeout_ms = int(os.getenv("MONGO_TIMEOUT_MS", "1000"))
        configured_engine = os.getenv("FRAUD_ENGINE_PATH")
        self.fraud_engine_path = Path(configured_engine) if configured_engine else self._default_engine_path()
        self.fraud_engine_timeout_seconds = float(os.getenv("FRAUD_ENGINE_TIMEOUT_SECONDS", "2"))
        self.ml_enabled = _bool_env("ML_ENABLED", False)
        configured_ml_model = os.getenv("ML_MODEL_PATH")
        self.ml_model_path = Path(configured_ml_model) if configured_ml_model else self.project_root / "ml" / "models" / "paysim-baseline.joblib"
        self.ml_engine_timeout_seconds = float(os.getenv("ML_ENGINE_TIMEOUT_SECONDS", "3"))
        self.ml_rule_weight = float(os.getenv("ML_RULE_WEIGHT", "0.70"))
        self.ml_model_weight = float(os.getenv("ML_MODEL_WEIGHT", "0.30"))
        self.auth_required = _bool_env("AUTH_REQUIRED", True)
        self.jwt_secret = os.getenv("JWT_SECRET", "development-only-change-me")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiry_minutes = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ]
        self.alert_threshold = float(os.getenv("FRAUD_ALERT_THRESHOLD", "0.30"))
        self.hold_threshold = float(os.getenv("FRAUD_HOLD_THRESHOLD", "0.60"))
        self.rate_limit_enabled = _bool_env("RATE_LIMIT_ENABLED", True)
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        self.rate_limit_window_seconds = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        self.request_id_header = os.getenv("REQUEST_ID_HEADER", "X-Request-ID")
        if self.ml_rule_weight < 0 or self.ml_model_weight < 0 or abs((self.ml_rule_weight + self.ml_model_weight) - 1.0) > 1e-9:
            raise ValueError("ML_RULE_WEIGHT and ML_MODEL_WEIGHT must be non-negative and sum to 1")
        if not 1 <= self.rate_limit_per_minute <= 10000:
            raise ValueError("RATE_LIMIT_PER_MINUTE must be between 1 and 10000")
        if not 1 <= self.rate_limit_window_seconds <= 86400:
            raise ValueError("RATE_LIMIT_WINDOW_SECONDS must be between 1 and 86400")
        if self.environment.lower() in {"production", "prod"} and self.jwt_secret == "development-only-change-me":
            raise ValueError("JWT_SECRET must be changed in production")

    def _default_engine_path(self) -> Path:
        build_dir = self.project_root / "cpp" / "build"
        candidates = [build_dir / "fraud_engine.exe", build_dir / "fraud_engine"]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
