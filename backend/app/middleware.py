"""Small application middleware for traceability and abuse control."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

logger = logging.getLogger("banking_fraud.request")


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._request_times: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        request_id = request.headers.get(settings.request_id_header) or str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        key = (request.client.host if request.client else "unknown", request.url.path)
        protected_write = request.method in {"POST", "PATCH", "PUT", "DELETE"} and (
            request.url.path.endswith("/auth/login") or request.url.path.endswith("/transactions/transfers")
        )
        if settings.rate_limit_enabled and protected_write:
            now = time.monotonic()
            bucket = self._request_times[key]
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()
            if len(bucket) >= settings.rate_limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "request_id": request_id},
                    headers={settings.request_id_header: request_id, "Retry-After": "60"},
                )
            bucket.append(now)
        response = await call_next(request)
        response.headers[settings.request_id_header] = request_id
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response
