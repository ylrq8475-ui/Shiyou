from __future__ import annotations

import platform
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import config_fingerprint, resolve_project_path
from .exceptions import ConfigurationError, DataContractError
from .io import write_json
from .models import build_model
from .multistep import build_training_samples, load_multisource_split
from .scoring import official_twelve_month_score

PANEL_EXCLUDED = {"WELL_ID", "NY", "anchor_time", "RCYL", "__template_order"}
SUPPORTED_CANDIDATES = {
    "median",
    "hist_gradient_boosting",
    "extra_trees",
    "hist_gradient_boosting_weighted",
    "hist_gradient_boosting_poisson_weighted",
    "extra_trees_weighted",
    "extra_trees_log",
    "extra_trees_log_weighted",
    "hist_gradient_boosting_ratio_last",
    "hist_gradient_boosting_ratio_mean",
    "hist_gradient_boosting_log_ratio_last",
    "hist_gradient_boosting_log_ratio_mean",
    "extra_trees_ratio_last",
    "extra_trees_ratio_mean",
    "extra_trees_log_ratio_last",
    "extra_trees_log_ratio_mean",
}
BASELINE_CANDIDATES = {"recent_value", "history_mean", "decline_curve"}
SUPPORTED_CANDIDATES |= BASELINE_CANDIDATES

TARGET_SUFFIXES = {
    "_log_ratio_last": "log_ratio_last",
    "_log_ratio_mean": "log_ratio_mean",
    "_ratio_last": "ratio_last",
    "_ratio_mean": "ratio_mean",
}


def _candidate_spec(name: str) -> tuple[str, str]:
    for suffix, transform in TARGET_SUFFIXES.items():
        if name.endswith(suffix):
            return name[: -len(suffix)], transform
    return name.removesuffix("_weighted"), "identity"


def panel_feature_columns(panel: pd.DataFrame) -> list[str]:
    columns = [
        str(column)
        for column in panel.columns
        if column not in PANEL_EXCLUDED
        and not str(column).startswith("__")
        and not panel[column].isna().all()
    ]
    if "horizon" not in columns:
        raise DataContractError("The multi-horizon panel must contain the horizon feature.")
    if not columns:
        raise DataContractError("No model features remain in the panel.")
    return columns


def configured_feature_columns(panel: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    """Apply an explicit, auditable feature boundary without changing the panel."""
    columns = panel_feature_columns(panel)
    policy = str(config.get("model", {}).get("feature_policy", "all_v1"))
    if policy == "all_v1":
        return columns
    if policy != "plus_layer_v1":
        raise ConfigurationError(f"Unsupported model.feature_policy: {policy}")
    shared = {"horizon", "forecast_step", "history_month_count"}
    selected = [
        column
        for column in columns
        if column in shared
        or column.startswith("history__")
        or column.startswith("layer__")
    ]
    if "horizon" not in selected:
        raise DataContractError("The configured feature policy removed horizon.")
    if any(column.startswith("plan_first__") for column in selected):
        raise DataContractError("plus_layer_v1 must exclude all first-plan features.")
    return selected


def feature_policy_metadata(features: list[str], config: dict[str, Any]) -> dict[str, Any]:
    policy = str(config.get("model", {}).get("feature_policy", "all_v1"))
    payload = json.dumps(features, ensure_ascii=False, separators=(",", ":"))
    return {
        "policy": policy,
        "feature_count": len(features),
        "history_feature_count": sum(column.startswith("history__") for column in features),
        "layer_feature_count": sum(column.startswith("layer__") for column in features),
        "plan_first_feature_count": sum(column.startswith("plan_first__") for column in features),
        "ordered_feature_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def _preprocessor(frame: pd.DataFrame) -> ColumnTransformer:
    numeric = [column for column in frame if pd.api.types.is_numeric_dtype(frame[column])]
    categorical = [column for column in frame if column not in numeric]
    transformers = []
    if numeric:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical,
            )
        )
    return ColumnTransformer(transformers, remainder="drop")


def _model_pipeline(name: str, x: pd.DataFrame, config: dict[str, Any]) -> Pipeline:
    base_name, _ = _candidate_spec(name)
    params = config.get("model", {}).get("params", {}).get(name, {})
    if not params:
        params = config.get("model", {}).get("params", {}).get(base_name, {})
    seed = int(config.get("project", {}).get("random_seed", 20260916))
    return Pipeline(
        [
            ("preprocess", _preprocessor(x)),
            ("model", build_model(base_name, seed, params)),
        ]
    )


