# PaySim Dataset Card

## Source

- Dataset: [Synthetic Financial Datasets for Fraud Detection](https://www.kaggle.com/datasets/ealaxi/paysim1)
- Generator: PaySim mobile-money simulator
- License: CC BY-SA 4.0
- Local archive: `paysim-dataset.zip`
- Extracted file: `PS_20174392719_1491204439457_log.csv`
- CSV SHA-256: `16910F90577B0D981BF8FF289714510BB89BC71BFF7D3F220F024E287E4EEA6B`
- Acquisition date: 2026-11-21

## Dataset profile

- 6,362,620 transaction records
- 8,213 fraud records
- Fraud prevalence: approximately 0.1291%
- Five transaction types: `CASH_IN`, `CASH_OUT`, `DEBIT`, `PAYMENT`, and `TRANSFER`
- `step` represents hourly simulation steps from 1 through 743
- Target: `isFraud`

## Feature policy

The model uses only:

- `amount`
- `step`
- `type`

The model excludes `isFraud`, `isFlaggedFraud`, `nameOrig`, `nameDest`, and all
four balance columns. The PaySim data card warns that balance columns can leak
the fraud outcome because fraudulent transactions are cancelled. This policy
keeps training aligned with the backend's decision-time contract.

## Model artifact

The locally trained baseline is `ml/models/paysim-baseline.joblib`, version
`1.1.0`. It is ignored by Git and registered as deployed only in the local
PostgreSQL instance. The repository does not contain the raw CSV or binary
model artifact.

Temporal validation uses 6,010,937 training rows, 228,103 threshold-validation
rows, and 123,580 later test rows. The validation-selected decision threshold is
`0.49`:

| Metric | Value |
|---|---:|
| Precision | 0.077117 |
| Recall | 0.776904 |
| F1 | 0.140307 |
| PR-AUC | 0.166048 |
| ROC-AUC | 0.899735 |

These metrics are a reproducible academic baseline, not evidence of production
fraud-detection performance. The artifact remains opt-in and requires further
governance before any operational experiment.
