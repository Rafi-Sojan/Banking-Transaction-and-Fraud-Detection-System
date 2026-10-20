"""Optional MongoDB event storage.

MongoDB is deliberately non-authoritative. A failed event write is logged and
reported to the caller as ``False``; it must not roll back a PostgreSQL ledger
operation that has already committed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class MongoEventStore:
    def __init__(self) -> None:
        self._client: Any = None
        self._collection: Any = None

    def _collection_for_events(self) -> Any:
        if self._collection is not None:
            return self._collection
        try:
            from pymongo import MongoClient
        except ImportError as exc:  # pragma: no cover - dependency install issue
            raise RuntimeError("pymongo is required for MongoDB event storage") from exc

        settings = get_settings()
        self._client = MongoClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=settings.mongo_timeout_ms,
            connectTimeoutMS=settings.mongo_timeout_ms,
        )
        self._collection = self._client[settings.mongo_database]["events"]
        return self._collection

    def record_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        try:
            collection = self._collection_for_events()
            collection.insert_one(
                {
                    "event_type": event_type,
                    "occurred_at": datetime.now(timezone.utc),
                    "payload": payload,
                }
            )
            return True
        except Exception as exc:  # Mongo is supporting infrastructure only.
            logger.warning("Unable to persist supporting event %s: %s", event_type, exc)
            return False

    def ping(self) -> bool:
        try:
            self._collection_for_events().database.client.admin.command("ping")
            return True
        except Exception:
            return False


@lru_cache(maxsize=1)
def get_event_store() -> MongoEventStore:
    return MongoEventStore()
