"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accounts, auth, customers, fraud, report, transactions
from app.config import get_settings
from app.databases.mongodb import get_event_store
from app.databases.postgres import get_connection

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

for router_module in (auth, accounts, customers, transactions, fraud, report):
    app.include_router(router_module.router, prefix="/api/v1")


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness() -> dict[str, object]:
    database_ready = False
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1")
            database_ready = True
    except Exception:
        database_ready = False
    engine_ready = settings.fraud_engine_path.exists()
    mongo_ready = get_event_store().ping()
    return {
        "status": "ok" if database_ready and engine_ready else "degraded",
        "postgresql": database_ready,
        "fraud_engine": engine_ready,
        "mongodb_events": mongo_ready,
    }
