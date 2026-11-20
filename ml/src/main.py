"""JSON stdin/stdout entry point for backend ML inference."""

from __future__ import annotations

import argparse
import json
import sys

from ml.src.engine import MLInferenceEngine, ModelLoadError


def main() -> int:
    parser = argparse.ArgumentParser(description="Banking fraud ML inference engine")
    parser.add_argument("--model", required=True, help="Path to a versioned Joblib model bundle")
    args = parser.parse_args()
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        print("ml_engine error: expected one JSON object on stdin", file=sys.stderr)
        return 2
    try:
        payload = json.loads(raw_input)
        if not isinstance(payload, dict):
            raise ValueError("JSON root must be an object")
        prediction = MLInferenceEngine(args.model).predict(payload)
        print(json.dumps({
            "fraud_probability": prediction.fraud_probability,
            "model_name": prediction.model_name,
            "version": prediction.version,
        }))
        return 0
    except (ValueError, TypeError, ModelLoadError) as exc:
        print(f"ml_engine error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

