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
        self._collection.create_index([("event_type", 1), ("occurred_at", -1)])
        self._collection.create_index([("occurred_at", -1)])
        self._collection.create_index([("payload.transaction_id", 1), ("occurred_at", -1)])
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

    def list_events(
        self,
        event_type: str | None = None,
        transaction_id: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        try:
            query: dict[str, Any] = {}
            if event_type:
                query["event_type"] = event_type
            if transaction_id is not None:
                query["payload.transaction_id"] = transaction_id
            rows = self._collection_for_events().find(query, {"_id": 0}).sort("occurred_at", -1).limit(limit)
            return list(rows)
        except Exception as exc:
            logger.warning("Unable to read supporting events: %s", exc)
            return []


@lru_cache(maxsize=1)
def get_event_store() -> MongoEventStore:
    return MongoEventStore()
