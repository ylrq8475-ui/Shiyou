from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .exceptions import SubmissionError

OFFICIAL_COLUMNS = ["WELL_ID", "NY", "RCYL"]
DATE_PATTERN = re.compile(r"^\d{4}/\d{2}/\d{2}$")
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def well_csv_filename(well_id: str) -> str:
    if not isinstance(well_id, str) or not well_id:
        raise SubmissionError("WELL_ID must be a non-empty string.")
    safe = INVALID_FILENAME.sub("_", well_id).rstrip(". ")
    if not safe or safe in {".", ".."}:
        raise SubmissionError("WELL_ID cannot be converted to a safe filename.")
    return f"{safe}.csv"


def _validate_dates(values: pd.Series) -> None:
    strings = values.astype("string")
    if strings.isna().any() or not strings.str.match(DATE_PATTERN).all():
        raise SubmissionError("NY must be a non-missing string in YYYY/MM/DD format.")
    parsed = pd.to_datetime(strings, format="%Y/%m/%d", errors="coerce")
    rendered = parsed.dt.strftime("%Y/%m/%d").astype("string")
    if parsed.isna().any() or rendered.tolist() != strings.tolist():
        raise SubmissionError("NY contains an invalid calendar date.")


def validate_submission_frame(
    frame: pd.DataFrame,
    config: dict[str, Any] | None = None,
    *,
    reference_ids: pd.DataFrame | pd.Series | None = None,
    reference: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Validate the fixed official per-well output contract."""
    if list(frame.columns) != OFFICIAL_COLUMNS:
        raise SubmissionError("Columns must be exactly WELL_ID, NY, RCYL in that order.")
    if frame.empty:
        raise SubmissionError("Submission cannot be empty.")
    if not all(isinstance(value, str) and value for value in frame["WELL_ID"]):
        raise SubmissionError("WELL_ID values must be non-empty strings.")
    _validate_dates(frame["NY"])
    if frame[["WELL_ID", "NY"]].duplicated().any():
        raise SubmissionError("WELL_ID-NY keys must be unique.")
    counts = frame.groupby("WELL_ID", sort=False).size()
    if counts.ne(12).any():
        raise SubmissionError("Each WELL_ID must have exactly 12 rows.")
    predictions = pd.to_numeric(frame["RCYL"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(predictions).all():
        raise SubmissionError("RCYL must contain only finite numeric values.")
    if (predictions < 0).any():
        raise SubmissionError("RCYL must be non-negative.")

    reference_frame = reference
    if reference_frame is None and isinstance(reference_ids, pd.DataFrame):
        reference_frame = reference_ids
    if reference_frame is not None:
        if not {"WELL_ID", "NY"}.issubset(reference_frame.columns):
            raise SubmissionError("Reference template must contain WELL_ID and NY.")
        expected = list(
            reference_frame.loc[:, ["WELL_ID", "NY"]].astype(str).itertuples(index=False, name=None)
        )
        actual = list(frame.loc[:, ["WELL_ID", "NY"]].astype(str).itertuples(index=False, name=None))
        if actual != expected:
            raise SubmissionError("Submission keys or row order differ from the reference template.")
    return {"valid": True, "rows": len(frame), "wells": int(frame["WELL_ID"].nunique())}


def read_submission(path: Path, config: dict[str, Any] | None = None) -> pd.DataFrame:
    try:
        return pd.read_csv(
            path,
            encoding=(config or {}).get("submission", {}).get("encoding", "utf-8-sig"),
            dtype={"WELL_ID": "string", "NY": "string"},
        ).astype({"WELL_ID": object, "NY": object})
    except Exception as exc:
        raise SubmissionError("Unable to read the submission file; its path is suppressed.") from exc


def validate_result_zip(path: Path, reference: pd.DataFrame) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = archive.namelist()
            if not names or any("/" in name or "\\" in name or not name.lower().endswith(".csv") for name in names):
                raise SubmissionError("result.zip root may contain only per-well CSV files.")
            if len(names) != len(set(name.casefold() for name in names)):
                raise SubmissionError("result.zip contains duplicate filenames.")
            frames = []
            for name in names:
                frame = pd.read_csv(
                    io.BytesIO(archive.read(name)),
                    encoding="utf-8-sig",
                    dtype={"WELL_ID": "string", "NY": "string"},
                ).astype({"WELL_ID": object, "NY": object})
                if frame["WELL_ID"].nunique(dropna=False) != 1:
                    raise SubmissionError("Each CSV must contain exactly one WELL_ID.")
                expected_name = well_csv_filename(frame["WELL_ID"].iloc[0])
                if name != expected_name:
                    raise SubmissionError("A per-well CSV filename does not match its WELL_ID.")
                frames.append(frame)
    except zipfile.BadZipFile as exc:
        raise SubmissionError("The result archive is not a valid ZIP file.") from exc
    combined = pd.concat(frames, ignore_index=True)
    # Reorder archive rows to the reference solely for structural validation.
    keyed = combined.set_index(["WELL_ID", "NY"], drop=False)
    expected_keys = list(reference[["WELL_ID", "NY"]].astype(str).itertuples(index=False, name=None))
    if set(keyed.index.map(lambda item: (str(item[0]), str(item[1])))) != set(expected_keys):
        raise SubmissionError("ZIP keys differ from the reference template.")
    ordered = keyed.loc[expected_keys].reset_index(drop=True)
    return validate_submission_frame(ordered, reference=reference)
