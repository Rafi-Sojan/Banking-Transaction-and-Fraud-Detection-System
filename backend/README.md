# Backend

The backend is the application coordinator for the simulated banking and fraud
detection system. It owns the HTTP API, authentication, PostgreSQL workflow,
MongoDB supporting-event writes, and the deterministic C++ rule-engine call.
Frontend wiring and ML inference are intentionally outside this implementation
scope.

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
└── utils/                  Password, JWT, and validation helpers
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

## Implemented endpoints

- `POST /api/v1/auth/login` and `GET /api/v1/auth/me`
- `GET /api/v1/customers` and `GET /api/v1/customers/{id}`
- `GET /api/v1/accounts` and `GET /api/v1/accounts/{id}`
- `POST /api/v1/transactions/transfers`
- `GET /api/v1/transactions` and `GET /api/v1/transactions/{id}`
- `GET /api/v1/fraud/alerts`
- `POST /api/v1/fraud/alerts/{id}/investigations`
- `POST /api/v1/fraud/investigations/{id}/close`
- Investigator/admin transaction and fraud reports
- `GET /health/live` and `GET /health/ready`

## Transaction behavior

1. The API validates the transfer request.
2. The backend sends decision-time features to the C++ engine without shell
   interpolation.
3. Low-risk transfers call PostgreSQL's atomic `process_transfer` function.
4. Medium-risk transfers complete but can receive a persisted fraud alert.
5. High/critical-risk transfers are inserted as pending and held by
   `create_fraud_alert`; balances are not changed.
6. Rule-level results are stored in `fraud_rule_result` for explainability.
7. Transfer and investigation actions are recorded in `audit_log`.
8. A supporting event is attempted in MongoDB after PostgreSQL commits.

The backend never treats an unavailable fraud engine as low risk, and MongoDB
does not become a second source of truth for balances or transaction state.
