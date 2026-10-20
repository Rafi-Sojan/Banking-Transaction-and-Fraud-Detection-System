# C++ fraud rule engine

The C++ component is a deterministic, explainable fraud-rule engine. It is
intended to be called by the FastAPI backend through a controlled subprocess
interface. It does not make final payment-authorisation decisions and does not
claim to confirm fraud.

## Build and test

```bash
cmake -S cpp -B cpp/build -DBUILD_TESTING=ON
cmake --build cpp/build
ctest --test-dir cpp/build --output-on-failure
```

## JSON contract

The `fraud_engine` executable reads one JSON object from stdin and writes one
JSON object to stdout. Invalid input produces a non-zero exit code and an error
on stderr.

Example input:

```json
{
  "transaction_id": "txn-1001",
  "amount": 7500.0,
  "transaction_type": "card_purchase",
  "merchant_category": "crypto",
  "transaction_count_10m": 6,
  "failed_attempts_1h": 1,
  "account_age_days": 30,
  "is_new_device": true,
  "is_new_location": false,
  "country": "GB",
  "home_country": "IN"
}
```

Required fields are `transaction_id`, `amount`, and `transaction_type`.
Optional feature fields default to neutral values. A `rule_config` object may
override thresholds and risk contributions for a request; production callers
should load these values from the authorized database configuration rather than
trusting arbitrary client input.

Example output shape:

```json
{
  "transaction_id": "txn-1001",
  "rule_score": 1.000000,
  "risk_level": "critical",
  "rules": [
    {
      "rule_id": "large_amount",
      "triggered": true,
      "risk_contribution": 0.35,
      "reason": "Transaction amount meets or exceeds the configured large-amount threshold"
    }
  ],
  "reasons": ["..."]
}
```

Risk levels are `low` (<0.30), `medium` (0.30–<0.60), `high` (0.60–<0.85),
and `critical` (≥0.85). The backend must combine this rule score with the ML
probability using its documented decision policy.

For a function-by-function explanation of the rule engine, JSON analyzer,
executable behavior, and corresponding database routines, see
[docs/function-reference.md](../docs/function-reference.md).
