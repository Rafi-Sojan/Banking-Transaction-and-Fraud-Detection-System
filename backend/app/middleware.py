"""Small application middleware for traceability and abuse control."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.services.rate_limit_service import RateLimitServiceError, check_rate_limit

logger = logging.getLogger("banking_fraud.request")


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)

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
            bucket_key = f"{key[0]}:{key[1]}"
            try:
                decision = await run_in_threadpool(
                    check_rate_limit,
                    bucket_key,
                    settings.rate_limit_per_minute,
                    settings.rate_limit_window_seconds,
                )
            except RateLimitServiceError as exc:
                return JSONResponse(
                    status_code=503,
                    content={"detail": str(exc), "request_id": request_id},
                    headers={settings.request_id_header: request_id},
                )
            if not decision.allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "request_id": request_id},
                    headers={settings.request_id_header: request_id, "Retry-After": str(decision.retry_after)},
                )
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
