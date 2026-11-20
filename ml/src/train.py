"""Train and persist the reproducible PaySim baseline model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.src.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES, training_features, training_target


def build_pipeline() -> Pipeline:
    """Create the preprocessing and classifier pipeline."""

    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("one_hot", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessor = ColumnTransformer([
        ("numeric", numeric, list(NUMERIC_FEATURES)),
        ("categorical", categorical, list(CATEGORICAL_FEATURES)),
    ])
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)),
    ])


def train_model(input_path: str | Path, output_path: str | Path, model_name: str, version: str) -> dict[str, Any]:
    """Train, evaluate, and persist a model bundle from a PaySim CSV."""

    frame = pd.read_csv(input_path)
    features = training_features(frame)
    target = training_target(frame)
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
        stratify=target,
    )
    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype("int64")
    metrics = {
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
    }
    bundle = {
        "pipeline": pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "model_name": model_name,
        "version": version,
        "metrics": metrics,
        "dataset": "PaySim",
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output)
    return {"model_name": model_name, "version": version, "model_path": str(output), "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a PaySim fraud model")
    parser.add_argument("--input", required=True, help="Path to PaySim CSV")
    parser.add_argument("--output", required=True, help="Path for Joblib model bundle")
    parser.add_argument("--model-name", default="paysim-baseline")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--metadata-output", help="Optional JSON metrics output path")
    args = parser.parse_args()
    metadata = train_model(args.input, args.output, args.model_name, args.version)
    rendered = json.dumps(metadata, indent=2)
    if args.metadata_output:
        Path(args.metadata_output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

