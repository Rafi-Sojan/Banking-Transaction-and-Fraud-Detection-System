from pathlib import Path

from ml.src.pipeline import process_dataset, run_pipeline, validate_dataset


FIXTURE = Path(__file__).parent / "fixtures" / "paysim_fixture.csv"


def test_validate_dataset_reports_classes_and_types() -> None:
    summary = validate_dataset(FIXTURE)
    assert summary["rows"] == 20
    assert summary["fraud_rows"] == 4
    assert summary["transaction_types"]["TRANSFER"] == 4


def test_process_dataset_excludes_leakage_columns(tmp_path: Path) -> None:
    output = tmp_path / "processed.csv"
    details = process_dataset(FIXTURE, output)
    assert details["columns"] == ["amount", "step", "type", "isFraud"]


def test_pipeline_trains_and_reports(tmp_path: Path) -> None:
    report = run_pipeline(FIXTURE, tmp_path / "output", "fixture-model", "ci")
    assert report["validation"]["fraud_rows"] == 4
    assert Path(report["model"]["model_path"]).exists()
    assert (tmp_path / "output" / "pipeline-report.json").exists()
