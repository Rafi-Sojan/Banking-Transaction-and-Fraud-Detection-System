# ML Engine

The ML component provides a reproducible PaySim baseline and a controlled JSON
inference process. It is separate from the C++ deterministic rules engine and
does not authorize transactions or write to PostgreSQL directly.

The acquired dataset and provenance record are documented in
[DATASET_CARD.md](DATASET_CARD.md). Raw data and trained artifacts are ignored
by Git.

## Feature policy

Training uses only non-leaking decision-time PaySim features:

- `amount`
- `step`
- `type`

The target `isFraud`, simulator flag `isFlaggedFraud`, customer identifiers,
and all four PaySim balance columns are excluded. The dataset card warns that
the balances can leak the fraud outcome because fraudulent transactions are
cancelled. The trainer requires both fraud classes, uses ordered train,
validation, and test periods by `step`, tunes a decision threshold on the
validation period, and reports precision, recall, F1, PR-AUC, and ROC-AUC on
the later test period.

## Train a model

PaySim data is not committed to the repository. After obtaining an authorized
synthetic PaySim CSV, run:

```powershell
$env:PYTHONPATH = "."
python -m ml.src.train `
  --input ml\data\raw\PS_20174392719_1491204439457_log.csv `
  --output ml\models\paysim-baseline.joblib `
  --metadata-output ml\models\paysim-baseline.json `
  --model-name paysim-baseline `
  --version 1.0.0
```

Model files are ignored by Git. The generated bundle contains the preprocessing
pipeline, classifier, feature schema, version, dataset name, and evaluation
metrics.

## Inference contract

The engine reads one JSON object from standard input:

```json
{
  "transaction_id": "txn-1001",
  "amount": 7500.0,
  "transaction_type": "TRANSFER",
  "step": 120
}
```

Invoke it with:

```powershell
python -m ml.src.main --model ml\models\paysim-baseline.joblib
```

It returns:

```json
{
  "fraud_probability": 0.812345,
  "model_name": "paysim-baseline",
  "version": "1.0.0"
}
```

Malformed input, missing models, and inference failures return exit code `2`
and write an error to stderr.

## Backend activation

The backend keeps ML disabled by default even though the local baseline has
been trained and registered. To enable it, configure:

```text
ML_ENABLED=true
ML_MODEL_PATH=ml/models/paysim-baseline.joblib
ML_RULE_WEIGHT=0.70
ML_MODEL_WEIGHT=0.30
```

When enabled, the backend combines the C++ rule score and ML probability using
the configured weights. If the model is unavailable or fails, the request
returns an error; it is never silently treated as low risk. Register the model
as `deployed` in PostgreSQL for `fraud_alert.ml_model_id` to reference it.

## Push-time validation pipeline

The ML workflow runs on pushes and pull requests that touch `ml/` or the ML
workflow itself. It performs the following checks in order:

1. Installs the pinned ML dependencies from `ml/requirements.txt`.
2. Compiles the ML source and runs the unit, CLI, and pipeline tests.
3. Validates the committed PaySim-shaped fixture, normalizes it to the
   leakage-safe feature frame, trains a short-lived model, and writes a JSON
   report with dataset counts and evaluation metrics.
4. Uploads the processed fixture, model bundle, and report as a workflow
   artifact. The real PaySim CSV and local model artifacts remain ignored and
   are never required in GitHub Actions.

Run the same fixture pipeline locally with:

```powershell
$env:PYTHONPATH = "."
python -m ml.src.pipeline `
  --input ml\tests\fixtures\paysim_fixture.csv `
  --output-dir ml\pipeline-output `
  --model-name paysim-ci `
  --version local
```

For an authorized full PaySim CSV, replace the fixture path. The full-dataset
run is intended for local or separately managed data jobs because raw data and
trained artifacts are intentionally not committed.