def _fit_pipeline(
    estimator: Pipeline,
    name: str,
    x: pd.DataFrame,
    y: pd.Series,
    horizon: pd.Series,
    panel: pd.DataFrame,
) -> None:
    _, transform = _candidate_spec(name)
    fit_target = _transform_target(y, panel, transform)
    if name.endswith("_weighted"):
        steps = pd.to_numeric(horizon, errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(steps).all() or (steps < 1).any():
            raise DataContractError("Official horizon weights require positive finite horizons.")
        weights = np.power(2.0, -steps)
        weights = weights / weights.mean()
        estimator.fit(x, fit_target, model__sample_weight=weights)
    else:
        estimator.fit(x, fit_target)


def _target_scale(panel: pd.DataFrame, transform: str) -> np.ndarray:
    if transform.endswith("_last"):
        column = "history__RCYL__last"
    elif transform.endswith("_mean"):
        column = "history__RCYL__roll_12_mean"
    else:
        return np.ones(len(panel), dtype=float)
    if column not in panel:
        raise DataContractError(f"Target transform {transform} requires {column}.")
    scale = pd.to_numeric(panel[column], errors="coerce").to_numpy(dtype=float)
    fallback = pd.to_numeric(
        panel.get("history__RCYL__last", pd.Series(index=panel.index, dtype=float)),
        errors="coerce",
    ).to_numpy(dtype=float)
    scale = np.where(np.isfinite(scale) & (scale > 0), scale, fallback)
    scale = np.where(np.isfinite(scale) & (scale > 0), scale, 1.0)
    return scale


def _transform_target(y: pd.Series, panel: pd.DataFrame, transform: str) -> np.ndarray:
    values = pd.to_numeric(y, errors="coerce").to_numpy(dtype=float)
    if transform == "identity":
        return values
    ratio = values / _target_scale(panel, transform)
    if transform.startswith("log_"):
        return np.log1p(np.clip(ratio, 0.0, None))
    return ratio


def predict_pipeline_output(
    estimator: Pipeline,
    name: str,
    x: pd.DataFrame,
    panel: pd.DataFrame,
) -> np.ndarray:
    raw = np.asarray(estimator.predict(x), dtype=float)
    _, transform = _candidate_spec(name)
    if transform == "identity":
        return raw
    if transform.startswith("log_"):
        raw = np.expm1(raw)
    return raw * _target_scale(panel, transform)


def _score_prediction_array(panel: pd.DataFrame, prediction: np.ndarray) -> float:
    scored = panel.loc[:, ["WELL_ID", "horizon", "RCYL"]].copy()
    scored["prediction"] = np.clip(np.asarray(prediction, dtype=float), 0.0, None)
    return official_twelve_month_score(
        scored,
        truth_column="RCYL",
        prediction_column="prediction",
        epsilon=1e-6,
    ).total


def _optimal_prediction_scale(panel: pd.DataFrame, prediction: np.ndarray) -> tuple[float, float]:
    factors = np.linspace(0.6, 1.4, 161)
    scored = [(_score_prediction_array(panel, prediction * factor), float(factor)) for factor in factors]
    best_score, best_factor = max(scored, key=lambda item: (item[0], -abs(item[1] - 1.0)))
    return best_factor, best_score


def baseline_predict(panel: pd.DataFrame, name: str) -> np.ndarray:
    """Deterministic, leakage-safe baselines using only pre-anchor features."""
    if name not in BASELINE_CANDIDATES:
        raise ConfigurationError(f"Unknown deterministic baseline: {name}")
    last_column = "history__RCYL__last"
    if last_column not in panel:
        raise DataContractError(f"Baseline {name} requires {last_column}.")
    last = pd.to_numeric(panel[last_column], errors="coerce")
    if name == "recent_value":
        prediction = last
    elif name == "history_mean":
        mean_column = "history__RCYL__roll_12_mean"
        if mean_column not in panel:
            raise DataContractError(f"Baseline {name} requires {mean_column}.")
        prediction = pd.to_numeric(panel[mean_column], errors="coerce").fillna(last)
    else:
        trend_column = "history__RCYL__trend_6"
        if trend_column not in panel or "forecast_step" not in panel:
            raise DataContractError(
                f"Baseline {name} requires {trend_column} and forecast_step."
            )
        trend = pd.to_numeric(panel[trend_column], errors="coerce").fillna(0.0)
        forecast_step = pd.to_numeric(panel["forecast_step"], errors="coerce")
        prediction = last + trend * forecast_step
    values = prediction.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise DataContractError(f"Baseline {name} produced non-finite predictions.")
    return np.clip(values, 0.0, None)


def train_from_panel(
    panel: pd.DataFrame,
    config: dict[str, Any],
    *,
    artifact_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    required = {"WELL_ID", "horizon", "RCYL"}
    missing = sorted(required - set(panel.columns))
    if missing:
        raise DataContractError("Training panel columns are missing: " + ", ".join(missing))
    features = configured_feature_columns(panel, config)
    x = panel.loc[:, features]
    y = pd.to_numeric(panel["RCYL"], errors="coerce")
    if y.isna().any() or not np.isfinite(y.to_numpy(dtype=float)).all():
        raise DataContractError("Training RCYL must be finite and numeric.")
    groups = panel["WELL_ID"]
    well_count = int(groups.nunique())
    if well_count < 2:
        raise DataContractError("At least two wells are required for group-isolated validation.")
    requested_splits = int(config.get("validation", {}).get("n_splits", 5))
    if requested_splits < 2:
        raise ConfigurationError("validation.n_splits must be at least 2.")
    splitter = GroupKFold(n_splits=min(requested_splits, well_count))

    candidates = list(config.get("model", {}).get("candidates", []))
    if not candidates:
        candidates = ["median", "hist_gradient_boosting", "extra_trees"]
    unknown = sorted(set(candidates) - SUPPORTED_CANDIDATES)
    if unknown:
        raise ConfigurationError("Unsupported multi-horizon candidates: " + ", ".join(unknown))
    calibration_policy = str(
        config.get("model", {}).get("calibration_policy", "legacy_non_nested_diagnostic")
    )
    if calibration_policy not in {"none", "legacy_non_nested_diagnostic"}:
        raise ConfigurationError("model.calibration_policy must be none or legacy_non_nested_diagnostic.")

    candidate_reports: list[dict[str, Any]] = []
    for name in candidates:
        oof = np.full(len(panel), np.nan, dtype=float)
        fold_ids = np.zeros(len(panel), dtype=int)
        fold_rows = []
        for fold, (train_index, valid_index) in enumerate(splitter.split(x, y, groups), start=1):
            train_groups = set(groups.iloc[train_index])
            valid_groups = set(groups.iloc[valid_index])
            if train_groups & valid_groups:
                raise DataContractError("A WELL_ID appears in both training and validation folds.")
            fold_ids[valid_index] = fold
            if name in BASELINE_CANDIDATES:
                oof[valid_index] = baseline_predict(panel.iloc[valid_index], name)
            else:
                estimator = _model_pipeline(name, x.iloc[train_index], config)
                _fit_pipeline(
                    estimator,
                    name,
                    x.iloc[train_index],
                    y.iloc[train_index],
                    panel["horizon"].iloc[train_index],
                    panel.iloc[train_index],
                )
                oof[valid_index] = np.clip(
                    predict_pipeline_output(
                        estimator,
                        name,
                        x.iloc[valid_index],
                        panel.iloc[valid_index],
                    ),
                    0.0,
                    None,
                )
            fold_rows.append(
                {
                    "fold": fold,
                    "train_wells": len(train_groups),
                    "validation_wells": len(valid_groups),
                }
            )
        if not np.isfinite(oof).all():
            raise DataContractError("OOF prediction coverage is incomplete.")
        uncalibrated_score = _score_prediction_array(panel, oof)
        if calibration_policy == "none":
            calibrated_score = uncalibrated_score
            deployment_scale = 1.0
            deployment_calibrated_score = uncalibrated_score
            for fold_row in fold_rows:
                fold = int(fold_row["fold"])
                validation_mask = fold_ids == fold
                fold_row["prediction_scale"] = 1.0
                fold_row["official_score"] = _score_prediction_array(
                    panel.loc[validation_mask], oof[validation_mask]
                )
        else:
            calibrated_oof = np.full(len(panel), np.nan, dtype=float)
            for fold_row in fold_rows:
                fold = int(fold_row["fold"])
                calibration_mask = fold_ids != fold
                validation_mask = fold_ids == fold
                fold_scale, _ = _optimal_prediction_scale(
                    panel.loc[calibration_mask], oof[calibration_mask]
                )
                calibrated_oof[validation_mask] = oof[validation_mask] * fold_scale
                fold_row["prediction_scale"] = fold_scale
                fold_row["official_score"] = _score_prediction_array(
                    panel.loc[validation_mask], calibrated_oof[validation_mask]
                )
            calibrated_score = _score_prediction_array(panel, calibrated_oof)
            deployment_scale, deployment_calibrated_score = _optimal_prediction_scale(panel, oof)
        fold_scores = [row["official_score"] for row in fold_rows]
        candidate_reports.append(
            {
                "model": name,
                "official_oof_score": calibrated_score,
                "official_oof_score_uncalibrated": uncalibrated_score,
                "deployment_prediction_scale": deployment_scale,
                "deployment_calibrated_oof_score": deployment_calibrated_score,
                "calibration": calibration_policy,
                "fold_score_mean": float(np.mean(fold_scores)),
                "fold_score_std": float(np.std(fold_scores)),
                "fold_score_min": float(np.min(fold_scores)),
                "fold_score_max": float(np.max(fold_scores)),
                "folds": fold_rows,
            }
        )

    selected = max(candidate_reports, key=lambda item: item["official_oof_score"])
    final_pipeline = None
    if selected["model"] not in BASELINE_CANDIDATES:
        final_pipeline = _model_pipeline(selected["model"], x, config)
        _fit_pipeline(final_pipeline, selected["model"], x, y, panel["horizon"], panel)
    anchor_policy = panel.attrs.get("anchor_policy")
    training_window_audit = panel.attrs.get("training_window_audit")
    feature_policy = feature_policy_metadata(features, config)
    artifact = {
        "artifact_version": 5,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_name": selected["model"],
        "pipeline": final_pipeline,
        "deterministic_baseline": selected["model"] in BASELINE_CANDIDATES,
        "target_transform": _candidate_spec(selected["model"])[1],
        "prediction_scale": selected["deployment_prediction_scale"],
        "feature_columns": features,
        "feature_policy": feature_policy,
        "calibration_policy": calibration_policy,
        "config_fingerprint": config_fingerprint(config),
        "anchor_policy": anchor_policy,
        "training_window_audit": training_window_audit,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    report = {
        "selected_model": selected["model"],
        "selection_score": selected["official_oof_score"],
        "selection_metric": "official_oof_score_uncalibrated" if calibration_policy == "none" else "official_oof_score",
        "formula_version": "official_12m_smape_v1",
        "validation": "GroupKFold by WELL_ID; no well crosses folds",
        "anchor_policy": anchor_policy,
        "training_window_audit": training_window_audit,
        "training_wells": well_count,
        "feature_policy": feature_policy,
        "calibration_policy": calibration_policy,
        "candidates": candidate_reports,
    }
    if artifact_path is not None:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, artifact_path)
    return artifact, report


def run_training(config: dict[str, Any]) -> dict[str, Any]:
    tables = load_multisource_split(config, "train")
    panel = build_training_samples(tables, config)
    model_config = config.get("model", {})
    artifact_path = resolve_project_path(config, model_config.get("artifact_path", "artifacts/model.joblib"))
    _, report = train_from_panel(panel, config, artifact_path=artifact_path)
    report_path = resolve_project_path(
        config, model_config.get("metrics_output", "artifacts/validation_metrics.json")
    )
    write_json(report, report_path)
    return report


def load_model_artifact(path: Path) -> dict[str, Any]:
    try:
        artifact = joblib.load(path)
    except Exception as exc:
        raise DataContractError("Unable to load the local model artifact; its path is suppressed.") from exc
    required = {
        "artifact_version",
        "pipeline",
        "feature_columns",
        "config_fingerprint",
        "model_name",
        "deterministic_baseline",
        "target_transform",
        "prediction_scale",
        "anchor_policy",
        "training_window_audit",
    }
    if not isinstance(artifact, dict) or not required.issubset(artifact):
        raise DataContractError("The local model artifact has an invalid structure.")
    if artifact["artifact_version"] != 5:
        raise DataContractError("Unsupported model artifact version.")
    return artifact
