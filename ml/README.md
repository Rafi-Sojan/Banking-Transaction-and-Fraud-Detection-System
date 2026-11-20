# ML Engine

The ML component provides a reproducible PaySim baseline and a controlled JSON
inference process. It is separate from the C++ deterministic rules engine and
does not authorize transactions or write to PostgreSQL directly.

## Feature policy

Training uses only decision-time PaySim features:

- `amount`
- `step`
- `oldbalanceOrg`
- `newbalanceOrig`
- `oldbalanceDest`
- `newbalanceDest`
- `type`

The target `isFraud` and simulator flag `isFlaggedFraud` are not used as model
inputs. The trainer requires both fraud classes to be present and reports
precision, recall, F1, PR-AUC, and ROC-AUC.

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

The backend keeps ML disabled by default until a trained model exists. To
enable it, configure:

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

