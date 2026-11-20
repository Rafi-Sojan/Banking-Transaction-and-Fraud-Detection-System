from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

from ml.src.engine import MLInferenceEngine
from ml.src.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES


def test_inference_engine_loads_versioned_bundle(tmp_path: Path) -> None:
    frame = pd.DataFrame([
        {"amount": 10.0, "step": 1, "type": "PAYMENT"},
        {"amount": 9000.0, "step": 2, "type": "TRANSFER"},
        {"amount": 15.0, "step": 3, "type": "PAYMENT"},
        {"amount": 8000.0, "step": 4, "type": "TRANSFER"},
    ])
    labels = [0, 1, 0, 1]
    preprocessor = ColumnTransformer([
        ("numeric", "passthrough", list(NUMERIC_FEATURES)),
        ("categorical", OneHotEncoder(handle_unknown="ignore"), list(CATEGORICAL_FEATURES)),
    ])
    pipeline = Pipeline([("preprocessor", preprocessor), ("classifier", LogisticRegression(max_iter=1000))])
    pipeline.fit(frame, labels)
    model_path = tmp_path / "model.joblib"
    joblib.dump({"pipeline": pipeline, "feature_columns": FEATURE_COLUMNS, "model_name": "test", "version": "1"}, model_path)

    prediction = MLInferenceEngine(model_path).predict({"amount": 5000, "transaction_type": "TRANSFER"})

    assert prediction.model_name == "test"
    assert prediction.version == "1"
    assert 0.0 <= prediction.fraud_probability <= 1.0

