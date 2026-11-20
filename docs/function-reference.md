# Database and C++ Function Reference

Last updated: 2026-11-21

This document describes the behavior implemented by the database routines,
trigger functions, and C++ fraud-engine functions. It documents current
behavior, including validation, side effects, and error boundaries.

## 1. Database functions

### `process_transfer`

Defined in `database/procedures/transaction_procedures.sql`.

```sql
process_transfer(
    p_source_account_id BIGINT,
    p_destination_account_id BIGINT,
    p_amount NUMERIC(19,4),
    p_currency_code CHAR(3) DEFAULT 'USD',
    p_idempotency_key VARCHAR(160) DEFAULT NULL,
    p_initiated_by_user_id BIGINT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT
```

Purpose: atomically process a simulated account-to-account transfer and return
the created or previously existing `transaction_id`.

Validation:

- Source and destination accounts must differ.
- Amount must be non-null and greater than zero.
- Currency must be exactly three uppercase letters.
- Both accounts must exist and have `active` status.
- Both accounts must use the requested currency.
- The source account must have sufficient funds.

Processing:

1. A matching idempotency key returns the existing transaction ID without
   creating a duplicate or changing balances.
2. Reusing a key with different source, destination, or amount raises an error.
3. Both account rows are locked in ascending account-ID order.
4. A `completed` transfer is inserted.
5. The source balance is debited and the destination balance is credited.
6. The status-history trigger records the completed state.

Side effects: inserts into `transactions` and `transaction_status_history`, and
updates two `account.balance` values. The API should call this function instead
of performing balance arithmetic itself.

### `create_fraud_alert`

Defined in `database/procedures/fraud_procedures.sql`.

```sql
create_fraud_alert(
    p_transaction_id BIGINT,
    p_rule_score NUMERIC(8,6),
    p_ml_probability NUMERIC(8,6),
    p_combined_risk_score NUMERIC(8,6),
    p_risk_level VARCHAR(20),
    p_ml_model_id BIGINT DEFAULT NULL,
    p_reasons JSONB DEFAULT '[]'::jsonb
) RETURNS BIGINT
```

Purpose: persist a rule-engine/ML evaluation and return the new `alert_id`.

Behavior:

- Inserts a `fraud_alert` row with default status `open`.
- Foreign keys and score/risk-level constraints validate the input.
- If risk is `high` or `critical` and the transaction is `pending`, its status
  changes to `held`.
- Other transaction statuses are not changed.

This function records a risk signal. It does not confirm fraud and does not
automatically create an investigation.

### Held-transfer lifecycle functions

Defined in `database/procedures/transaction_lifecycle.sql`.

```sql
approve_held_transfer(p_transaction_id BIGINT, p_user_id BIGINT DEFAULT NULL) RETURNS BIGINT
decline_held_transfer(p_transaction_id BIGINT, p_user_id BIGINT DEFAULT NULL, p_reason TEXT DEFAULT NULL) RETURNS BIGINT
reverse_completed_transfer(
    p_transaction_id BIGINT,
    p_user_id BIGINT DEFAULT NULL,
    p_idempotency_key VARCHAR(160) DEFAULT NULL,
    p_reason TEXT DEFAULT NULL
) RETURNS BIGINT
```

`approve_held_transfer` locks the held transaction and both accounts in stable
order, validates active status, matching currency, and available funds, then
completes the transfer and returns the original ID. It rejects non-held
transactions and never silently bypasses account checks.

`decline_held_transfer` changes only an existing `held` transaction to
`declined`, preserving balances and optionally recording the reason in the
transaction description.

`reverse_completed_transfer` accepts only a completed transfer, creates a
separate completed `refund` in the opposite direction, restores both balances,
marks the original `reversed`, and returns the reversal ID. A supplied
idempotency key returns the existing reversal on retry.

### `close_investigation`

Defined in `database/procedures/fraud_procedures.sql`.

```sql
close_investigation(
    p_investigation_id BIGINT,
    p_user_id BIGINT,
    p_outcome VARCHAR(30),
    p_notes TEXT DEFAULT NULL
) RETURNS VOID
```

Accepted outcomes are `confirmed_fraud`, `legitimate`, and `inconclusive`.

Behavior:

1. Rejects unsupported outcomes.
2. Marks the investigation `closed` and stores outcome, notes, and close time.
3. Raises an error when the investigation does not exist.
4. Inserts an `investigation_action` with action type `closed`.
5. Marks the alert `confirmed` only for `confirmed_fraud`; otherwise marks it
   `resolved`.

Authorization is not performed here. FastAPI must authorize `p_user_id` before
calling the function.

### `set_updated_at`

Defined in `database/triggers/transaction_triggers.sql`.

```sql
set_updated_at() RETURNS TRIGGER
```

Before an update, sets `NEW.updated_at` to `CURRENT_TIMESTAMP` and returns the
updated row. It is attached to `customer`, `account`, `app_user`, `fraud_rule`,
`transactions`, `fraud_alert`, and `investigation`.

### `record_transaction_status_change`

Defined in `database/triggers/transaction_triggers.sql` and attached to
`transactions` for `AFTER INSERT OR UPDATE OF status`.

