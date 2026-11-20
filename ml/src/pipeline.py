"""Validation, processing, training, and reporting pipeline for PaySim."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ml.src.features import FEATURE_COLUMNS, TARGET_COLUMN, training_features, training_target
from ml.src.train import train_model

RAW_COLUMNS = (
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)
RAW_NUMERIC_COLUMNS = (
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)


def validate_dataset(input_path: str | Path, chunksize: int = 250_000) -> dict[str, Any]:
    """Stream-validate the raw PaySim CSV and return a dataset summary."""

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"PaySim input does not exist: {path}")
    header = pd.read_csv(path, nrows=0)
    missing = [column for column in RAW_COLUMNS if column not in header.columns]
    if missing:
        raise ValueError(f"PaySim dataset is missing required columns: {', '.join(missing)}")

    row_count = 0
    fraud_count = 0
    flagged_count = 0
    type_counts: dict[str, int] = {}
    for chunk in pd.read_csv(path, usecols=list(RAW_COLUMNS), chunksize=chunksize):
        numeric_columns: dict[str, pd.Series] = {}
        for column in RAW_NUMERIC_COLUMNS:
            numeric = pd.to_numeric(chunk[column], errors="coerce")
            if numeric.isna().any():
                raise ValueError(f"PaySim column {column} contains non-numeric or missing values")
            numeric_columns[column] = numeric
        if (numeric_columns["amount"] < 0).any() or (numeric_columns["step"] < 0).any():
            raise ValueError("PaySim amount and step values must be non-negative")
        fraud_values = set(numeric_columns[TARGET_COLUMN].unique())
        if not fraud_values.issubset({0, 1}):
            raise ValueError("PaySim isFraud must contain only 0 and 1")
        flagged_values = set(numeric_columns["isFlaggedFraud"].unique())
        if not flagged_values.issubset({0, 1}):
            raise ValueError("PaySim isFlaggedFraud must contain only 0 and 1")
        types = chunk["type"].astype(str).str.upper()
        if types.eq("").any() or types.eq("NAN").any():
            raise ValueError("PaySim type must not be empty")
        for transaction_type, count in types.value_counts().items():
            type_counts[transaction_type] = type_counts.get(transaction_type, 0) + int(count)
        row_count += len(chunk)
        fraud_count += int(numeric_columns[TARGET_COLUMN].sum())
        flagged_count += int(numeric_columns["isFlaggedFraud"].sum())

    if row_count == 0 or fraud_count == 0 or fraud_count == row_count:
        raise ValueError("PaySim dataset must contain both legitimate and fraudulent rows")
    return {
        "input_path": str(path),
        "rows": row_count,
        "fraud_rows": fraud_count,
        "fraud_rate": fraud_count / row_count,
        "flagged_rows": flagged_count,
        "transaction_types": dict(sorted(type_counts.items())),
        "raw_columns": list(RAW_COLUMNS),
        "feature_columns": list(FEATURE_COLUMNS),
    }


def process_dataset(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Write the normalized, leakage-safe training frame."""

    frame = pd.read_csv(input_path, usecols=list(RAW_COLUMNS))
    features = training_features(frame)
    features["type"] = features["type"].astype(str).str.upper()
    processed = features.copy()
    processed[TARGET_COLUMN] = training_target(frame)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    processed.to_csv(output, index=False)
    return {
        "output_path": str(output),
        "rows": len(processed),
        "columns": list(processed.columns),
    }


def run_pipeline(
    input_path: str | Path,
    output_dir: str | Path,
    model_name: str,
    version: str,
) -> dict[str, Any]:
    """Run validation, processing, training, and report generation."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    validation = validate_dataset(input_path)
    processing = process_dataset(input_path, output / "processed-paysim.csv")
    model = train_model(
        processing["output_path"],
        output / f"{model_name}-{version}.joblib",
        model_name,
        version,
    )
    report = {"validation": validation, "processing": processing, "model": model}
    (output / "pipeline-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate, process, train, and report PaySim")
    parser.add_argument("--input", required=True, help="Path to raw PaySim CSV")
    parser.add_argument("--output-dir", required=True, help="Output directory for processed data and model")
    parser.add_argument("--model-name", default="paysim-baseline")
    parser.add_argument("--version", default="ci")
    args = parser.parse_args()
    print(json.dumps(run_pipeline(args.input, args.output_dir, args.model_name, args.version), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
