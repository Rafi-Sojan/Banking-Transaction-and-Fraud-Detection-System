# Banking Transaction and Fraud Detection System

An academic full-stack simulation for banking transactions and fraud detection.
It is not a production banking platform and uses simulated data only.

## Project areas

- `backend/` — FastAPI application core, transaction/fraud services, auth, database clients, and C++ adapter.
- `frontend/` — React/Vite application scaffolding.
- `database/` — PostgreSQL schema, routines, reporting views, seed data, and setup instructions.
- `cpp/` — deterministic C++ fraud-rule engine and JSON subprocess contract.
- `ml/` — reserved for the PaySim preprocessing, training, evaluation, and inference pipeline.
- `tests/` — integration tests, currently including PostgreSQL database smoke tests.
- `docs/` — architecture and implementation documentation.

## Documentation

- [Implementation status](docs/implementation-status.md)
- [Database and C++ function reference](docs/function-reference.md)
- [Database documentation](database/README.md)
- [C++ engine documentation](cpp/README.md)
- [Architecture](docs/architecture.md)
- [Database design](docs/database-design.md)
- [Backend documentation](backend/README.md)

## Current quick starts

Initialize PostgreSQL:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/setup.sql
```

Run the database integration tests from PowerShell:

```powershell
.\scripts\run_database_tests.ps1
```

Build and test the C++ engine:

```bash
cmake -S cpp -B cpp/build -DBUILD_TESTING=ON
cmake --build cpp/build
ctest --test-dir cpp/build --output-on-failure
```

See [docs/implementation-status.md](docs/implementation-status.md) for the
completed changes, verification results, and remaining implementation work.
