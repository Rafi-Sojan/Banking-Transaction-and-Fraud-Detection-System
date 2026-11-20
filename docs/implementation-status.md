# Implementation Status

Last updated: 2026-11-21

This document records the implementation completed in the repository so far.
The system remains an academic simulation. It does not connect to real bank
accounts, process real payments, or provide production-grade fraud decisions.

## Current status

| Area | Status | Notes |
|---|---|---|
| PostgreSQL database foundation | Implemented | Schema, constraints, indexes, triggers, routines, views, and synthetic seed data are available. |
| PostgreSQL integration tests | Implemented | Tests run transactionally and roll back their changes, including the shared rate-limit table. |
| C++ deterministic fraud engine | Implemented | Library, executable, JSON contract, rules, and unit tests are available. |
| C++ CI workflow | Implemented | Builds, runs CTest, and validates the JSON contract. |
| FastAPI backend core | Implemented | API routers, auth, PostgreSQL transaction/fraud services, C++ adapter, investigation workflow, and health endpoints are available. |
| MongoDB event store | Implemented, supporting | Best-effort writes, event indexes, bounded query API, and health reporting are available; PostgreSQL remains authoritative. |
| Python ML engine | Implemented, opt-in | Leakage-safe PaySim feature contract, temporal validation, validation-period threshold tuning, processing/training pipeline, fixture-backed model tests, Joblib model bundle, JSON inference process, backend adapter, score-combination policy, and local model registration are implemented. Raw data and artifacts remain uncommitted. |
| Frontend workflow integration | Implemented | React client provides authenticated dashboard, account/customer views, transfers, transaction history, fraud-alert review, and investigator actions through the FastAPI API. |
| Shared rate limiting | Implemented | PostgreSQL-backed atomic buckets are shared across backend worker processes for login and transfer writes. |

## Database implementation

PostgreSQL is the authoritative store for simulated financial and fraud-workflow
records. The implementation is organized as follows:

- [database/schema/create_tables.sql](../database/schema/create_tables.sql) creates the core relational tables.
- [database/schema/constraints.sql](../database/schema/constraints.sql) adds domain, status, score, currency, and relationship checks.
- [database/schema/indexes.sql](../database/schema/indexes.sql) adds indexes for account, transaction, fraud-alert, investigation, and audit queries.
- [database/triggers/transaction_triggers.sql](../database/triggers/transaction_triggers.sql) manages timestamps, status history, and protection of final transaction fields.
- [database/triggers/fraud_triggers.sql](../database/triggers/fraud_triggers.sql) prevents reopening confirmed fraud alerts through invalid status transitions.
- [database/procedures/transaction_procedures.sql](../database/procedures/transaction_procedures.sql) provides the atomic `process_transfer` function.
- [database/procedures/transaction_lifecycle.sql](../database/procedures/transaction_lifecycle.sql) provides held approval/decline and completed-transfer reversal functions.
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
- Held approval, decline, reversal, and balance-restoration lifecycle behavior.

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
`critical`. The C++ score is not a final authorization decision. When ML is
enabled, the backend combines it with the Python ML probability using
configured weights.

## CI workflow changes

[.github/workflows/cpp.yml](../.github/workflows/cpp.yml) was updated to:

1. Support manual dispatch.
2. Run when C++ sources or the C++ workflow changes.
3. Configure CMake with testing enabled.
4. Build the C++ library, executable, and tests.
5. Run CTest with failure output.
6. Pipe a JSON transaction into `fraud_engine` and verify transaction ID and risk level output.

The backend implementation is covered by its Python dependency set, unit tests,
and database-backed API integration tests. ML has its own validation,
processing, model-testing, training, inference, and CI workflow. The frontend
remains a separate client boundary and consumes backend contracts without
owning ledger, rules, ML, or persistence logic.

## Verification completed

The following checks have passed locally:

```text
PostgreSQL 16.15 accepting connections on 127.0.0.1:5432
19 expected PostgreSQL tables created
Database seed data loaded
Atomic transfer smoke test passed
Idempotent transfer retry returned the same transaction ID
Invalid negative amount rejected
Database setup rerun completed successfully
Database integration tests passed
Backend tests passed (8 tests, including database-backed API integration)
FastAPI import and health checks passed
Backend-to-C++ fraud-engine smoke test passed
ML engine unit, JSON-contract, and pipeline tests passed (5 tests)
PaySim full dataset validated, processed, and temporally trained
ML-enabled backend integration passed (8 tests)
PaySim baseline version 1.1.0 registered and deployed in local PostgreSQL metadata
ML temporal validation and threshold-tuning pipeline implemented
Frontend production build passed
Shared PostgreSQL rate-limit bucket added
fraud_engine_tests: all tests passed
fraud_engine JSON smoke test returned the expected high-risk result
git diff --check passed (with normal Windows line-ending warnings)
```

The local host did not have CMake installed, so the C++ executable and tests
were compiled directly with the available GNU C++ compiler. The CMake/CTest
path is configured in CI and should be the authoritative cross-platform build
verification.

## Remaining scoped work

1. Push the changes and confirm the GitHub Actions ML, frontend, backend, and database workflows pass in GitHub.
2. Add optional frontend enhancements such as pagination, account filtering, and live refresh.
