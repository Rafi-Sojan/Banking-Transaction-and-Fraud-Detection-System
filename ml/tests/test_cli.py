import json
import subprocess
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ml.src.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES


def test_json_inference_contract(tmp_path: Path) -> None:
    frame = pd.DataFrame([
        {"amount": 10.0, "step": 1, "type": "PAYMENT"},
        {"amount": 9000.0, "step": 2, "type": "TRANSFER"},
        {"amount": 15.0, "step": 3, "type": "PAYMENT"},
        {"amount": 8000.0, "step": 4, "type": "TRANSFER"},
    ])
    preprocessor = ColumnTransformer([
        ("numeric", "passthrough", list(NUMERIC_FEATURES)),
        ("categorical", OneHotEncoder(handle_unknown="ignore"), list(CATEGORICAL_FEATURES)),
    ])
    pipeline = Pipeline([("preprocessor", preprocessor), ("classifier", LogisticRegression(max_iter=1000))])
    pipeline.fit(frame, [0, 1, 0, 1])
    model_path = tmp_path / "model.joblib"
    joblib.dump({"pipeline": pipeline, "feature_columns": FEATURE_COLUMNS, "model_name": "test", "version": "1"}, model_path)

    completed = subprocess.run(
        [sys.executable, "-m", "ml.src.main", "--model", str(model_path)],
        input=json.dumps({"transaction_id": "cli-test", "amount": 5000, "transaction_type": "TRANSFER"}),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output["model_name"] == "test"
    assert output["version"] == "1"
    assert 0 <= output["fraud_probability"] <= 1

