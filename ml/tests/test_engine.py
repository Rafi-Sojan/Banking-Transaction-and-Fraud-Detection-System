from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

from ml.src.engine import MLInferenceEngine
from ml.src.features import FEATURE_COLUMNS


def test_inference_engine_loads_versioned_bundle(tmp_path: Path) -> None:
    frame = pd.DataFrame([
        {"amount": 10.0, "step": 1, "oldbalanceOrg": 100.0, "newbalanceOrig": 90.0, "oldbalanceDest": 0.0, "newbalanceDest": 10.0, "type": "PAYMENT"},
        {"amount": 9000.0, "step": 2, "oldbalanceOrg": 10000.0, "newbalanceOrig": 1000.0, "oldbalanceDest": 0.0, "newbalanceDest": 9000.0, "type": "TRANSFER"},
        {"amount": 15.0, "step": 3, "oldbalanceOrg": 100.0, "newbalanceOrig": 85.0, "oldbalanceDest": 0.0, "newbalanceDest": 15.0, "type": "PAYMENT"},
        {"amount": 8000.0, "step": 4, "oldbalanceOrg": 9000.0, "newbalanceOrig": 1000.0, "oldbalanceDest": 0.0, "newbalanceDest": 8000.0, "type": "TRANSFER"},
    ])
    labels = [0, 1, 0, 1]
    preprocessor = ColumnTransformer([
        ("numeric", "passthrough", ["amount", "step", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"]),
        ("categorical", OneHotEncoder(handle_unknown="ignore"), ["type"]),
    ])
    pipeline = Pipeline([("preprocessor", preprocessor), ("classifier", LogisticRegression(max_iter=1000))])
    pipeline.fit(frame, labels)
    model_path = tmp_path / "model.joblib"
    joblib.dump({"pipeline": pipeline, "feature_columns": FEATURE_COLUMNS, "model_name": "test", "version": "1"}, model_path)

    prediction = MLInferenceEngine(model_path).predict({"amount": 5000, "transaction_type": "TRANSFER"})

    assert prediction.model_name == "test"
    assert prediction.version == "1"
    assert 0.0 <= prediction.fraud_probability <= 1.0

