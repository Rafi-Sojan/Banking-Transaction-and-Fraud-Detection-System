# Banking Transaction and Fraud Detection System

An academic simulation of banking transactions and fraud analysis. The system
is designed for synthetic data, deterministic experimentation, and explainable
software boundaries. It is not a production banking platform, does not connect
to real accounts, and must not be used to process real payments or make
production fraud decisions.

## Scope

The current implementation focuses on the backend core and its authoritative
data and rules services:

- FastAPI application, authentication, authorization, and API contracts.
- PostgreSQL as the authoritative store for accounts, balances, transactions,
  alerts, investigations, and audit records.
- MongoDB as optional supporting storage for behavioral and device events.
- C++17 deterministic fraud rules and an opt-in Python PaySim ML engine,
  both invoked through controlled JSON subprocesses.
- Automated unit, integration, C++ build, and database validation workflows.

Frontend API wiring remains separate. The ML engine is implemented but remains
disabled until a trained model is supplied. When enabled, an unavailable ML
component is an error, never a low-risk result.

## Architecture

```text
React/Vite frontend          FastAPI backend
        │                         │
        └────── REST/JSON ────────┤
                                  ├── Authentication and RBAC
                                  ├── Transaction/fraud services
                                  ├── C++ deterministic rule engine
                                  ├── PostgreSQL authoritative records
                                  └── MongoDB supporting events
```

PostgreSQL owns financial truth. Account balances are changed only through the
atomic `process_transfer` database function. The C++ engine evaluates
deterministic rules and returns explainable results; it does not access the
database or authorize payments. MongoDB events may support analysis but do not
replace PostgreSQL transaction state.

## Repository structure

```text
backend/                 FastAPI application and backend tests
cpp/                     C++17 fraud-rule engine and CTest target
database/                PostgreSQL schema, routines, views, and seed data
frontend/                React/Vite application scaffolding
ml/                      PaySim preprocessing, training, and inference engine
tests/integration/       PostgreSQL integration smoke tests
docs/                    Architecture, design, and implementation records
.github/workflows/       Backend, database, C++, frontend, and ML workflows
```

## Current implementation

### Backend

The backend provides:

- Authentication and JWT-based session handling.
- Role-based access for customers, investigators, and administrators.
- Customer and account read APIs.
- Atomic transfer processing with idempotency support.
- C++ rule-engine evaluation before transaction processing.
- Medium-risk alert persistence.
- High/critical-risk transaction holding without balance movement.
- Fraud-alert listing, investigation assignment/actions, and open/close workflows.
- Held-transfer approval/decline and completed-transfer reversal workflows.
- Administrator user provisioning and ML model registry/deployment metadata.
- Supporting MongoDB event query and PostgreSQL audit-report endpoints.
- Audit-log entries for transaction and investigation actions.
- PostgreSQL readiness, C++ engine, and MongoDB health checks.

See [backend/README.md](backend/README.md) for setup instructions and the
endpoint catalog.

### Database

The database includes schema creation, constraints, indexes, triggers,
procedures, reporting views, and synthetic seed data. Initialize it through the
single entry point:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/setup.sql
```

See [database/README.md](database/README.md) and
[docs/database-design.md](docs/database-design.md).

### C++ fraud engine

Build and test the C++ engine with CMake:

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build cpp/build --config Release --parallel
ctest --test-dir cpp/build --output-on-failure -C Release
```

The executable reads one JSON object from standard input and writes one JSON
result to standard output. See [cpp/README.md](cpp/README.md) for the contract
and rule behavior.

### Python ML engine

Install the ML dependencies and run the ML tests with:

```powershell
python -m pip install -r ml\requirements.txt
$env:PYTHONPATH = "."
python -m pytest ml\tests -q
```

Train the versioned PaySim baseline only with an authorized synthetic dataset:

```powershell
python -m ml.src.train `
  --input ml\data\raw\paysim.csv `
  --output ml\models\paysim-baseline.joblib `
  --metadata-output ml\models\paysim-baseline.json `
  --model-name paysim-baseline `
  --version 1.0.0
```

ML is activated in the backend with `ML_ENABLED=true` and a configured model
path. See [ml/README.md](ml/README.md) for the feature policy, JSON contract,
metrics, and deployment metadata requirements.

## Local backend setup

Create a virtual environment, install the backend dependencies, and start the
FastAPI application from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload
```

The backend expects PostgreSQL to be initialized and the C++ executable to be
available at `cpp/build/fraud_engine.exe` on Windows or
`cpp/build/fraud_engine` on Linux/macOS. Set `FRAUD_ENGINE_PATH` when using a
different location. Connection settings and secrets belong in a local `.env`
file; use [.env.example](.env.example) as the placeholder template.

The default configuration requires authentication. The database seed contains
synthetic customers and accounts but does not create demo application-user
credentials. Bootstrap an administrator through a controlled database
operation, then use the administrator-only provisioning endpoint.

## Test commands

Backend unit tests:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests -q
```

PostgreSQL integration tests:

```powershell
.\scripts\run_database_tests.ps1
```

C++ tests:

```bash
ctest --test-dir cpp/build --output-on-failure -C Release
```

Test locations are deliberately separated:

```text
backend/tests/          Python backend tests
cpp/tests/              C++ unit tests
tests/integration/      PostgreSQL smoke tests
```

## CI workflows

GitHub Actions workflows are available for:

- Backend dependency installation, PostgreSQL provisioning, C++ build, and API integration tests.
- PostgreSQL initialization and integration tests.
- C++ CMake build, CTest, and JSON contract smoke testing.
- Frontend build scaffolding.
- ML source validation scaffolding.

Each workflow supports manual dispatch and triggers on relevant source or
workflow-file changes. Frontend integration remains separate; ML source and
inference are covered independently until an authorized trained model is supplied.

## Documentation

- [Architecture](docs/architecture.md)
- [Implementation status](docs/implementation-status.md)
- [Database design](docs/database-design.md)
- [Database and C++ function reference](docs/function-reference.md)
- [Backend documentation](backend/README.md)
- [Database documentation](database/README.md)
- [C++ engine documentation](cpp/README.md)
- [ML engine documentation](ml/README.md)

## Development principles

- Use simulated data only.
- Keep PostgreSQL authoritative for balances and transaction state.
- Use decimal database types for financial values; do not use floating-point
  database balances.
- Keep deterministic rules explainable and auditable.
- Do not store plaintext passwords or raw card numbers.
- Keep secrets in environment variables and never commit `.env` files.
- Treat frontend and ML integration as separate boundaries until explicitly
  implemented and tested.
