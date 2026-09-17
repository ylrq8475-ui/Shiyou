import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_uplift.exceptions import SubmissionError
from oil_uplift.packaging import create_code_zip, create_result_zip
from oil_uplift.submission import validate_result_zip, validate_submission_frame


def candidate():
    rows = []
    for well in ("SYNTH_A", "SYNTH_B"):
        for date in pd.date_range("2024-01-01", periods=12, freq="MS"):
            rows.append(
                {"WELL_ID": well, "NY": date.strftime("%Y/%m/%d"), "RCYL": 1.234567}
            )
    return pd.DataFrame(rows, columns=["WELL_ID", "NY", "RCYL"])


def config(root: Path):
    return {
        "_runtime": {"project_root": str(root)},
        "submission": {"encoding": "utf-8-sig", "reference_ids_file": None},
    }


def test_valid_submission_and_result_zip_are_root_flat(tmp_path):
    frame = candidate()
    source = tmp_path / "combined.csv"
    output = tmp_path / "result.zip"
    frame.to_csv(source, index=False, encoding="utf-8-sig")
    assert validate_submission_frame(frame)["wells"] == 2
    create_result_zip(config(tmp_path), source, output)
    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == ["SYNTH_A.csv", "SYNTH_B.csv"]
        assert all("/" not in name for name in archive.namelist())
    assert validate_result_zip(output, frame[["WELL_ID", "NY"]])["rows"] == 24


@pytest.mark.parametrize("mutation", ["negative", "nan", "duplicate", "bad_date", "short"])
def test_submission_lint_rejects_invalid_candidates(mutation):
    frame = candidate()
    if mutation == "negative":
        frame.loc[0, "RCYL"] = -0.1
    elif mutation == "nan":
        frame.loc[0, "RCYL"] = np.nan
    elif mutation == "duplicate":
        frame.loc[1, ["WELL_ID", "NY"]] = frame.loc[0, ["WELL_ID", "NY"]]
    elif mutation == "bad_date":
        frame.loc[0, "NY"] = "2024/02/30"
    elif mutation == "short":
        frame = frame.iloc[:-1].copy()
    with pytest.raises(SubmissionError):
        validate_submission_frame(frame)


def test_reference_order_is_mandatory():
    frame = candidate()
    reversed_frame = frame.iloc[::-1].reset_index(drop=True)
    with pytest.raises(SubmissionError, match="order"):
        validate_submission_frame(reversed_frame, reference=frame[["WELL_ID", "NY"]])


def test_code_zip_excludes_private_data_models_and_outputs(tmp_path):
    for name in ("README.md", "predict.py", "requirements.txt", "reproduce_submission.py"):
        (tmp_path / name).write_text("safe", encoding="utf-8")
    (tmp_path / "src" / "oil_uplift").mkdir(parents=True)
    (tmp_path / "src" / "oil_uplift" / "model.py").write_text("safe", encoding="utf-8")
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "default.yaml").write_text("safe", encoding="utf-8")
    (tmp_path / "configs" / "private_runtime.yaml").write_text("sensitive", encoding="utf-8")
    for directory, filename in (
        ("private_logs", "audit.json"),
        ("data", "raw.csv"),
        ("processed", "features.csv"),
        ("models", "model.joblib"),
        ("submissions", "candidate.csv"),
    ):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / filename).write_text("sensitive", encoding="utf-8")
    output = tmp_path / "submission_code.zip"
    create_code_zip(config(tmp_path), output)
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert {
        "README.md",
        "predict.py",
        "requirements.txt",
        "src/oil_uplift/model.py",
    }.issubset(names)
    assert "configs/default.yaml" in names
    assert "configs/private_runtime.yaml" not in names
    assert not any(
        name.startswith(("private_logs/", "data/", "processed/", "models/", "submissions/"))
        for name in names
    )
