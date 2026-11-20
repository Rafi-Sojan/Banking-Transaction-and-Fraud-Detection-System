"""PostgreSQL-backed rate limiting shared by all API worker processes."""

from __future__ import annotations

from dataclasses import dataclass

from app.databases.postgres import get_connection


class RateLimitServiceError(RuntimeError):
    """Raised when the shared rate-limit store cannot be reached."""


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of one atomic rate-limit bucket update."""

    allowed: bool
    retry_after: int


def check_rate_limit(bucket_key: str, limit: int, window_seconds: int) -> RateLimitResult:
    """Atomically count a request in PostgreSQL and return the enforcement decision."""

    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO rate_limit_bucket (bucket_key, window_started_at, request_count)
                VALUES (%s, CURRENT_TIMESTAMP, 1)
                ON CONFLICT (bucket_key) DO UPDATE
                SET window_started_at = CASE
                        WHEN rate_limit_bucket.window_started_at <= CURRENT_TIMESTAMP
                            - INTERVAL '1 second' * %s
                        THEN CURRENT_TIMESTAMP
                        ELSE rate_limit_bucket.window_started_at
                    END,
                    request_count = CASE
                        WHEN rate_limit_bucket.window_started_at <= CURRENT_TIMESTAMP
                            - INTERVAL '1 second' * %s
                        THEN 1
                        ELSE rate_limit_bucket.request_count + 1
                    END
                RETURNING request_count,
                    GREATEST(
                        0,
                        CEIL(EXTRACT(EPOCH FROM (
                            window_started_at + INTERVAL '1 second' * %s - CURRENT_TIMESTAMP
                        )))
                    )::INTEGER AS retry_after
                """,
                (bucket_key, window_seconds, window_seconds, window_seconds),
            ).fetchone()
        return RateLimitResult(
            allowed=int(row["request_count"]) <= limit,
            retry_after=max(1, int(row["retry_after"] or window_seconds)),
        )
    except Exception as exc:
        raise RateLimitServiceError("Shared rate limiter is unavailable") from exc
