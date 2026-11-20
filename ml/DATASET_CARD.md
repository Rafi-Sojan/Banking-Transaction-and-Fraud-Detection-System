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
`1.0.0`. It is ignored by Git and registered as deployed only in the local
PostgreSQL instance. The repository does not contain the raw CSV or binary
model artifact.

Baseline holdout metrics at threshold `0.5`:

| Metric | Value |
|---|---:|
| Precision | 0.005236 |
| Recall | 0.882532 |
| F1 | 0.010411 |
| PR-AUC | 0.020684 |
| ROC-AUC | 0.919355 |

These metrics are a reproducible academic baseline, not evidence of production
fraud-detection performance. Threshold selection and temporal validation remain
necessary before any operational use.
