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

from ml.src.features import FEATURE_COLUMNS


def test_json_inference_contract(tmp_path: Path) -> None:
    frame = pd.DataFrame([
        {"amount": 10.0, "step": 1, "oldbalanceOrg": 100.0, "newbalanceOrig": 90.0, "oldbalanceDest": 0.0, "newbalanceDest": 10.0, "type": "PAYMENT"},
        {"amount": 9000.0, "step": 2, "oldbalanceOrg": 10000.0, "newbalanceOrig": 1000.0, "oldbalanceDest": 0.0, "newbalanceDest": 9000.0, "type": "TRANSFER"},
        {"amount": 15.0, "step": 3, "oldbalanceOrg": 100.0, "newbalanceOrig": 85.0, "oldbalanceDest": 0.0, "newbalanceDest": 15.0, "type": "PAYMENT"},
        {"amount": 8000.0, "step": 4, "oldbalanceOrg": 9000.0, "newbalanceOrig": 1000.0, "oldbalanceDest": 0.0, "newbalanceDest": 8000.0, "type": "TRANSFER"},
    ])
    preprocessor = ColumnTransformer([
        ("numeric", "passthrough", list(FEATURE_COLUMNS[:-1])),
        ("categorical", OneHotEncoder(handle_unknown="ignore"), ["type"]),
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

