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


def temporal_split(
    features: pd.DataFrame,
    target: pd.Series,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """Split PaySim into ordered train, threshold-validation, and test periods."""

    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("temporal split fractions must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train and validation fractions must leave a test period")
    steps = pd.to_numeric(features["step"], errors="raise")
    unique_steps = sorted(steps.unique())
    if len(unique_steps) < 3:
        raise ValueError("temporal validation requires at least three distinct PaySim steps")

    train_end = max(1, min(len(unique_steps) - 2, int(len(unique_steps) * train_fraction)))
    validation_end = max(
        train_end + 1,
        min(len(unique_steps) - 1, int(len(unique_steps) * (train_fraction + validation_fraction))),
    )
    train_steps = set(unique_steps[:train_end])
    validation_steps = set(unique_steps[train_end:validation_end])
    test_steps = set(unique_steps[validation_end:])
    train_mask = steps.isin(train_steps)
    validation_mask = steps.isin(validation_steps)
    test_mask = steps.isin(test_steps)
    return (
        features.loc[train_mask],
        features.loc[validation_mask],
        features.loc[test_mask],
        target.loc[train_mask],
        target.loc[validation_mask],
        target.loc[test_mask],
    )


def tune_threshold(
    target: pd.Series,
    probabilities: Any,
    minimum_recall: float = 0.80,
) -> tuple[float, dict[str, float]]:
    """Choose a threshold on validation data while preferring the target recall."""

    if not 0 <= minimum_recall <= 1:
        raise ValueError("minimum_recall must be between 0 and 1")
    candidates: list[dict[str, float]] = []
    for threshold_index in range(0, 101):
        threshold = threshold_index / 100
        predictions = (probabilities >= threshold).astype("int64")
        candidates.append({
            "threshold": threshold,
            "precision": float(precision_score(target, predictions, zero_division=0)),
            "recall": float(recall_score(target, predictions, zero_division=0)),
            "f1": float(f1_score(target, predictions, zero_division=0)),
        })
    eligible = [candidate for candidate in candidates if candidate["recall"] >= minimum_recall]
    selected = max(
        eligible or candidates,
        key=lambda candidate: (candidate["f1"], candidate["precision"], candidate["recall"], -candidate["threshold"]),
    )
    return selected["threshold"], selected


def _classification_metrics(target: pd.Series, probabilities: Any, threshold: float) -> dict[str, float]:
    predictions = (probabilities >= threshold).astype("int64")
    return {
        "precision": float(precision_score(target, predictions, zero_division=0)),
        "recall": float(recall_score(target, predictions, zero_division=0)),
        "f1": float(f1_score(target, predictions, zero_division=0)),
        "pr_auc": float(average_precision_score(target, probabilities)),
        "roc_auc": float(roc_auc_score(target, probabilities)),
    }


def train_model(
    input_path: str | Path,
    output_path: str | Path,
    model_name: str,
    version: str,
    validation_strategy: str = "temporal",
) -> dict[str, Any]:
    """Train, evaluate, and persist a model bundle from a PaySim CSV."""

    frame = pd.read_csv(input_path)
    features = training_features(frame)
    target = training_target(frame)
    if validation_strategy == "temporal":
        x_train, x_validation, x_test, y_train, y_validation, y_test = temporal_split(features, target)
    elif validation_strategy == "random":
        x_train, x_test, y_train, y_test = train_test_split(
            features,
            target,
            test_size=0.2,
            random_state=42,
            stratify=target,
        )
        x_validation, y_validation = x_train, y_train
    else:
        raise ValueError("validation_strategy must be temporal or random")
    for name, labels in (("training", y_train), ("validation", y_validation), ("test", y_test)):
        if labels.nunique(dropna=True) < 2:
            raise ValueError(f"PaySim {name} period must contain both fraud classes")
    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)
    validation_probabilities = pipeline.predict_proba(x_validation)[:, 1]
    threshold, threshold_metrics = tune_threshold(y_validation, validation_probabilities)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    metrics = _classification_metrics(y_test, probabilities, threshold)
    metrics["decision_threshold"] = threshold
    metrics["validation_precision"] = threshold_metrics["precision"]
    metrics["validation_recall"] = threshold_metrics["recall"]
    metrics["validation_f1"] = threshold_metrics["f1"]
    bundle = {
        "pipeline": pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "model_name": model_name,
        "version": version,
        "metrics": metrics,
        "decision_threshold": threshold,
        "validation_strategy": validation_strategy,
        "split_rows": {
            "train": len(x_train),
            "validation": len(x_validation),
            "test": len(x_test),
        },
        "dataset": "PaySim",
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output)
    return {
        "model_name": model_name,
        "version": version,
        "model_path": str(output),
        "validation_strategy": validation_strategy,
        "decision_threshold": threshold,
        "split_rows": bundle["split_rows"],
        "metrics": metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a PaySim fraud model")
    parser.add_argument("--input", required=True, help="Path to PaySim CSV")
    parser.add_argument("--output", required=True, help="Path for Joblib model bundle")
    parser.add_argument("--model-name", default="paysim-baseline")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--validation-strategy", choices=("temporal", "random"), default="temporal")
    parser.add_argument("--metadata-output", help="Optional JSON metrics output path")
    args = parser.parse_args()
    metadata = train_model(args.input, args.output, args.model_name, args.version, args.validation_strategy)
    rendered = json.dumps(metadata, indent=2)
    if args.metadata_output:
        Path(args.metadata_output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

