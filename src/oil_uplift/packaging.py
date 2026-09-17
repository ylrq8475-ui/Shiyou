from __future__ import annotations

import fnmatch
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd

from .config import project_root, resolve_project_path
from .exceptions import ConfigurationError, SubmissionError
from .submission import read_submission, validate_submission_frame, well_csv_filename


def _read_combined_result(source: Path, config: dict[str, Any]) -> pd.DataFrame:
    if source.is_file():
        return read_submission(source, config)
    if not source.is_dir():
        raise SubmissionError("The candidate result source is unavailable; its path is suppressed.")
    paths = sorted(path for path in source.iterdir() if path.is_file() and path.suffix.lower() == ".csv")
    if not paths:
        raise SubmissionError("The candidate result directory contains no CSV files.")
    return pd.concat([read_submission(path, config) for path in paths], ignore_index=True)


def _reference(config: dict[str, Any]) -> pd.DataFrame | None:
    value = config.get("submission", {}).get("reference_ids_file")
    if not value:
        return None
    path = resolve_project_path(config, value)
    try:
        return pd.read_csv(
            path,
            encoding=config.get("submission", {}).get("encoding", "utf-8-sig"),
            dtype={"WELL_ID": "string", "NY": "string"},
        ).astype({"WELL_ID": object, "NY": object})
    except Exception as exc:
        raise SubmissionError("Unable to read the reference template; its path is suppressed.") from exc


def create_result_zip(config: dict[str, Any], submission_path: Path, output_zip: Path) -> dict[str, Any]:
    frame = _read_combined_result(submission_path, config)
    reference = _reference(config)
    validation = validate_submission_frame(frame, config, reference=reference)
    mapped: dict[str, str] = {}
    for well_id in frame["WELL_ID"].drop_duplicates():
        filename = well_csv_filename(well_id)
        key = filename.casefold()
        if key in mapped and mapped[key] != well_id:
            raise SubmissionError("Two WELL_ID values map to the same safe filename.")
        mapped[key] = well_id

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for well_id, group in frame.groupby("WELL_ID", sort=False):
            csv_text = group.loc[:, ["WELL_ID", "NY", "RCYL"]].to_csv(
                index=False,
                float_format="%.6f",
            )
            archive.writestr(well_csv_filename(well_id), csv_text.encode("utf-8-sig"))
    return {**validation, "root_wrapped": False, "manifest_included": False}


def _excluded(relative: PurePosixPath) -> bool:
    text = relative.as_posix()
    patterns = (
        "data/**",
        "artifacts/**",
        "deliverables/**",
        "private_logs/**",
        "processed/**",
        "models/**",
        "submissions/**",
        "configs/private_*.yaml",
        "configs/private_*.yml",
        ".git/**",
        ".venv/**",
        "**/__pycache__/**",
        ".pytest_cache/**",
        "*.csv",
        "*.xlsx",
        "*.joblib",
        "*.zip",
    )
    return any(relative.match(pattern) or fnmatch.fnmatch(text, pattern) for pattern in patterns)


def _included_code_file(relative: PurePosixPath) -> bool:
    text = relative.as_posix()
    root_files = {
        "README.md",
        "audit_data.py",
        "infer.py",
        "package_delivery.py",
        "predict.py",
        "pyproject.toml",
        "reproduce_submission.py",
        "requirements-lock.txt",
        "requirements.txt",
        "train.py",
        "validate_submission.py",
    }
    script_files = {
        "scripts/analyze_anchor_candidates.py",
        "scripts/prepare_private_runtime_config.py",
        "scripts/secure_local_audit.py",
        "scripts/simulate_submission_check.py",
    }
    return (
        text in root_files
        or text == "configs/default.yaml"
        or text in script_files
        or text.startswith("src/oil_uplift/")
        or (text.startswith("tests/") and text != "tests/test_a2b002_experiments.py")
    )


def create_code_zip(config: dict[str, Any], output_zip: Path) -> dict[str, Any]:
    root = project_root(config)
    required = {"README.md", "predict.py", "requirements.txt"}
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise ConfigurationError("Code package is incomplete: " + ", ".join(missing))
    files: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.resolve() == output_zip.resolve():
            continue
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if _excluded(relative) or not _included_code_file(relative):
            continue
        files.append((path, relative.as_posix()))
    archive_names = {name for _, name in files}
    if not required.issubset(archive_names):
        raise ConfigurationError("Required root entry files would be missing from the code archive.")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, name in files:
            archive.write(path, arcname=name)
    return {"file_count": len(files), "root_wrapped": False}
