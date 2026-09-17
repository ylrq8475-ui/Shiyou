import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_uplift.inference import predict_from_panel
from oil_uplift.exceptions import ConfigurationError
from oil_uplift.training import (
    baseline_predict,
    configured_feature_columns,
    panel_feature_columns,
    train_from_panel,
)


def make_config():
    return {
        "project": {
            "random_seed": 20260916,
            "allow_external_data": False,
            "allow_pretrained_weights": False,
        },
        "validation": {"n_splits": 3},
        "model": {
            "candidates": ["median", "hist_gradient_boosting", "extra_trees"],
            "params": {
                "hist_gradient_boosting": {"max_iter": 10},
                "extra_trees": {"n_estimators": 10, "n_jobs": 1},
            },
        },
        "scoring": {
            "confirmed": True,
            "formula_version": "official_12m_smape_v1",
            "epsilon": 1e-6,
            "direction": "maximize",
        },
        "submission": {"encoding": "utf-8-sig"},
    }


def make_panel(include_target=True):
    rows = []
    for well_index, well in enumerate(["A", "B", "C"], start=1):
        for horizon, date in enumerate(pd.date_range("2022-01-01", periods=12, freq="MS"), start=1):
            row = {
                "WELL_ID": well,
                "NY": date.strftime("%Y/%m/%d"),
                "anchor_time": pd.Timestamp("2022-01-01"),
                "horizon": horizon,
                "forecast_step": horizon,
                "history__RCYL__last": float(10 * well_index),
                "history__RCYL__roll_12_mean": float(10 * well_index - 1),
                "history__RCYL__trend_6": 1.0,
                "layer__KXD__mean": float(well_index),
                "plan_first__type": "X" if well_index < 3 else "Y",
                "__template_order": len(rows),
            }
            if include_target:
                row["RCYL"] = float(10 * well_index + horizon)
            rows.append(row)
    return pd.DataFrame(rows)


def test_group_isolated_training_and_panel_inference_preserve_template_order():
    config = make_config()
    train = make_panel(include_target=True)
    features = panel_feature_columns(train)
    assert "horizon" in features
    assert not {"WELL_ID", "NY", "anchor_time", "RCYL", "__template_order"} & set(features)
    artifact, report = train_from_panel(train, config)
    assert report["selected_model"] in {"median", "hist_gradient_boosting", "extra_trees"}
    for candidate in report["candidates"]:
        for fold in candidate["folds"]:
            assert fold["train_wells"] + fold["validation_wells"] == 3

    test = make_panel(include_target=False)
    prediction = predict_from_panel(test, artifact, config)
    assert list(prediction.columns) == ["WELL_ID", "NY", "RCYL"]
    assert len(prediction) == len(test)
    assert prediction[["WELL_ID", "NY"]].astype(str).equals(test[["WELL_ID", "NY"]].astype(str))
    assert (prediction["RCYL"] >= 0).all()


def test_explicit_baselines_are_compared_and_report_fold_stability():
    config = make_config()
    config["model"]["candidates"] = ["recent_value", "history_mean", "decline_curve"]
    train = make_panel(include_target=True)
    artifact, report = train_from_panel(train, config)
    assert report["selected_model"] == "decline_curve"
    assert artifact["deterministic_baseline"] is True
    assert artifact["pipeline"] is None
    for candidate in report["candidates"]:
        assert {"fold_score_mean", "fold_score_std", "fold_score_min", "fold_score_max"} <= set(candidate)
        assert all("official_score" in fold for fold in candidate["folds"])
    prediction = predict_from_panel(make_panel(include_target=False), artifact, config)
    assert len(prediction) == 36
    assert (prediction["RCYL"] >= 0).all()


def test_decline_baseline_uses_actual_forecast_step_and_rejects_invalid_fold_count():
    panel = make_panel(include_target=True)
    first = panel.index[0]
    panel.loc[first, "history__RCYL__last"] = 10.0
    panel.loc[first, "history__RCYL__trend_6"] = 2.0
    panel.loc[first, "horizon"] = 1
    panel.loc[first, "forecast_step"] = 2
    prediction = baseline_predict(panel.loc[[first]], "decline_curve")
    assert prediction.tolist() == [14.0]

    config = make_config()
    config["validation"]["n_splits"] = 1
    with pytest.raises(ConfigurationError, match="at least 2"):
        train_from_panel(panel, config)


