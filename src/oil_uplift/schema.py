from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .exceptions import ConfigurationError, DataContractError


@dataclass(frozen=True)
class SchemaContract:
    sample_id: str
    group_id: str
    event_time: str
    target: str | None
    sample_weight: str | None
    feature_columns: tuple[str, ...]
    datetime_columns: tuple[str, ...]
    categorical_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...]


def _mapped(config: dict[str, Any], canonical: str, required: bool) -> str | None:
    value = config.get("schema", {}).get("mapping", {}).get(canonical)
    if value in (None, ""):
        if required:
            raise ConfigurationError(f"schema.mapping.{canonical} must be configured.")
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"schema.mapping.{canonical} must be a column name string.")
    return value


def build_schema_contract(
    frame: pd.DataFrame,
    config: dict[str, Any],
    *,
    require_target: bool,
) -> SchemaContract:
    sample_id = _mapped(config, "sample_id", required=True)
    group_id = _mapped(config, "group_id", required=True)
    event_time = _mapped(config, "event_time", required=True)
    target = _mapped(config, "target", required=require_target)
    sample_weight = _mapped(config, "sample_weight", required=False)

    schema = config.get("schema", {})
    excluded = set(schema.get("exclude_columns", []))
    excluded.update(filter(None, [sample_id, group_id, event_time, target, sample_weight]))
    excluded.add("__source_file_id")
    explicit_features = schema.get("feature_columns", [])
    features = list(explicit_features) if explicit_features else [
        str(column) for column in frame.columns if column not in excluded
    ]
    if not features:
        raise DataContractError("No feature columns remain after applying the schema contract.")

    datetime_columns = tuple(schema.get("datetime_columns", []))
    categorical_columns = tuple(schema.get("categorical_columns", []))
    numeric_columns = tuple(schema.get("numeric_columns", []))
    referenced = set(features) | set(datetime_columns) | set(categorical_columns) | set(numeric_columns)
    referenced.update(filter(None, [sample_id, group_id, event_time, target, sample_weight]))
    missing = sorted(referenced - set(frame.columns))
    if missing:
        raise DataContractError(f"Configured columns are missing: {', '.join(missing)}")
    if len(features) != len(set(features)):
        raise ConfigurationError("schema.feature_columns contains duplicates.")
    if schema.get("strict_unique_sample_id", True) and frame[sample_id].duplicated().any():
        raise DataContractError("Sample IDs must be unique under the configured schema.")

    overlap = (set(categorical_columns) & set(numeric_columns)) | (
        set(datetime_columns) & (set(categorical_columns) | set(numeric_columns))
    )
    if overlap:
        raise ConfigurationError(f"Feature type lists overlap: {', '.join(sorted(overlap))}")

    return SchemaContract(
        sample_id=sample_id,
        group_id=group_id,
        event_time=event_time,
        target=target,
        sample_weight=sample_weight,
        feature_columns=tuple(features),
        datetime_columns=datetime_columns,
        categorical_columns=categorical_columns,
        numeric_columns=numeric_columns,
    )


def coerce_event_time(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_datetime(frame[column], errors="coerce", utc=True)
    if values.isna().any():
        raise DataContractError(f"The configured event-time column contains {int(values.isna().sum())} invalid values.")
    return values


def normalize_column_name(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value).casefold())


def suggest_mapping(columns: list[str], aliases: dict[str, list[str]]) -> dict[str, list[str]]:
    """Suggest only user-supplied alias matches; never infer domain semantics."""
    normalized = {normalize_column_name(column): column for column in columns}
    suggestions: dict[str, list[str]] = {}
    for canonical, candidates in aliases.items():
        matches = []
        for candidate in candidates:
            match = normalized.get(normalize_column_name(candidate))
            if match is not None and match not in matches:
                matches.append(match)
        suggestions[canonical] = matches
    return suggestions
