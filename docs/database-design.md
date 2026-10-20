# Database Design

Last updated: 2026-10-21

The database layer uses PostgreSQL as the authoritative source for simulated
financial records and fraud investigations. MongoDB is reserved for supporting
behavioral, login, and device events; it must not replace PostgreSQL for
balances, transactions, or account state.

## Database components

The implementation is split into ordered SQL layers:

| Layer | File | Responsibility |
|---|---|---|
| Tables | `database/schema/create_tables.sql` | Creates the relational entities and foreign keys. |
| Constraints | `database/schema/constraints.sql` | Adds status, score, currency, amount, and relationship checks. |
| Indexes | `database/schema/indexes.sql` | Supports account, transaction, fraud, investigation, and audit queries. |
| Triggers | `database/triggers/` | Maintains timestamps, status history, and protected state transitions. |
| Functions | `database/procedures/` | Provides atomic transfers, fraud-alert creation, and investigation closing. |
| Views | `database/views/` | Provides transaction and fraud reporting projections. |
| Seed | `database/seed/data.sql` | Inserts repeatable synthetic demonstration data. |

Run all layers through [database/setup.sql](../database/setup.sql).

## Relational entities

### Core banking entities

- `customer` stores simulated customer profiles.
- `branch` stores simulated branch details and unique IFSC codes.
- `account` stores customer accounts, branch relationships, balances, currency, and status.
- `card` stores hashed card identifiers and account-linked card metadata. Raw card numbers are never stored.
- `merchant_category` classifies merchants.
- `location` stores merchant location metadata.
- `merchant` stores merchant identity, category, location, and status.
- `transactions` stores authoritative financial transaction records.

`transactions` is deliberately plural because `transaction` is a reserved SQL
keyword. Each transaction contains source and optional destination accounts,
optional card and merchant references, amount, currency, type, status,
timestamp, metadata, and an optional unique idempotency key.

### Identity and authorization entities

- `role` stores role names and JSON permissions.
- `app_user` stores login identity, password hash, role, optional customer link, and status.
- `audit_log` records security-sensitive, administrative, and system actions.

Application users are separate from customer profiles so staff users can exist
without being customers.

### Fraud and investigation entities

- `fraud_rule` stores versioned deterministic rule configuration.
- `ml_model` stores model versions, paths, evaluation metrics, deployment status, and metadata.
- `fraud_alert` stores rule score, ML probability, combined risk score, risk level, reasons, and review status.
- `fraud_rule_result` stores rule-by-rule evaluation history for explainability.
- `investigation` stores alert assignment, review status, outcome, notes, and timestamps.
- `investigation_action` stores the chronological action history for an investigation.
- `transaction_status_history` preserves every transaction status transition.

## Key relationships

```text
CUSTOMER 1 ──── M ACCOUNT M ──── 1 BRANCH
ACCOUNT   1 ──── M CARD
ACCOUNT   1 ──── M TRANSACTIONS (source)
ACCOUNT   1 ──── M TRANSACTIONS (destination)
MERCHANT_CATEGORY 1 ──── M MERCHANT M ──── 1 LOCATION
TRANSACTIONS 1 ──── M FRAUD_ALERT
FRAUD_ALERT 1 ──── M FRAUD_RULE_RESULT M ──── 1 FRAUD_RULE
FRAUD_ALERT 1 ──── M INVESTIGATION
INVESTIGATION 1 ──── M INVESTIGATION_ACTION
ROLE 1 ──── M APP_USER
APP_USER 1 ──── M INVESTIGATION_ACTION
APP_USER 1 ──── M AUDIT_LOG
ML_MODEL 1 ──── M FRAUD_ALERT
```

The active-investigation partial unique index prevents more than one open,
in-progress, or escalated investigation for the same alert while allowing
historical closed investigation records.

## Integrity rules

- Amounts and balances use `NUMERIC(19,4)`, never floating-point storage.
- Account balances cannot become negative.
- Transactions require positive amounts and supported transaction types.
- Source and destination accounts cannot be identical.
- Account and transaction currencies must use three uppercase letters.
- Account, user, alert, investigation, and model statuses are constrained to documented values.
- Risk scores and model metrics are constrained to the range 0 through 1.
- Idempotency keys are unique when present.
- Customer emails are unique case-insensitively.
- Usernames are stored in lowercase and unique case-insensitively.
- Passwords are represented only by password hashes.
- Foreign keys preserve relationships between financial and fraud records.
- Timestamp columns use `TIMESTAMPTZ` and default to the database current timestamp.

## Transaction processing

The `process_transfer` function is the database boundary for simulated account
transfers. It:

1. Validates amount, currency, and distinct accounts.
2. Returns the original transaction for a matching idempotency key.
3. Locks both accounts in ascending ID order to reduce deadlock risk.
4. Verifies that both accounts exist, are active, and use the requested currency.
5. Verifies sufficient source-account funds.
6. Inserts a completed transfer record.
7. Debits the source account and credits the destination account.
8. Lets the status-history trigger record the completed state.

The database trigger prevents financial fields on completed, declined, or
reversed transactions from being changed later. A reversal should be modeled
as a separate controlled workflow rather than rewriting the original record.

## Fraud workflow support

`create_fraud_alert` stores the rule and ML scores together with reasons and an
optional model reference. A high or critical alert changes a pending
transaction to `held`; it does not confirm fraud. Investigation outcomes remain
separate from model predictions and rule flags.

`close_investigation` records the final outcome, writes an investigation action,
and updates the alert to `confirmed` only for `confirmed_fraud`; other outcomes
resolve the alert without asserting fraud.

## Initialization and tests

Initialize the database with:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/setup.sql
```

Run integration tests with:

```powershell
.\scripts\run_database_tests.ps1
```

The tests verify the expected tables and seed data, atomic and idempotent
transfers, status history, invalid amount rejection, and high-risk alert
handling. They run inside a transaction and roll back all test records.

See [function-reference.md](function-reference.md) for exact parameters,
validation, side effects, and error behavior of each database function and
trigger function.

## Deliberate scope boundaries

- PostgreSQL owns authoritative financial state.
- MongoDB event storage is not yet implemented; only its intended boundary is defined.
- ML scores are stored as model output metadata and are not treated as confirmed fraud.
- Seed records are synthetic and contain no real customer, payment, or credential data.
- Migrations are currently represented by ordered, repeatable SQL layers; a versioned migration tool can be introduced when the backend repository layer is added.