def test_artifact_and_validation_report_keep_auditable_anchor_policy_metadata():
    panel = make_panel(include_target=True)
    policy = {
        "approval_id": "B2U-001",
        "rule_version": "data_inferred_latest_record_v1",
        "eligible_event_value_count": 2,
        "eligible_event_value_sha256": ["a" * 64, "b" * 64],
    }
    panel.attrs["anchor_policy"] = policy
    panel.attrs["training_window_audit"] = {
        "candidate_wells": 3,
        "included_wells": 3,
        "excluded_wells": 0,
        "exclusion_reason_counts": {},
    }
    artifact, report = train_from_panel(panel, make_config())
    assert artifact["artifact_version"] == 5
    assert artifact["anchor_policy"] == policy
    assert report["anchor_policy"] == policy
    assert report["training_window_audit"]["excluded_wells"] == 0
    assert artifact["prediction_scale"] > 0


def test_all_missing_features_are_removed_and_weighted_log_models_train():
    panel = make_panel(include_target=True)
    panel["all_missing"] = pd.NA
    assert "all_missing" not in panel_feature_columns(panel)
    config = make_config()
    config["model"]["candidates"] = [
        "hist_gradient_boosting_weighted",
        "hist_gradient_boosting_poisson_weighted",
        "extra_trees_weighted",
        "extra_trees_log_weighted",
    ]
    config["model"]["params"] = {
        "hist_gradient_boosting_weighted": {"max_iter": 10},
        "hist_gradient_boosting_poisson_weighted": {"max_iter": 10},
        "extra_trees_weighted": {"n_estimators": 10, "n_jobs": 1},
        "extra_trees_log_weighted": {"n_estimators": 10, "n_jobs": 1},
    }
    artifact, report = train_from_panel(panel, config)
    assert artifact["model_name"] in set(config["model"]["candidates"])
    assert len(report["candidates"]) == 4


def test_ratio_target_models_train_and_restore_absolute_scale():
    panel = make_panel(include_target=True)
    config = make_config()
    config["model"]["candidates"] = [
        "hist_gradient_boosting_ratio_last",
        "hist_gradient_boosting_log_ratio_mean",
        "extra_trees_ratio_mean",
        "extra_trees_log_ratio_last",
    ]
    config["model"]["params"] = {
        "hist_gradient_boosting_ratio_last": {"max_iter": 10},
        "hist_gradient_boosting_log_ratio_mean": {"max_iter": 10},
        "extra_trees_ratio_mean": {"n_estimators": 10, "n_jobs": 1},
        "extra_trees_log_ratio_last": {"n_estimators": 10, "n_jobs": 1},
    }
    artifact, report = train_from_panel(panel, config)
    prediction = predict_from_panel(make_panel(include_target=False), artifact, config)
    assert artifact["target_transform"] != "identity"
    assert len(report["candidates"]) == 4
    assert np.isfinite(prediction["RCYL"]).all()
    assert (prediction["RCYL"] >= 0).all()


def test_plus_layer_policy_excludes_plan_and_disables_prediction_scaling():
    panel = make_panel(include_target=True)
    config = make_config()
    config["model"]["candidates"] = ["extra_trees_log_ratio_last"]
    config["model"]["params"] = {
        "extra_trees_log_ratio_last": {"n_estimators": 10, "n_jobs": 1}
    }
    config["model"]["feature_policy"] = "plus_layer_v1"
    config["model"]["calibration_policy"] = "none"
    features = configured_feature_columns(panel, config)
    assert not any(column.startswith("plan_first__") for column in features)
    artifact, report = train_from_panel(panel, config)
    assert artifact["prediction_scale"] == 1.0
    assert artifact["calibration_policy"] == "none"
    assert artifact["feature_policy"]["plan_first_feature_count"] == 0
    assert report["selection_metric"] == "official_oof_score_uncalibrated"
    candidate = report["candidates"][0]
    assert candidate["official_oof_score"] == candidate["official_oof_score_uncalibrated"]
    assert all(fold["prediction_scale"] == 1.0 for fold in candidate["folds"])


def test_unknown_feature_policy_fails_closed():
    config = make_config()
    config["model"]["feature_policy"] = "unknown"
    with pytest.raises(ConfigurationError, match="feature_policy"):
        configured_feature_columns(make_panel(include_target=True), config)
