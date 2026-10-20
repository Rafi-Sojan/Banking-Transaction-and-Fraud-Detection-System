# Implementation Status

Last updated: 2026-10-21

This document records the implementation completed in the repository so far.
The system remains an academic simulation. It does not connect to real bank
accounts, process real payments, or provide production-grade fraud decisions.

## Current status

| Area | Status | Notes |
|---|---|---|
| PostgreSQL database foundation | Implemented | Schema, constraints, indexes, triggers, routines, views, and synthetic seed data are available. |
| PostgreSQL integration tests | Implemented | Tests run transactionally and roll back their changes. |
| C++ deterministic fraud engine | Implemented | Library, executable, JSON contract, rules, and unit tests are available. |
| C++ CI workflow | Implemented | Builds, runs CTest, and validates the JSON contract. |
| FastAPI backend core | Implemented | API routers, auth, PostgreSQL transaction/fraud services, C++ adapter, investigation workflow, and health endpoints are available. |
| MongoDB event store | Partially implemented | Supporting event writes are attempted after PostgreSQL commits; event queries and richer event schemas remain pending. |
| Python ML pipeline | Not implemented | PaySim preprocessing, training, evaluation, and inference still need to be built. |
| Frontend workflow integration | Not implemented | The existing frontend is not yet connected to the completed database and fraud engine. |

## Database implementation

PostgreSQL is the authoritative store for simulated financial and fraud-workflow
records. The implementation is organized as follows:

- [database/schema/create_tables.sql](../database/schema/create_tables.sql) creates the core relational tables.
- [database/schema/constraints.sql](../database/schema/constraints.sql) adds domain, status, score, currency, and relationship checks.
- [database/schema/indexes.sql](../database/schema/indexes.sql) adds indexes for account, transaction, fraud-alert, investigation, and audit queries.
- [database/triggers/transaction_triggers.sql](../database/triggers/transaction_triggers.sql) manages timestamps, status history, and protection of final transaction fields.
- [database/triggers/fraud_triggers.sql](../database/triggers/fraud_triggers.sql) prevents reopening confirmed fraud alerts through invalid status transitions.
- [database/procedures/transaction_procedures.sql](../database/procedures/transaction_procedures.sql) provides the atomic `process_transfer` function.
- [database/procedures/fraud_procedures.sql](../database/procedures/fraud_procedures.sql) provides fraud-alert creation and investigation-closing helpers.
- [database/views/transaction_reports.sql](../database/views/transaction_reports.sql) provides transaction reporting data.
- [database/views/fraud_reports.sql](../database/views/fraud_reports.sql) provides fraud and investigation reporting data.
- [database/seed/data.sql](../database/seed/data.sql) provides synthetic demonstration data.
- [database/setup.sql](../database/setup.sql) is the single-entry initialization script.

The relational model includes the conceptual entities from the project design:
customers, accounts, branches, cards, merchants, merchant categories,
locations, application users, roles, transactions, fraud alerts,
investigations, investigation actions, fraud rules, ML-model metadata, and
audit logs.

Two supporting tables extend the conceptual ER model for implementation needs:

- `transaction_status_history` preserves transaction state changes.
- `fraud_rule_result` preserves rule-by-rule explanations for an alert.

Balances and amounts use `NUMERIC(19,4)`. The transfer function locks both
accounts in a stable order, checks account status, currency, and available
funds, applies both balance updates, and accepts an idempotency key.

## Database setup and local environment

The repository includes PostgreSQL and MongoDB services in
[docker-compose.yaml](../docker-compose.yaml). Connection placeholders are
documented in [.env.example](../.env.example); actual `.env` files remain
ignored and must not be committed.

