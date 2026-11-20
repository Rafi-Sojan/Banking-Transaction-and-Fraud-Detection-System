"""Feature contracts shared by PaySim training and online inference.

The target column and simulator-only fields are deliberately excluded from the
feature set. The selected columns are available at transaction decision time
and avoid using ``isFraud`` or ``isFlaggedFraud`` as model inputs.
"""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

NUMERIC_FEATURES = (
    "amount",
    "step",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
)
CATEGORICAL_FEATURES = ("type",)
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET_COLUMN = "isFraud"
EXCLUDED_COLUMNS = {TARGET_COLUMN, "isFlaggedFraud"}


def validate_training_frame(frame: pd.DataFrame) -> None:
    """Validate the minimum PaySim columns required for training."""

    missing = [column for column in (*FEATURE_COLUMNS, TARGET_COLUMN) if column not in frame.columns]
    if missing:
        raise ValueError(f"PaySim dataset is missing required columns: {', '.join(missing)}")
    if frame[TARGET_COLUMN].nunique(dropna=True) < 2:
        raise ValueError("PaySim training data must contain both fraud classes")


def training_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return only approved model features from a PaySim dataframe."""

    validate_training_frame(frame)
    return frame.loc[:, FEATURE_COLUMNS].copy()


def training_target(frame: pd.DataFrame) -> pd.Series:
    """Return the binary fraud target after validating its values."""

    validate_training_frame(frame)
    target = pd.to_numeric(frame[TARGET_COLUMN], errors="raise")
    if not target.isin([0, 1]).all():
        raise ValueError("PaySim isFraud must contain only 0 and 1")
    return target.astype("int64")


def online_features(payload: dict[str, Any]) -> pd.DataFrame:
    """Build a one-row inference frame from a backend JSON payload.

    Missing optional PaySim balance/step fields use neutral zero values. The
    transaction amount and type are required because they are part of the
    backend decision contract.
    """

    if "amount" not in payload or "transaction_type" not in payload:
        raise ValueError("ML input requires amount and transaction_type")
    row = {
        "amount": payload["amount"],
        "step": payload.get("step", 0),
        "oldbalanceOrg": payload.get("oldbalanceOrg", payload.get("old_balance_origin", 0)),
        "newbalanceOrig": payload.get("newbalanceOrig", payload.get("new_balance_origin", 0)),
        "oldbalanceDest": payload.get("oldbalanceDest", payload.get("old_balance_destination", 0)),
        "newbalanceDest": payload.get("newbalanceDest", payload.get("new_balance_destination", 0)),
        "type": payload["transaction_type"],
    }
    frame = pd.DataFrame([row], columns=FEATURE_COLUMNS)
    for column in NUMERIC_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame

