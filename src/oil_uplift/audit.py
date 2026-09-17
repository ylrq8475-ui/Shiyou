from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd

from .exceptions import PolicyBlockedError
from .io import read_table
from .schema import suggest_mapping

AUTH_ENV = "COMPETITION_DATA_ACCESS_ACK"
AUTH_VALUE = "I_AM_AUTHORIZED"


def require_local_audit_authorization(cli_authorized: bool) -> None:
    if not cli_authorized or os.environ.get(AUTH_ENV) != AUTH_VALUE:
        raise PolicyBlockedError(
            "Local data audit requires --authorized and COMPETITION_DATA_ACCESS_ACK=I_AM_AUTHORIZED."
        )


def _safe_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def audit_frame(frame: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    columns: dict[str, Any] = {}
    datetime_columns = set(config.get("schema", {}).get("datetime_columns", []))
    for name in frame.columns:
        series = frame[name]
        item: dict[str, Any] = {
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "missing_fraction": float(series.isna().mean()),
            "unique_count": int(series.nunique(dropna=True)),
        }
        if name in datetime_columns:
            parsed = pd.to_datetime(series, errors="coerce", utc=True)
            item["invalid_datetime_count"] = int(parsed.isna().sum() - series.isna().sum())
            item["minimum"] = _safe_scalar(parsed.min())
            item["maximum"] = _safe_scalar(parsed.max())
        elif pd.api.types.is_numeric_dtype(series):
            finite = pd.to_numeric(series, errors="coerce")
            item["minimum"] = _safe_scalar(finite.min())
            item["maximum"] = _safe_scalar(finite.max())
            item["mean"] = _safe_scalar(finite.mean())
        columns[str(name)] = item
    aliases = config.get("schema", {}).get("aliases", {})
    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "duplicate_rows": int(frame.duplicated().sum()),
        "column_profile": columns,
        "mapping_suggestions_from_configured_aliases": suggest_mapping(list(map(str, frame.columns)), aliases),
    }


def audit_declared_files(paths: list[Path], config: dict[str, Any]) -> dict[str, Any]:
    files = []
    for number, path in enumerate(paths, start=1):
        frame = read_table(path, config)
        files.append(
            {
                "file_id": f"file_{number:03d}",
                "format": path.suffix.lower().lstrip("."),
                "profile": audit_frame(frame, config),
            }
        )
    return {
        "notice": "Generated locally from explicitly declared files; raw paths are intentionally omitted.",
        "file_count": len(files),
        "files": files,
    }
