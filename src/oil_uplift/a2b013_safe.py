"""A2B-013: latest segment-end, next-month, no-layer safety boundary.

Only aggregate diagnostics may leave this module. Well keys, targets and
predictions stay in memory except for the explicitly authorized result ZIP.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .exceptions import DataContractError
from .multistep import (
    MultiSourceTables,
    _history_features,
    _training_window_targets,
    load_multisource_split,
)
from .scoring import official_twelve_month_score
from .submission import well_csv_filename
from .training import (
    _fit_pipeline,
    _model_pipeline,
    configured_feature_columns,
    predict_pipeline_output,
)


MODEL_NAME = "extra_trees_log_ratio_last"
EXPECTED_PARAMS = {
    "n_estimators": 400,
    "min_samples_leaf": 6,
    "max_features": 0.75,
    "n_jobs": -1,
}
EXPECTED_FEATURE_COUNT = 325
OFFICIAL_COLUMNS = ["WELL_ID", "NY", "RCYL"]


@dataclass
class SafeData:
    train: pd.DataFrame
    test: pd.DataFrame
    reference: pd.DataFrame
    features: list[str]
    audit: dict[str, Any]


def safe_config(source: dict[str, Any], input_dir: str | None = None) -> dict[str, Any]:
    """Disable layer and plan loading before any raw tables are opened."""
    config = copy.deepcopy(source)
    if input_dir is not None:
        config["data"]["input_dir"] = input_dir
    if config.get("project", {}).get("allow_external_data") is not False:
        raise DataContractError("External data is forbidden.")
    if config.get("project", {}).get("allow_pretrained_weights") is not False:
        raise DataContractError("Pretrained weights are forbidden.")
    if config.get("project", {}).get("random_seed") != 20260916:
        raise DataContractError("The frozen random seed changed.")
    model = config.get("model", {})
    if model.get("candidates") != [MODEL_NAME]:
        raise DataContractError("The frozen model choice changed.")
    if model.get("params", {}).get(MODEL_NAME) != EXPECTED_PARAMS:
        raise DataContractError("The frozen ExtraTrees parameters changed.")
    if model.get("calibration_policy") != "none":
        raise DataContractError("Calibration is forbidden.")
    if model.get("feature_policy") != "plus_layer_v1":
        raise DataContractError("The frozen history feature specification changed.")
    anchor = config.get("anchors", {})
    if anchor.get("first_forecast_month_offset") != 1 or anchor.get("horizon_months") != 12:
        raise DataContractError("The approved forecast horizon changed.")
    if not anchor.get("eligible_event_values") or anchor.get("same_month_tie_strategy") != "error":
        raise DataContractError("Eligible event or duplicate-month rule changed.")
    if config.get("scoring", {}).get("epsilon") != 1e-6:
        raise DataContractError("The official scoring epsilon changed.")
    for split in ("train", "test"):
        roles = config["data"]["sources"][split]
        roles["layer"] = []
        roles["plan"] = []
    return config


def _periods(frame: pd.DataFrame, date_column: str) -> pd.Series:
    parsed = pd.to_datetime(frame[date_column], errors="coerce")
    if parsed.isna().any():
        raise DataContractError("History contains an invalid calendar date.")
    return parsed.dt.to_period("M")


def segment_end_anchors(history: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, int]]:
    """Merge consecutive eligible months, then select the last segment end."""
    anchor = config["anchors"]
    well, date, event = anchor["well_column"], anchor["date_column"], anchor["event_column"]
    if not {well, date, event}.issubset(history.columns):
        raise DataContractError("A required anchor field is absent.")
    local = history.loc[:, [well, date, event]].copy()
    local["__period"] = _periods(local, date)
    if local[[well, "__period"]].duplicated().any():
        raise DataContractError("A well has duplicate records in one natural month.")
    eligible = local.loc[local[event].isin(anchor["eligible_event_values"])]
    if eligible.empty:
        raise DataContractError("No eligible event month was found.")
    rows: list[dict[str, Any]] = []
    segment_count = 0
    for well_value, group in eligible.groupby(well, sort=False):
        ordered = sorted(group["__period"].tolist())
        previous = ordered[0]
        latest_end = previous
        segment_count += 1
        for current in ordered[1:]:
            if current.ordinal != previous.ordinal + 1:
                segment_count += 1
            previous = current
            latest_end = current
        rows.append({well: well_value, "anchor_period": latest_end})
    # The frozen training path sorts latest anchors by WELL_ID. Preserve that
    # deterministic training-row order because ExtraTrees' seeded random draw
    # sequence is sensitive to input row order even when values are identical.
    anchors = pd.DataFrame(rows).sort_values(well, kind="mergesort").reset_index(drop=True)
    if anchors[well].duplicated().any():
        raise DataContractError("A latest-event anchor is not unique by well.")
    return anchors, {
        "eligible_wells": int(len(anchors)),
        "eligible_event_months": int(len(eligible)),
        "merged_event_segments": int(segment_count),
    }


def _safe_history_values(
    history: pd.DataFrame,
    well_value: Any,
    anchor_period: pd.Period,
    config: dict[str, Any],
) -> dict[str, Any]:
    # _history_features with the prior month includes records through that
    # month; therefore no anchor-month or later dynamic value can enter.
    prior_month = (anchor_period - 1).to_timestamp()
    values = _history_features(history, well_value, prior_month, config)
    return {
        "history_month_count": values["history_month_count"],
        **{key: value for key, value in values.items() if key.startswith("history__")},
    }


def _same_feature_value(left: Any, right: Any) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    if isinstance(left, (float, int, np.number)) and isinstance(right, (float, int, np.number)):
        return bool(np.isclose(left, right, rtol=0, atol=0, equal_nan=True))
    return bool(left == right)


def audit_pre_anchor_cutoff(
    history: pd.DataFrame,
    anchors: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, int]:
    well, date = config["anchors"]["well_column"], config["anchors"]["date_column"]
    work = history.copy()
    work["__period"] = _periods(work, date)
    checked = 0
    for item in anchors.to_dict("records"):
        well_value, anchor_period = item[well], item["anchor_period"]
        full = _safe_history_values(history, well_value, anchor_period, config)
        restricted = work.loc[
            (work[well] == well_value) & (work["__period"] < anchor_period)
        ].drop(columns="__period")
        trimmed = _safe_history_values(restricted, well_value, anchor_period, config)
        if full.keys() != trimmed.keys() or not all(
            _same_feature_value(full[key], trimmed[key]) for key in full
        ):
            raise DataContractError("A history feature changes after future rows are excluded.")
        checked += len(full)
    return {"events_checked": int(len(anchors)), "feature_values_checked": checked,
            "future_sensitive_feature_count": 0}


def _build_train_panel(tables: MultiSourceTables, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    history = tables.history
    well = config["anchors"]["well_column"]
    anchors, segment_audit = segment_end_anchors(history, config)
    rows: list[dict[str, Any]] = []
    exclusions: dict[str, int] = {}
    included: list[dict[str, Any]] = []
    for item in anchors.to_dict("records"):
        well_value, anchor_period = item[well], item["anchor_period"]
        periods = [anchor_period + step for step in range(1, 13)]
        targets, reason = _training_window_targets(history, well_value, periods, config)
        if reason is not None:
            exclusions[reason] = exclusions.get(reason, 0) + 1
            continue
        if targets is None or len(targets) != 12 or any(value < 0 for value in targets):
            raise DataContractError("A complete training target window is invalid.")
        base = _safe_history_values(history, well_value, anchor_period, config)
        for step, target_value in enumerate(targets, start=1):
            rows.append({well: well_value, "anchor_time": anchor_period.to_timestamp(),
                         "horizon": step, "forecast_step": step, "RCYL": target_value,
                         **base})
        included.append(item)
    panel = pd.DataFrame(rows)
    if panel.empty or panel.groupby(well).size().ne(12).any():
        raise DataContractError("No complete latest-event training cohort remains.")
    if panel[[well, "horizon"]].duplicated().any():
        raise DataContractError("The training target expansion has duplicate rows.")
    audit = {**segment_audit, "included_wells": int(panel[well].nunique()),
             "excluded_wells": int(sum(exclusions.values())),
             "exclusion_reason_counts": exclusions, "target_rows": int(len(panel)),
             "duplicate_target_rows": 0}
    return panel, audit, pd.DataFrame(included)


def _build_test_panel(tables: MultiSourceTables, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int], pd.DataFrame]:
    if tables.template is None:
        raise DataContractError("The official test template is absent.")
    well, date = config["anchors"]["well_column"], config["anchors"]["date_column"]
    target = config["schema"]["mapping"]["target"]
    template = tables.template.copy()
    if target in template:
        template = template.loc[pd.to_numeric(template[target], errors="coerce").isna()].copy()
    if template.empty or not {well, date}.issubset(template):
        raise DataContractError("The test template has no valid target keys.")
    reference = template.loc[:, [well, date]].reset_index(drop=True)
    if reference.isna().any(axis=None) or reference.duplicated().any():
        raise DataContractError("Test template keys are missing or duplicated.")
    if reference.groupby(well, sort=False).size().ne(12).any():
        raise DataContractError("Each test well must have exactly 12 template rows.")
    dates = pd.to_datetime(reference[date], format="mixed", errors="coerce")
    if dates.isna().any() or not reference[date].map(lambda value: isinstance(value, str)).all():
        raise DataContractError("Test template dates are not valid strings.")
    anchors, segment_audit = segment_end_anchors(tables.history, config)
    anchor_map = anchors.set_index(well)["anchor_period"].to_dict()
    rows: list[dict[str, Any]] = []
    used: list[dict[str, Any]] = []
    for well_value, group in reference.groupby(well, sort=False):
        if well_value not in anchor_map:
            raise DataContractError("A test well lacks a latest segment-end anchor.")
        anchor_period = anchor_map[well_value]
        actual = pd.to_datetime(group[date], format="mixed").dt.to_period("M").tolist()
        expected = [anchor_period + step for step in range(1, 13)]
        if actual != expected:
            raise DataContractError("Test template months differ from segment-end plus one.")
        base = _safe_history_values(tables.history, well_value, anchor_period, config)
        for step, (_, template_row) in enumerate(group.iterrows(), start=1):
            rows.append({well: template_row[well], date: template_row[date],
                         "anchor_time": anchor_period.to_timestamp(),
                         "horizon": step, "forecast_step": step, **base})
        used.append({well: well_value, "anchor_period": anchor_period})
    panel = pd.DataFrame(rows)
    if panel.loc[:, [well, date]].astype(str).values.tolist() != reference.astype(str).values.tolist():
        raise DataContractError("Test panel keys changed order from the template.")
    return panel, reference, {**segment_audit, "test_wells": int(reference[well].nunique()),
                              "template_rows": int(len(reference)), "template_mismatches": 0}, pd.DataFrame(used)


def build_safe_data(config: dict[str, Any]) -> SafeData:
    train_tables = load_multisource_split(config, "train")
    test_tables = load_multisource_split(config, "test")
    if not train_tables.layer.empty or not train_tables.plan.empty or not test_tables.layer.empty or not test_tables.plan.empty:
        raise DataContractError("Layer or first-plan data were loaded into the safe pipeline.")
    train, train_audit, train_anchors = _build_train_panel(train_tables, config)
    test, reference, test_audit, test_anchors = _build_test_panel(test_tables, config)
    features = configured_feature_columns(train, config)
    if len(features) != EXPECTED_FEATURE_COUNT or any(
        name.startswith(("layer__", "plan_first__")) for name in features
    ):
        raise DataContractError("The no-layer 325-feature boundary changed.")
    if list(test.loc[:, features].columns) != features:
        raise DataContractError("Train/test feature columns do not align.")
    if set(train["WELL_ID"]) & set(test["WELL_ID"]):
        raise DataContractError("A train well appears in the test template.")
    cutoff_train = audit_pre_anchor_cutoff(train_tables.history, train_anchors, config)
    cutoff_test = audit_pre_anchor_cutoff(test_tables.history, test_anchors, config)
    audit = {
        "train": train_audit,
        "test": test_audit,
        "feature_count": len(features),
        "history_feature_count": sum(name.startswith("history__") for name in features),
        "layer_feature_count": 0,
        "first_plan_feature_count": 0,
        "train_test_well_overlap": 0,
        "cutoff_train": cutoff_train,
        "cutoff_test": cutoff_test,
    }
    return SafeData(train, test, reference, features, audit)


def _official_score(panel: pd.DataFrame, prediction: np.ndarray) -> float:
    work = panel.loc[:, ["WELL_ID", "horizon", "RCYL"]].copy()
    work["prediction"] = prediction
    return official_twelve_month_score(work, truth_column="RCYL", prediction_column="prediction", epsilon=1e-6).total


def _monthly_losses(panel: pd.DataFrame, prediction: np.ndarray) -> list[float]:
    truth = panel["RCYL"].to_numpy(dtype=float)
    step = panel["horizon"].to_numpy(dtype=int)
    if not np.isfinite(truth).all() or not np.isfinite(prediction).all():
        raise DataContractError("OOF loss inputs are not finite.")
    weighted = np.power(0.5, step) * np.abs(prediction - truth) / (np.abs(prediction) + np.abs(truth) + 1e-6)
    return [float(np.mean(weighted[step == month])) for month in range(1, 13)]


def fit_and_predict(train: pd.DataFrame, valid: pd.DataFrame, features: list[str], config: dict[str, Any]) -> tuple[Any, np.ndarray]:
    estimator = _model_pipeline(MODEL_NAME, train.loc[:, features], config)
    _fit_pipeline(estimator, MODEL_NAME, train.loc[:, features], train["RCYL"],
                  train["horizon"], train)
    raw = predict_pipeline_output(estimator, MODEL_NAME, valid.loc[:, features], valid)
    if not np.isfinite(raw).all():
        raise DataContractError("The model produced a non-finite prediction.")
    return estimator, np.clip(raw, 0.0, None)


def evaluate_fixed_oof(data: SafeData, config: dict[str, Any]) -> dict[str, Any]:
    panel = data.train
    splitter = GroupKFold(n_splits=5)
    groups = panel["WELL_ID"]
    oof = np.full(len(panel), np.nan, dtype=float)
    fold_scores: list[float] = []
    fold_counts: list[dict[str, int]] = []
    for fold, (train_idx, valid_idx) in enumerate(splitter.split(panel, panel["RCYL"], groups), start=1):
        train_wells = set(groups.iloc[train_idx])
        valid_wells = set(groups.iloc[valid_idx])
        if train_wells & valid_wells:
            raise DataContractError("A WELL_ID crossed a validation fold.")
        _, pred = fit_and_predict(panel.iloc[train_idx], panel.iloc[valid_idx], data.features, config)
        oof[valid_idx] = pred
        fold_scores.append(_official_score(panel.iloc[valid_idx], pred))
        fold_counts.append({"fold": fold, "training_wells": len(train_wells),
                            "validation_wells": len(valid_wells)})
    if not np.isfinite(oof).all() or (oof < 0).any():
        raise DataContractError("OOF coverage or prediction constraints failed.")
    score = _official_score(panel, oof)
    month = _monthly_losses(panel, oof)
    independent_score = 100.0 * (1.0 - sum(month))
    if abs(score - independent_score) > 1e-10:
        raise DataContractError("Independent official metric check failed.")
    return {
        "official_oof": score,
        "independent_metric_absolute_error": abs(score - independent_score),
        "fold_scores": fold_scores,
        "worst_fold_score": float(min(fold_scores)),
        "fold_score_std": float(np.std(fold_scores)),
        "fold_counts": fold_counts,
        "monthly_weighted_loss": month,
        "month_1_loss": month[0],
        "months_1_2_loss": float(sum(month[:2])),
        "months_1_4_loss": float(sum(month[:4])),
        "months_1_12_loss": float(sum(month)),
        "negative_prediction_count": 0,
        "nan_prediction_count": 0,
        "inf_prediction_count": 0,
        "duplicate_target_row_count": 0,
        "row_level_oof_persisted": False,
    }


def train_final(data: SafeData, config: dict[str, Any], artifact_path: Path, config_sha256: str, plan_sha256: str) -> dict[str, Any]:
    estimator, prediction = fit_and_predict(data.train, data.test, data.features, config)
    artifact = {
        "version": "A2B-013-END_T1_CM1_NL",
        "model_name": MODEL_NAME,
        "pipeline": estimator,
        "feature_columns": data.features,
        "config_sha256": config_sha256,
        "plan_sha256": plan_sha256,
        "feature_sha256": hashlib.sha256(json.dumps(data.features, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    return {"artifact": artifact, "test_prediction": prediction}


def infer_from_artifact(artifact_path: Path, data: SafeData, config_sha256: str, plan_sha256: str) -> np.ndarray:
    artifact = joblib.load(artifact_path)
    if artifact.get("version") != "A2B-013-END_T1_CM1_NL" or artifact.get("model_name") != MODEL_NAME:
        raise DataContractError("The A2B-013 artifact identity is invalid.")
    if artifact.get("config_sha256") != config_sha256 or artifact.get("plan_sha256") != plan_sha256:
        raise DataContractError("The A2B-013 model/config/plan fingerprints differ.")
    if artifact.get("feature_columns") != data.features:
        raise DataContractError("The inference feature order differs from training.")
    raw = predict_pipeline_output(artifact["pipeline"], MODEL_NAME, data.test.loc[:, data.features], data.test)
    if not np.isfinite(raw).all():
        raise DataContractError("Repeated inference produced non-finite predictions.")
    return np.clip(raw, 0.0, None)


def result_frame(data: SafeData, prediction: np.ndarray) -> pd.DataFrame:
    frame = data.reference.loc[:, ["WELL_ID", "NY"]].copy()
    if len(frame) != len(prediction):
        raise DataContractError("Template/prediction row counts differ.")
    frame["RCYL"] = np.asarray(prediction, dtype=float)
    validate_exact_template_result(frame, data.reference)
    return frame


def validate_exact_template_result(frame: pd.DataFrame, reference: pd.DataFrame) -> dict[str, int]:
    """Preserve the source-template NY lexemes exactly, including no zero padding."""
    if list(frame.columns) != OFFICIAL_COLUMNS or frame.empty:
        raise DataContractError("The result has an invalid column contract.")
    if not {"WELL_ID", "NY"}.issubset(reference.columns):
        raise DataContractError("The test reference key contract is invalid.")
    keys = frame.loc[:, ["WELL_ID", "NY"]].astype(str).values.tolist()
    expected = reference.loc[:, ["WELL_ID", "NY"]].astype(str).values.tolist()
    if keys != expected:
        raise DataContractError("Result WELL_ID/NY keys or row order differ from the template.")
    if frame.loc[:, ["WELL_ID", "NY"]].duplicated().any():
        raise DataContractError("Result keys contain duplicates.")
    counts = frame.groupby("WELL_ID", sort=False).size()
    if counts.empty or counts.ne(12).any():
        raise DataContractError("Every result well must have 12 rows.")
    dates = pd.to_datetime(frame["NY"], format="mixed", errors="coerce")
    if dates.isna().any():
        raise DataContractError("Result dates cannot be parsed.")
    prediction = pd.to_numeric(frame["RCYL"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(prediction).all() or (prediction < 0).any():
        raise DataContractError("Result predictions must be finite and non-negative.")
    return {"wells": int(len(counts)), "rows": int(len(frame))}


def validate_exact_result_zip(path: Path, reference: pd.DataFrame) -> dict[str, int]:
    frames = []
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if not names or len(names) != len(set(name.casefold() for name in names)):
            raise DataContractError("The result ZIP has missing or duplicate members.")
        if any("/" in name or "\\" in name or not name.lower().endswith(".csv") for name in names):
            raise DataContractError("The result ZIP must contain only root-level CSV files.")
        for name in names:
            frame = pd.read_csv(io.BytesIO(archive.read(name)), encoding="utf-8-sig",
                                dtype={"WELL_ID": "string", "NY": "string"}).astype(
                                    {"WELL_ID": object, "NY": object})
            if list(frame.columns) != OFFICIAL_COLUMNS or frame["WELL_ID"].nunique(dropna=False) != 1:
                raise DataContractError("A result ZIP member has an invalid per-well schema.")
            if name != well_csv_filename(frame["WELL_ID"].iloc[0]):
                raise DataContractError("A result ZIP filename differs from its WELL_ID.")
            frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    if combined.loc[:, ["WELL_ID", "NY"]].duplicated().any():
        raise DataContractError("Extracted result keys are duplicated.")
    expected_keys = [tuple(item) for item in reference.loc[:, ["WELL_ID", "NY"]].astype(str).values.tolist()]
    keyed = combined.set_index(["WELL_ID", "NY"], drop=False)
    actual_keys = set(tuple(item) for item in keyed.index.tolist())
    if actual_keys != set(expected_keys):
        raise DataContractError("Extracted result keys differ from the exact template.")
    ordered = keyed.loc[expected_keys].reset_index(drop=True)
    return validate_exact_template_result(ordered, reference)


def write_result_zip(frame: pd.DataFrame, reference: pd.DataFrame, output_path: Path) -> dict[str, int]:
    """Create a byte-deterministic root-flat official ZIP without loose CSV files."""
    validation = validate_exact_template_result(frame, reference)
    names = set()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for well_value, group in frame.groupby("WELL_ID", sort=False):
            name = well_csv_filename(well_value)
            if name.casefold() in names:
                raise DataContractError("Per-well output filenames collide.")
            names.add(name.casefold())
            body = group.loc[:, OFFICIAL_COLUMNS].to_csv(index=False, float_format="%.6f").encode("utf-8-sig")
            entry = zipfile.ZipInfo(name, date_time=(2026, 9, 22, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, body, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    zipped = validate_exact_result_zip(output_path, reference)
    if zipped != validation or len(names) != validation["wells"]:
        raise DataContractError("Extracted result ZIP fails the official output contract.")
    return {"wells": validation["wells"], "rows": validation["rows"], "zip_members": len(names)}
