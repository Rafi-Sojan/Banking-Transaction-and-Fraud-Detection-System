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