```sql
record_transaction_status_change() RETURNS TRIGGER
```

On insert, it records `old_status = NULL`. On a status update, it records a row
only when the status actually changes. It stores the transaction ID, old status,
new status, and timestamp in `transaction_status_history`.

### `prevent_final_transaction_mutation`

Defined in `database/triggers/transaction_triggers.sql` and attached to
`transactions` for `BEFORE UPDATE`.

```sql
prevent_final_transaction_mutation() RETURNS TRIGGER
```

When the old status is `completed`, `declined`, or `reversed`, it rejects edits
to source account, destination account, card, merchant, amount, currency,
transaction type, or transaction timestamp. This protects finalized financial
facts; a reversal should be modeled as a controlled workflow.

### `prevent_confirmed_alert_reopen`

Defined in `database/triggers/fraud_triggers.sql` and attached to
`fraud_alert` for `BEFORE UPDATE OF alert_status`.

```sql
prevent_confirmed_alert_reopen() RETURNS TRIGGER
```

When an alert is `confirmed`, it rejects changes back to `open`,
`under_review`, or `dismissed`, preserving the investigation outcome.

## 2. Database workflow summary

```text
process_transfer
  -> transactions + balance updates + status history

create_fraud_alert
  -> fraud_alert + optional pending-to-held transition

close_investigation
  -> investigation closure + investigation action + alert resolution

approve_held_transfer / decline_held_transfer / reverse_completed_transfer
  -> controlled transaction state change + account locking + status history
```

## 3. C++ engine functions

The C++ public API is in the `banking::fraud` namespace. The implementation is
under `cpp/include/` and `cpp/src/`.

### `FraudRules` constructor

```cpp
explicit FraudRules(RuleConfig config = {});
```

Creates a deterministic evaluator with configurable thresholds and risk
contributions. Defaults are:

| Configuration | Default |
|---|---:|
| Large amount threshold | `5000.0` |
| Rapid frequency threshold | `5` transactions in 10 minutes |
| Failed attempts threshold | `3` attempts in 1 hour |
| Minimum account age | `7` days |
| Contributions | `0.35`, `0.30`, `0.20`, `0.10`, `0.10`, `0.10`, `0.15` by rule |
| High-risk categories | `cash_advance`, `crypto`, `gambling` |

### `FraudRules::evaluate`

```cpp
FraudEvaluation evaluate(const TransactionFeatures& transaction) const;
```

Evaluates one typed transaction against these rules:

| Rule ID | Trigger condition |
|---|---|
| `large_amount` | Amount meets or exceeds the configured threshold. |
| `rapid_frequency` | 10-minute transaction count meets or exceeds the threshold. |
| `repeated_failed_attempts` | 1-hour failed-attempt count meets or exceeds the threshold. |
| `new_device` | `is_new_device` is true. |
| `new_location` | `is_new_location` is true. |
| `cross_border` | Country and home country are present and differ case-insensitively. |
| `new_account` | Account age is provided and is below the minimum age. |
| `high_risk_merchant` | Merchant category matches a configured category. |

Each triggered rule contributes its configured value. Contributions are summed
and capped at `1.0`. The result contains:

- `rule_score`: normalized deterministic score from `0.0` to `1.0`.
- `risk_level`: `low`, `medium`, `high`, or `critical`.
- `rules`: one result for every rule, including non-triggered rules.
- `reasons`: human-readable reasons for triggered rules only.

This function does not access a database, invoke ML, change balances, or make a
final authorization decision.

### `clampRiskScore`

```cpp
double clampRiskScore(double score);
```

Constrains a score to the inclusive range `[0.0, 1.0]`. It is used for rule
contributions and the final combined rule score.

### `riskLevelForScore`

```cpp
std::string riskLevelForScore(double score);
```

Clamps the input and maps it to a label:

| Score | Level |
|---|---|
| `< 0.30` | `low` |
| `>= 0.30` and `< 0.60` | `medium` |
| `>= 0.60` and `< 0.85` | `high` |
| `>= 0.85` | `critical` |

### `TransactionAnalyzer` constructor

```cpp
explicit TransactionAnalyzer(RuleConfig config = {});
```

Creates the public analyzer facade with default or caller-provided rule
configuration.

### `TransactionAnalyzer::analyze`

```cpp
FraudEvaluation analyze(const TransactionFeatures& transaction) const;
```

Evaluates a typed feature object by delegating to `FraudRules`. It performs no
JSON parsing and no I/O.

### `TransactionAnalyzer::analyzeJson`

```cpp
std::string analyzeJson(const std::string& input) const;
```

Provides the subprocess boundary for FastAPI.

Input requirements:

- One JSON object.
- Required fields: `transaction_id`, `amount`, and `transaction_type`.
- Optional fields: merchant category, countries, frequency counts, failed
  attempts, account age, new-device flag, and new-location flag.
- Optional `rule_config` object for thresholds and contributions.

Validation:

- Rejects malformed JSON and missing/incorrectly typed required fields.
- Rejects non-positive amounts.
- Rejects negative frequency, failed-attempt, or account-age values.
- Throws `std::invalid_argument` on parse or validation errors.