The database can be initialized with:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/setup.sql
```

The detailed database instructions are in [database/README.md](../database/README.md).

For local verification, PostgreSQL 16.15 was installed and a project-local
cluster was created under `.postgres/`. The extracted local binaries are under
`tools/`. Both paths are ignored by Git and are development artifacts, not
project source files.

## Database tests

The database smoke tests are in
[tests/integration/database_smoke.sql](../tests/integration/database_smoke.sql)
and are run by [scripts/run_database_tests.ps1](../scripts/run_database_tests.ps1).

The tests cover:

- Expected table presence.
- Minimum synthetic seed data.
- Atomic transfer balance changes.
- Idempotent transfer retries.
- Transaction status-history recording.
- Rejection of negative transaction amounts.
- High-risk fraud-alert creation and transaction holding.

The tests run inside a transaction and finish with `ROLLBACK`, so test records
are not retained.

## C++ fraud engine

The C++ component is a dependency-free C++17 deterministic rule engine.

- [cpp/include/fraud_rules.hpp](../cpp/include/fraud_rules.hpp) defines transaction features, rule configuration, rule results, and evaluations.
- [cpp/src/fraud_rules.cpp](../cpp/src/fraud_rules.cpp) implements the explainable rules and risk-level thresholds.
- [cpp/include/transaction_analyzer.hpp](../cpp/include/transaction_analyzer.hpp) defines the analyzer interface.
- [cpp/src/transaction_analyzer.cpp](../cpp/src/transaction_analyzer.cpp) implements input validation, the restricted JSON parser, and JSON serialization.
- [cpp/src/main.cpp](../cpp/src/main.cpp) exposes the `fraud_engine` stdin/stdout executable.
- [cpp/tests/test_fraud_engine.cpp](../cpp/tests/test_fraud_engine.cpp) contains unit tests.
- [cpp/CMakeLists.txt](../cpp/CMakeLists.txt) defines the library, executable, and CTest target.
- [cpp/README.md](../cpp/README.md) documents the JSON contract and build commands.

Implemented rules:

1. `large_amount`
2. `rapid_frequency`
3. `repeated_failed_attempts`
4. `new_device`
5. `new_location`
6. `cross_border`
7. `new_account`
8. `high_risk_merchant`

The engine returns a normalized `rule_score`, a risk level, every rule result,
and human-readable reasons. Risk levels are `low`, `medium`, `high`, and
`critical`. The C++ score is not a final authorization decision and must later
be combined with the Python ML probability by the backend decision service.

## CI workflow changes

[.github/workflows/cpp.yml](../.github/workflows/cpp.yml) was updated to:

1. Support manual dispatch.
2. Run when C++ sources or the C++ workflow changes.
3. Configure CMake with testing enabled.
4. Build the C++ library, executable, and tests.
5. Run CTest with failure output.
6. Pipe a JSON transaction into `fraud_engine` and verify transaction ID and risk level output.

The backend implementation is now covered by its Python dependency set and unit tests. Frontend and ML workflows remain intentionally separate.

## Verification completed

The following checks have passed locally:

```text
PostgreSQL 16.15 accepting connections on 127.0.0.1:5432
18 expected PostgreSQL tables created
Database seed data loaded
Atomic transfer smoke test passed
Idempotent transfer retry returned the same transaction ID
Invalid negative amount rejected
Database setup rerun completed successfully
Database integration tests passed
Backend unit tests passed (3 tests)
FastAPI import and health checks passed
Backend-to-C++ fraud-engine smoke test passed
fraud_engine_tests: all tests passed
fraud_engine JSON smoke test returned the expected high-risk result
git diff --check passed (with normal Windows line-ending warnings)
```

The local host did not have CMake installed, so the C++ executable and tests
were compiled directly with the available GNU C++ compiler. The CMake/CTest
path is configured in CI and should be the authoritative cross-platform build
verification.

## Recommended next implementation steps

1. Add broader backend integration tests covering transaction and investigation lifecycles.
2. Add richer MongoDB event schemas and read APIs if supporting-event analysis requires them.
3. Implement the Python ML preprocessing, training, evaluation, model persistence, and inference interface.
4. Add the documented backend policy for combining C++ and ML scores after ML integration is approved.
5. Connect the frontend transaction and investigator workflows.
