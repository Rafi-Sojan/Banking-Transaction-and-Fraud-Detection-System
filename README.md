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
- C++17 deterministic fraud rules invoked through a controlled JSON subprocess.
- Automated unit, integration, C++ build, and database validation workflows.

Frontend API wiring and Python ML integration are intentionally separate work
streams. The backend does not treat an unavailable ML component as a low-risk
decision, and the current transaction path uses the deterministic C++ rules
engine only.

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
ml/                      Reserved PaySim/ML pipeline
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
- Fraud-alert listing and investigation open/close workflows.
- Audit-log entries for transaction and investigation actions.
- PostgreSQL readiness and C++ engine health checks.

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
credentials. Add an `app_user` record with a generated password hash before
using the login endpoint.

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

- Backend dependency installation and Python tests.
- PostgreSQL initialization and integration tests.
- C++ CMake build, CTest, and JSON contract smoke testing.
- Frontend build scaffolding.
- ML source validation scaffolding.

Each workflow supports manual dispatch and triggers on relevant source or
workflow-file changes. Frontend and ML workflows remain limited until those
components are implemented.

## Documentation

- [Architecture](docs/architecture.md)
- [Implementation status](docs/implementation-status.md)
- [Database design](docs/database-design.md)
- [Database and C++ function reference](docs/function-reference.md)
- [Backend documentation](backend/README.md)
- [Database documentation](database/README.md)
- [C++ engine documentation](cpp/README.md)

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