Output is one JSON object containing `transaction_id`, `rule_score`,
`risk_level`, all rule results, and triggered-rule reasons. The current parser
supports JSON objects with strings, numbers, booleans, and null values; input
arrays are not supported.

### Executable `main`

`cpp/src/main.cpp` implements the process protocol:

1. Reads all stdin as one JSON request.
2. Returns exit code `2` for empty or invalid input and writes the error to stderr.
3. Calls `TransactionAnalyzer::analyzeJson`.
4. Writes one JSON response to stdout and returns exit code `0` on success.

Example:

```bash
printf '%s\n' '{"transaction_id":"txn-1","amount":7500,"transaction_type":"card_purchase"}' \
  | ./cpp/build/fraud_engine
```

## 4. End-to-end responsibility boundary

```text
FastAPI validates request
        -> collects decision-time features
        -> TransactionAnalyzer::analyzeJson
        -> FraudRules::evaluate
        -> Python ML inference
        -> backend combines rule score and ML probability
        -> database.process_transfer / create_fraud_alert
```

The C++ engine is intentionally limited to deterministic rule evaluation. The
backend remains responsible for authentication, authorization, ML integration,
final simulated decisions, persistence, and audit policy.

## 5. Python ML engine

The ML implementation is under `ml/src/` and is documented in
[ml/README.md](../ml/README.md).

### `training_features` and `training_target`

These functions validate the PaySim training frame and select only approved,
non-leaking decision-time features: `amount`, `step`, and `type`. They reject
missing required columns, missing fraud classes, and non-binary targets.
`isFraud`, `isFlaggedFraud`, customer identifiers, and all balance columns are
excluded from model inputs.

### `train_model`

`ml.src.train.train_model(input_path, output_path, model_name, version)` builds
a preprocessing pipeline and class-balanced logistic-regression baseline,
evaluates it with precision, recall, F1, PR-AUC, and ROC-AUC, then persists a
versioned Joblib bundle. It does not download data or register a model as
deployed automatically.

### `validate_dataset`, `process_dataset`, and `run_pipeline`

`ml.src.pipeline.validate_dataset(input_path)` streams a PaySim CSV, verifies
the required raw columns, numeric domains, binary labels, non-empty transaction
types, and both fraud classes, then returns row, fraud-rate, type-count, and
feature-contract metadata. `process_dataset(input_path, output_path)` writes a
normalized training frame containing only `amount`, `step`, `type`, and
`isFraud`. `run_pipeline(input_path, output_dir, model_name, version)` composes
those steps with `train_model` and writes `pipeline-report.json`; it does not
mutate PostgreSQL or deploy the generated model.

### `MLInferenceEngine.predict`

Loads a validated Joblib bundle and returns one fraud probability together with
the model name and version. It rejects missing model files, incompatible
feature schemas, malformed input, and pipeline failures.

### `MLInferenceClient.predict`

The backend adapter invokes `python -m ml.src.main` with a JSON payload and
without shell interpolation. Missing or failing models raise an error; the
backend never converts an ML failure into a low-risk result.

### `combine_risk_scores`

Combines the C++ rule score and ML probability using `ML_RULE_WEIGHT` and
`ML_MODEL_WEIGHT`, which must be non-negative and sum to `1.0`. It returns the
normalized combined score and the `low`, `medium`, `high`, or `critical` risk
label used by alert and holding policy.

## 6. Backend service and API boundaries

The FastAPI routers are thin adapters over the following service functions:

| Backend function/API | Responsibility |
|---|---|
| `create_transfer` / `POST /transactions/transfers` | Validates the request, invokes C++ and optional ML evaluation, applies the configured hold/alert policy, persists PostgreSQL state, writes audit data, and attempts a supporting event. |
| `approve_held_transfer`, `decline_held_transfer`, `reverse_completed_transfer` / transaction lifecycle routes | Calls the matching PostgreSQL routine, records the actor and reason in `audit_log`, and returns the resulting transaction. |
| `create_user` / `POST /auth/users` | Administrator-only password hashing, role lookup, user insertion, and audit recording. Plaintext passwords never reach PostgreSQL. |
| `register_model`, `deploy_model` / `/models` | Stores model metadata, validates deployment paths inside the project root, enforces one deployed version per model name, and records model governance actions. Deployment requires an existing artifact. |
| `create_investigation`, `assign_investigation`, `add_investigation_action`, `close_investigation` / `/fraud/investigations` | Maintains alert review ownership, chronological investigator actions, final outcome, and audit entries. |
| `MongoEventStore.record_event`, `list_events` / `/events` | Best-effort supporting-event persistence and bounded investigator/admin reads. MongoDB failures do not change PostgreSQL ledger outcomes. |
| `/reports/transactions`, `/reports/fraud`, `/reports/audit` | Read-only investigator/admin projections over authoritative PostgreSQL views and audit records. |

Authentication and role checks occur in FastAPI dependencies. PostgreSQL
remains authoritative for balances, transaction status, alert state, and
model metadata; C++ and ML components never write financial records directly.
