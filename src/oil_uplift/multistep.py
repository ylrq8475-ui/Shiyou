from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import project_root, resolve_project_path
from .exceptions import ConfigurationError, DataContractError, PolicyBlockedError
from .io import read_table


@dataclass(frozen=True)
class MultiSourceTables:
    history: pd.DataFrame
    layer: pd.DataFrame
    plan: pd.DataFrame
    template: pd.DataFrame | None = None


def _declared_role_paths(config: dict[str, Any], split: str, role: str) -> list[Path]:
    sources = config.get("data", {}).get("sources", {})
    entries = sources.get(split, {}).get(role, [])
    if not isinstance(entries, list):
        raise ConfigurationError(f"data.sources.{split}.{role} must be a list.")
    input_dir = config.get("data", {}).get("input_dir")
    base = resolve_project_path(config, input_dir) if input_dir else project_root(config)
    paths: list[Path] = []
    for entry in entries:
        if not isinstance(entry, str) or not entry:
            raise ConfigurationError(f"data.sources.{split}.{role} contains an invalid entry.")
        candidate = Path(entry).expanduser()
        path = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
        if path.suffix.lower() not in {".csv", ".xlsx"} or not path.is_file():
            raise DataContractError(f"A declared {split}/{role} file is unavailable or unsupported.")
        paths.append(path)
    return paths


def _load_role(config: dict[str, Any], split: str, role: str, required: bool) -> pd.DataFrame:
    paths = _declared_role_paths(config, split, role)
    if not paths:
        if required:
            raise ConfigurationError(f"At least one {split}/{role} file must be declared.")
        return pd.DataFrame()
    frames = [read_table(path, config) for path in paths]
    first = list(frames[0].columns)
    if any(list(frame.columns) != first for frame in frames[1:]):
        raise DataContractError(f"Declared {split}/{role} files have inconsistent columns.")
    return pd.concat(frames, ignore_index=True)


def load_multisource_split(config: dict[str, Any], split: str) -> MultiSourceTables:
    if split not in {"train", "test"}:
        raise ConfigurationError("split must be train or test.")
    return MultiSourceTables(
        history=_load_role(config, split, "history", required=True),
        layer=_load_role(config, split, "layer", required=False),
        plan=_load_role(config, split, "plan", required=False),
        template=_load_role(config, split, "template", required=True) if split == "test" else None,
    )


def require_confirmed_anchor_policy(config: dict[str, Any]) -> dict[str, Any]:
    anchor = config.get("anchors", {})
    if anchor.get("confirmed") is not True:
        raise PolicyBlockedError("The official last-fracture anchor rule is not confirmed.")
    required = [
        "rule_version",
        "well_column",
        "date_column",
        "event_column",
        "eligible_event_values",
        "approval_id",
        "evidence_level",
        "event_semantics",
        "continuous_event_strategy",
        "selection_strategy",
        "same_month_tie_strategy",
        "incomplete_training_window_strategy",
        "first_forecast_month_offset",
    ]
    missing = [key for key in required if anchor.get(key) in (None, "", [])]
    if missing:
        raise PolicyBlockedError("The confirmed anchor rule is incomplete: " + ", ".join(missing))
    if int(anchor.get("horizon_months", 12)) != 12:
        raise ConfigurationError("The official forecast horizon must be 12 months.")
    expected = {
        "approval_id": "B2U-001",
        "evidence_level": "data_inferred_user_approved",
        "event_semantics": "independent_monthly_events",
        "continuous_event_strategy": "record_level_latest",
        "selection_strategy": "last_candidate_month",
        "same_month_tie_strategy": "error",
    }
    mismatched = [key for key, value in expected.items() if anchor.get(key) != value]
    if mismatched:
        raise PolicyBlockedError(
            "The approved data-inferred anchor policy has unsupported values: "
            + ", ".join(mismatched)
        )
    if int(anchor["first_forecast_month_offset"]) != 1:
        raise PolicyBlockedError("B2U-001 requires the first forecast month after the anchor month.")
    if anchor.get("tie_break_columns"):
        raise PolicyBlockedError("B2U-001 forbids silently resolving same-month candidate duplicates.")
    if anchor["incomplete_training_window_strategy"] not in {"error", "exclude_with_audit"}:
        raise PolicyBlockedError("Unsupported incomplete training-window strategy.")
    return anchor


