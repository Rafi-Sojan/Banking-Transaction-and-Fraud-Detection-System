# Database

The PostgreSQL database is the authoritative store for simulated financial and
fraud-workflow records. MongoDB is reserved for supporting behavioral and device
events and is not represented by the relational schema in this directory.

## Initialization order

The recommended entry point is `database/setup.sql`, which runs the scripts in
the required order:

```text
schema/create_tables.sql
schema/constraints.sql
schema/indexes.sql
triggers/transaction_triggers.sql
triggers/fraud_triggers.sql
procedures/transaction_procedures.sql
procedures/fraud_procedures.sql
views/transaction_reports.sql
views/fraud_reports.sql
seed/data.sql
```

Example:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/setup.sql
```

The individual files are kept separate so schema, constraints, indexes,
triggers, routines, views, and seed data can be reviewed independently.

## Tests

Run the PostgreSQL integration smoke tests from PowerShell:

```powershell
.\scripts\run_database_tests.ps1
```

The test suite validates schema presence, seed data, atomic transfers,
idempotency, transaction status history, constraint enforcement, and high-risk
fraud-alert handling. Tests run inside a transaction and roll back at the end.

For exact parameters, validation, side effects, and error conditions of every
database routine and trigger function, see
[docs/function-reference.md](../docs/function-reference.md).

## Design decisions

- `transactions` is used instead of the reserved SQL word `transaction`.
- `transaction_status_history` and `fraud_rule_result` extend the conceptual ER
  model to preserve state changes and rule-level explainability.
- Balances and amounts use `NUMERIC(19,4)` and are changed by the atomic
  `process_transfer` function, not by direct API-side arithmetic.
- The seed data is synthetic and contains no real credentials or financial data.
- The seeded ML model is explicitly offline and has no fabricated metrics.
