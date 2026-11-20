# Backend

The backend is the application coordinator for the simulated banking and fraud
detection system. It owns the HTTP API, authentication, PostgreSQL workflow,
MongoDB supporting-event writes, and the deterministic C++ rule-engine call.
Frontend wiring remains separate. Python ML inference is implemented as an
opt-in engine and is disabled until a trained model is configured.

## Structure

```text
backend/app/
├── main.py                 FastAPI app and health endpoints
├── config.py               Environment-backed settings
├── api/                    HTTP routers
├── databases/              PostgreSQL and MongoDB clients
├── schemas/                Pydantic request/response contracts
├── models/                 Domain model boundary documentation
├── services/               Transaction, fraud, and investigation workflows
└── utils/                  Password, JWT, validation, and request helpers
```

## Local setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload
```

The PostgreSQL schema must already be initialized with
`database/setup.sql`. The C++ executable must be built at
`cpp/build/fraud_engine.exe` or configured explicitly with `FRAUD_ENGINE_PATH`.

To enable ML inference, install `ml\requirements.txt` into the same Python
environment, train a model, and set `ML_ENABLED=true` and `ML_MODEL_PATH`.

## Implemented endpoints

- `POST /api/v1/auth/login` and `GET /api/v1/auth/me`
- `POST /api/v1/auth/users` and `GET /api/v1/auth/users`
- `GET /api/v1/customers` and `GET /api/v1/customers/{id}`
- `GET /api/v1/accounts` and `GET /api/v1/accounts/{id}`
- `POST /api/v1/transactions/transfers`
- `GET /api/v1/transactions` and `GET /api/v1/transactions/{id}`
- `POST /api/v1/transactions/{id}/approve`, `/decline`, and `/reverse`
- `GET /api/v1/fraud/alerts`
- `POST /api/v1/fraud/alerts/{id}/investigations`
- `POST /api/v1/fraud/investigations/{id}/close`
- Investigation list/detail, assignment, action, and alert-status endpoints
- `GET /api/v1/models`, model registration, and administrator-only deployment
- `GET /api/v1/events` for optional MongoDB supporting events
- `GET /api/v1/reports/audit` plus transaction/fraud reports
- Investigator/admin transaction and fraud reports
- `GET /health/live` and `GET /health/ready`

## Transaction behavior

1. The API validates the transfer request.
2. The backend sends decision-time features to the C++ engine without shell
   interpolation.
3. When `ML_ENABLED=true`, the backend invokes the versioned Python ML engine
   and combines its probability with the C++ rule score.
4. Low-risk transfers call PostgreSQL's atomic `process_transfer` function.
5. Medium-risk transfers complete but can receive a persisted fraud alert.
6. High/critical-risk transfers are inserted as pending and held by
   `create_fraud_alert`; balances are not changed.
7. Rule-level results are stored in `fraud_rule_result` for explainability.
8. Transfer and investigation actions are recorded in `audit_log`.
9. A supporting event is attempted in MongoDB after PostgreSQL commits.
10. Investigators and administrators can approve, decline, or reverse transfers;
    every lifecycle action is auditable.

Request IDs are returned in `X-Request-ID`. Login and transfer writes have a
configurable in-memory rate limit for this simulation (`RATE_LIMIT_*`).

The backend never treats an unavailable fraud engine as low risk, and MongoDB
does not become a second source of truth for balances or transaction state.