def anchor_policy_metadata(config: dict[str, Any]) -> dict[str, Any]:
    """Return an auditable anchor policy without exposing raw category values."""
    anchor = require_confirmed_anchor_policy(config)
    value_hashes = sorted(
        hashlib.sha256(str(value).encode("utf-8")).hexdigest()
        for value in anchor["eligible_event_values"]
    )
    return {
        "approval_id": anchor["approval_id"],
        "rule_version": anchor["rule_version"],
        "evidence_level": anchor["evidence_level"],
        "event_semantics": anchor["event_semantics"],
        "continuous_event_strategy": anchor["continuous_event_strategy"],
        "selection_strategy": anchor["selection_strategy"],
        "same_month_tie_strategy": anchor["same_month_tie_strategy"],
        "first_forecast_month_offset": int(anchor["first_forecast_month_offset"]),
        "history_cutoff": "through_anchor_month",
        "eligible_event_value_count": len(value_hashes),
        "eligible_event_value_sha256": value_hashes,
    }


def identify_last_fracture_anchors(history: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    anchor = require_confirmed_anchor_policy(config)
    well, date, event = anchor["well_column"], anchor["date_column"], anchor["event_column"]
    required = {well, date, event}
    missing = sorted(required - set(history.columns))
    if missing:
        raise DataContractError("Anchor columns are missing: " + ", ".join(missing))
    eligible = history.loc[history[event].isin(anchor["eligible_event_values"])].copy()
    if eligible.empty:
        raise DataContractError("No history rows match the confirmed fracture-event values.")
    eligible["__anchor_time"] = pd.to_datetime(eligible[date], errors="coerce")
    if eligible["__anchor_time"].isna().any():
        raise DataContractError("Eligible fracture rows contain invalid dates.")
    eligible["__anchor_period"] = eligible["__anchor_time"].dt.to_period("M")
    if eligible.duplicated([well, "__anchor_period"], keep=False).any():
        raise DataContractError("A well has multiple eligible fracture records in the same month.")
    ordered = eligible.sort_values([well, "__anchor_period"], kind="mergesort")
    result = ordered.groupby(well, sort=False, as_index=False).tail(1).copy()
    result["__anchor_time"] = result["__anchor_period"].dt.to_timestamp()
    return result.loc[:, [well, "__anchor_time"]]


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce") if column in frame else pd.Series(dtype=float)


def _slope(values: pd.Series) -> float:
    clean = values.dropna().to_numpy(dtype=float)
    if clean.size < 2:
        return np.nan
    return float(np.polyfit(np.arange(clean.size, dtype=float), clean, 1)[0])


def _history_features(
    history: pd.DataFrame,
    well_value: Any,
    anchor_time: pd.Timestamp,
    config: dict[str, Any],
) -> dict[str, Any]:
    anchor = config["anchors"]
    feature_config = config.get("features", {})
    well, date = anchor["well_column"], anchor["date_column"]
    target = config.get("schema", {}).get("mapping", {}).get("target", "RCYL")
    numeric_columns = list(feature_config.get("history_numeric_columns", []))
    if target not in numeric_columns:
        numeric_columns.insert(0, target)
    categorical_columns = list(feature_config.get("history_categorical_columns", []))
    lags = sorted(set(map(int, feature_config.get("target_lags", [1, 2, 3, 6, 12]))))
    windows = sorted(set(map(int, feature_config.get("rolling_windows", [3, 6, 12]))))
    trends = sorted(set(map(int, feature_config.get("trend_windows", [3, 6, 12]))))

    local = history.loc[history[well] == well_value].copy()
    local["__time"] = pd.to_datetime(local[date], errors="coerce")
    if local["__time"].isna().any():
        raise DataContractError("History contains invalid dates.")
    anchor_period = anchor_time.to_period("M")
    first_forecast_period = anchor_period + int(anchor["first_forecast_month_offset"])
    local = local.loc[local["__time"].dt.to_period("M") < first_forecast_period]
    local = local.sort_values("__time", kind="mergesort")
    if local.empty:
        raise DataContractError("No pre-anchor history is available for a forecast well.")
    local["__period"] = local["__time"].dt.to_period("M")
    # B2U-001 predicts from the month after the anchor, so the anchor month is observable.
    monthly = local.groupby("__period", sort=True, as_index=False).tail(1).sort_values("__time")
    result: dict[str, Any] = {
        "anchor_year": int(anchor_time.year),
        "anchor_month": int(anchor_time.month),
        "history_month_count": int(len(monthly)),
    }
    for column in numeric_columns:
        if column not in monthly:
            result[f"history__{column}__last"] = np.nan
            continue
        values = pd.to_numeric(monthly[column], errors="coerce").reset_index(drop=True)
        result[f"history__{column}__last"] = values.iloc[-1] if len(values) else np.nan
        for lag in lags:
            result[f"history__{column}__lag_{lag}"] = values.iloc[-lag] if len(values) >= lag else np.nan
        for window in windows:
            tail = values.tail(window)
            clean_tail = tail.dropna()
            if clean_tail.empty:
                mean_value = median_value = std_value = np.nan
            else:
                mean_value = clean_tail.mean()
                median_value = clean_tail.median()
                std_value = clean_tail.std(ddof=0)
            result[f"history__{column}__roll_{window}_mean"] = mean_value
            result[f"history__{column}__roll_{window}_median"] = median_value
            result[f"history__{column}__roll_{window}_std"] = std_value
            result[f"history__{column}__missing_{window}"] = int(tail.isna().sum())
        for window in trends:
            result[f"history__{column}__trend_{window}"] = _slope(values.tail(window))
    for column in categorical_columns:
        result[f"history__{column}__last"] = monthly[column].iloc[-1] if column in monthly else None
    return result


def _layer_features(layer: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    anchor = config["anchors"]
    feature_config = config.get("features", {})
    well = feature_config.get("layer_well_column", anchor["well_column"])
    numeric = list(feature_config.get("layer_numeric_columns", []))
    if layer.empty:
        return pd.DataFrame(columns=[anchor["well_column"]])
    missing = sorted(({well} | set(numeric)) - set(layer.columns))
    if missing:
        raise DataContractError("Layer feature columns are missing: " + ", ".join(missing))
    numeric_frame = layer.loc[:, [well, *numeric]].copy()
    for column in numeric:
        numeric_frame[column] = pd.to_numeric(numeric_frame[column], errors="coerce")
    grouped = numeric_frame.groupby(well, sort=False)[numeric].agg(["mean", "std", "min", "max"])
    grouped.columns = [f"layer__{column}__{stat}" for column, stat in grouped.columns]
    grouped["layer__row_count"] = numeric_frame.groupby(well).size()
    grouped = grouped.reset_index()
    if well != anchor["well_column"]:
        grouped = grouped.rename(columns={well: anchor["well_column"]})
    return grouped


def _plan_features(plan: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    anchor = config["anchors"]
    feature_config = config.get("features", {})
    official_well = anchor["well_column"]
    well = feature_config.get("plan_well_column", "井号")
    date = feature_config.get("plan_date_column", "完工日期")
    numeric = list(feature_config.get("plan_numeric_columns", []))
    categorical = list(feature_config.get("plan_categorical_columns", []))
    if plan.empty:
        return pd.DataFrame(columns=[official_well])
    required = {well, date, *numeric, *categorical}
    missing = sorted(required - set(plan.columns))
    if missing:
        raise DataContractError("Plan feature columns are missing: " + ", ".join(missing))
    local = plan.loc[:, [well, date, *numeric, *categorical]].copy()
    local["__plan_time"] = pd.to_datetime(local[date], errors="coerce")
    if local["__plan_time"].isna().any():
        raise DataContractError("Plan rows contain invalid completion dates.")
    # First plan only. It is never passed to anchor identification.
    first = local.sort_values([well, "__plan_time"], kind="mergesort").groupby(well, sort=False).head(1)
    output = pd.DataFrame({official_well: first[well].to_numpy()})
    for column in numeric:
        output[f"plan_first__{column}"] = pd.to_numeric(first[column], errors="coerce").to_numpy()
    for column in categorical:
        output[f"plan_first__{column}"] = first[column].astype("string").to_numpy()
    output["plan_first__year"] = first["__plan_time"].dt.year.to_numpy()
    output["plan_first__month"] = first["__plan_time"].dt.month.to_numpy()
    return output


def _static_feature_map(tables: MultiSourceTables, config: dict[str, Any]) -> dict[Any, dict[str, Any]]:
    well = config["anchors"]["well_column"]
    layer = _layer_features(tables.layer, config)
    plan = _plan_features(tables.plan, config)
    static = pd.merge(layer, plan, how="outer", on=well)
    if static.empty:
        return {}
    return {row[well]: {key: value for key, value in row.items() if key != well} for row in static.to_dict("records")}


def _target_for_period(
    history: pd.DataFrame,
    well_value: Any,
    period: pd.Period,
    config: dict[str, Any],
) -> float:
    anchor = config["anchors"]
    well, date = anchor["well_column"], anchor["date_column"]
    target = config.get("schema", {}).get("mapping", {}).get("target", "RCYL")
    local = history.loc[history[well] == well_value].copy()
    local["__time"] = pd.to_datetime(local[date], errors="coerce")
    matches = local.loc[local["__time"].dt.to_period("M") == period]
    if len(matches) != 1:
        raise DataContractError("Each training well/month must have exactly one target row.")
    value = pd.to_numeric(matches[target], errors="coerce").iloc[0]
    if pd.isna(value) or not np.isfinite(float(value)):
        raise DataContractError("Training target is missing or non-finite.")
    return float(value)


def _training_window_targets(
    history: pd.DataFrame,
    well_value: Any,
    periods: list[pd.Period],
    config: dict[str, Any],
) -> tuple[list[float] | None, str | None]:
    anchor = config["anchors"]
    well, date = anchor["well_column"], anchor["date_column"]
    target = config.get("schema", {}).get("mapping", {}).get("target", "RCYL")
    local = history.loc[history[well] == well_value, [date, target]].copy()
    local["__period"] = pd.to_datetime(local[date], errors="coerce").dt.to_period("M")
    if local["__period"].isna().any():
        raise DataContractError("History contains invalid dates.")
    values: list[float] = []
    for period in periods:
        matches = local.loc[local["__period"] == period, target]
        if len(matches) > 1:
            raise DataContractError("A training well has duplicate rows in a target month.")
        if matches.empty:
            return None, "missing_month"
        value = pd.to_numeric(matches, errors="coerce").iloc[0]
        if pd.isna(value):
            return None, "missing_target"
        if not np.isfinite(float(value)):
            return None, "nonfinite_target"
        values.append(float(value))
    return values, None


def build_training_samples(tables: MultiSourceTables, config: dict[str, Any]) -> pd.DataFrame:
    anchor_config = require_confirmed_anchor_policy(config)
    anchors = identify_last_fracture_anchors(tables.history, config)
    well = anchor_config["well_column"]
    target = config.get("schema", {}).get("mapping", {}).get("target", "RCYL")
    static = _static_feature_map(tables, config)
    rows: list[dict[str, Any]] = []
    offset = int(anchor_config["first_forecast_month_offset"])
    window_audit: dict[str, Any] = {
        "candidate_wells": int(len(anchors)),
        "included_wells": 0,
        "excluded_wells": 0,
        "exclusion_reason_counts": {},
        "strategy": anchor_config["incomplete_training_window_strategy"],
    }
    for anchor_row in anchors.to_dict("records"):
        well_value = anchor_row[well]
        anchor_time = pd.Timestamp(anchor_row["__anchor_time"])
        periods = [anchor_time.to_period("M") + offset + horizon - 1 for horizon in range(1, 13)]
        targets, exclusion_reason = _training_window_targets(
            tables.history, well_value, periods, config
        )
        if exclusion_reason is not None:
            if anchor_config["incomplete_training_window_strategy"] == "error":
                raise DataContractError("A training well does not have a complete 12-month target window.")
            window_audit["excluded_wells"] += 1
            counts = window_audit["exclusion_reason_counts"]
            counts[exclusion_reason] = int(counts.get(exclusion_reason, 0)) + 1
            continue
        base = _history_features(tables.history, well_value, anchor_time, config)
        base.update(static.get(well_value, {}))
        for horizon, target_value in enumerate(targets or [], start=1):
            row = {
                well: well_value,
                "anchor_time": anchor_time,
                "horizon": horizon,
                "forecast_step": horizon,
                target: target_value,
                **base,
            }
            rows.append(row)
        window_audit["included_wells"] += 1
    output = pd.DataFrame(rows)
    if output.empty:
        raise DataContractError("No complete training windows remain after the approved policy.")
    if output.groupby(well).size().ne(12).any():
        raise DataContractError("Training expansion must produce exactly 12 rows per well.")
    output.attrs["training_window_audit"] = window_audit
    output.attrs["anchor_policy"] = anchor_policy_metadata(config)
    return output


def validate_test_template(template: pd.DataFrame, config: dict[str, Any]) -> None:
    anchor = require_confirmed_anchor_policy(config)
    well, date = anchor["well_column"], anchor["date_column"]
    missing = sorted({well, date} - set(template.columns))
    if missing:
        raise DataContractError("Template key columns are missing: " + ", ".join(missing))
    if template[[well, date]].isna().any(axis=None) or template.duplicated([well, date]).any():
        raise DataContractError("Template WELL_ID/NY keys must be complete and unique.")
    if template.groupby(well, sort=False).size().ne(12).any():
        raise DataContractError("The test template must contain exactly 12 rows per well.")
    parsed = pd.to_datetime(template[date], format="%Y/%m/%d", errors="coerce")
    if parsed.isna().any():
        raise DataContractError("Template NY values must use valid YYYY/MM/DD dates.")


def build_test_samples(tables: MultiSourceTables, config: dict[str, Any]) -> pd.DataFrame:
    if tables.template is None:
        raise DataContractError("Test template is required.")
    anchor_config = require_confirmed_anchor_policy(config)
    target = config.get("schema", {}).get("mapping", {}).get("target", "RCYL")
    template = tables.template.copy()
    if target in template.columns:
        template = template.loc[pd.to_numeric(template[target], errors="coerce").isna()].copy()
    validate_test_template(template, config)
    anchors = identify_last_fracture_anchors(tables.history, config)
    well, date = anchor_config["well_column"], anchor_config["date_column"]
    anchor_map = anchors.set_index(well)["__anchor_time"].to_dict()
    static = _static_feature_map(tables, config)
    template = template.reset_index(drop=True)
    template["__template_order"] = np.arange(len(template))
    template["__normalized_date"] = pd.to_datetime(
        template[date], errors="raise"
    ).dt.strftime("%Y/%m/%d")
    output_rows: list[dict[str, Any]] = []
    offset = int(anchor_config["first_forecast_month_offset"])
    for well_value, group in template.groupby(well, sort=False):
        if well_value not in anchor_map:
            raise DataContractError("A template well has no confirmed last-fracture anchor.")
        anchor_time = pd.Timestamp(anchor_map[well_value])
        ordered = group.sort_values("__template_order", kind="mergesort")
        template_periods = pd.to_datetime(ordered[date], format="%Y/%m/%d").dt.to_period("M").tolist()
        expected = [anchor_time.to_period("M") + offset + horizon - 1 for horizon in range(1, 13)]
        if template_periods != expected:
            raise DataContractError("Template months do not match the confirmed anchor and horizon rule.")
        base = _history_features(tables.history, well_value, anchor_time, config)
        base.update(static.get(well_value, {}))
        for horizon, (_, template_row) in enumerate(ordered.iterrows(), start=1):
            output_rows.append(
                {
                    well: template_row[well],
                    date: template_row["__normalized_date"],
                    "__template_order": int(template_row["__template_order"]),
                    "anchor_time": anchor_time,
                    "horizon": horizon,
                    "forecast_step": horizon,
                    **base,
                }
            )
    output = pd.DataFrame(output_rows).sort_values("__template_order", kind="mergesort").reset_index(drop=True)
    if len(output) != len(template):
        raise DataContractError("Test feature construction changed the template row count.")
    expected_keys = pd.DataFrame(
        {
            well: template[well].astype(str).to_numpy(),
            date: template["__normalized_date"].to_numpy(),
        }
    )
    if not output[[well, date]].astype(str).equals(expected_keys.astype(str)):
        raise DataContractError("Test feature construction changed template keys or order.")
    output.attrs["anchor_policy"] = anchor_policy_metadata(config)
    return output
