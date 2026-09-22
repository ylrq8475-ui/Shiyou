from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from oil_uplift.a2b013_safe import (
    _build_test_panel,
    _build_train_panel,
    _monthly_losses,
    audit_pre_anchor_cutoff,
    safe_config,
    segment_end_anchors,
    validate_exact_result_zip,
    write_result_zip,
)
from oil_uplift.exceptions import DataContractError
from oil_uplift.multistep import MultiSourceTables
from oil_uplift.scoring import official_twelve_month_score


def _config() -> dict:
    return {
        "project": {"allow_external_data": False, "allow_pretrained_weights": False,
                    "random_seed": 20260916},
        "data": {"input_dir": "unused", "sources": {
            "train": {"history": ["unused"], "layer": ["forbidden"],
                      "plan": ["forbidden"], "template": []},
            "test": {"history": ["unused"], "layer": ["forbidden"],
                     "plan": ["forbidden"], "template": ["unused"]}}},
        "schema": {"mapping": {"target": "RCYL"}},
        "anchors": {"well_column": "WELL_ID", "date_column": "NY",
                    "event_column": "CSLB", "eligible_event_values": ["synthetic_event"],
                    "same_month_tie_strategy": "error", "first_forecast_month_offset": 1,
                    "horizon_months": 12},
        "features": {"history_numeric_columns": ["RCYL", "SCTS"],
                     "history_categorical_columns": [], "target_lags": [1, 2],
                     "rolling_windows": [3], "trend_windows": [3]},
        "model": {"candidates": ["extra_trees_log_ratio_last"],
                  "feature_policy": "plus_layer_v1", "calibration_policy": "none",
                  "params": {"extra_trees_log_ratio_last": {
                      "n_estimators": 400, "min_samples_leaf": 6,
                      "max_features": 0.75, "n_jobs": -1}}},
        "scoring": {"epsilon": 1e-6},
    }


def _history(well: str = "synthetic_a") -> pd.DataFrame:
    periods = pd.period_range("2025-01", "2026-03", freq="M")
    return pd.DataFrame({
        "WELL_ID": [well] * len(periods),
        "NY": [period.strftime("%Y/%m/01") for period in periods],
        "CSLB": ["synthetic_event" if period in (pd.Period("2025-02", "M"),
                                                  pd.Period("2025-03", "M")) else "none"
                 for period in periods],
        "RCYL": np.arange(1, len(periods) + 1, dtype=float),
        "SCTS": np.arange(10, 10 + len(periods), dtype=float),
    })


def test_safe_config_disables_layer_and_first_plan_before_loading() -> None:
    source = _config()
    result = safe_config(source, input_dir="another_read_only_root")
    assert result["data"]["sources"]["train"]["layer"] == []
    assert result["data"]["sources"]["test"]["plan"] == []
    assert source["data"]["sources"]["train"]["layer"] == ["forbidden"]
    assert result["data"]["input_dir"] == "another_read_only_root"


def test_safe_config_rejects_model_and_calibration_drift() -> None:
    changed = _config()
    changed["model"]["params"]["extra_trees_log_ratio_last"]["n_estimators"] = 401
    with pytest.raises(DataContractError):
        safe_config(changed)
    changed = _config()
    changed["model"]["calibration_policy"] = "legacy_non_nested_diagnostic"
    with pytest.raises(DataContractError):
        safe_config(changed)


def test_consecutive_months_merge_and_anchor_at_last_segment_end() -> None:
    history = _history()
    anchors, audit = segment_end_anchors(history, _config())
    assert anchors["anchor_period"].tolist() == [pd.Period("2025-03", "M")]
    assert audit["eligible_event_months"] == 2
    assert audit["merged_event_segments"] == 1
    changed = pd.concat([history, pd.DataFrame([{
        "WELL_ID": "synthetic_a", "NY": "2025/06/01",
        "CSLB": "synthetic_event", "RCYL": 5.0, "SCTS": 15.0,
    }])], ignore_index=True)
    # A duplicate production month is rejected, never resolved by row order.
    with pytest.raises(DataContractError):
        segment_end_anchors(changed, _config())


def test_anchor_rows_follow_frozen_well_order_not_file_order() -> None:
    later_name = _history("synthetic_z")
    earlier_name = _history("synthetic_a")
    anchors, _ = segment_end_anchors(pd.concat([later_name, earlier_name], ignore_index=True), _config())
    assert anchors["WELL_ID"].tolist() == ["synthetic_a", "synthetic_z"]


def test_pre_anchor_features_ignore_anchor_and_future_months() -> None:
    history = _history()
    anchors, _ = segment_end_anchors(history, _config())
    original = audit_pre_anchor_cutoff(history, anchors, _config())
    altered = history.copy()
    altered.loc[altered["NY"] >= "2025/03/01", ["RCYL", "SCTS"]] = 999999.0
    changed = audit_pre_anchor_cutoff(altered, anchors, _config())
    assert original["future_sensitive_feature_count"] == 0
    assert changed == original


def test_training_labels_start_after_segment_end_and_use_twelve_months() -> None:
    history = _history()
    panel, audit, anchors = _build_train_panel(
        MultiSourceTables(history, pd.DataFrame(), pd.DataFrame()), _config()
    )
    assert audit["included_wells"] == 1
    assert audit["target_rows"] == 12
    assert panel["horizon"].tolist() == list(range(1, 13))
    assert panel["RCYL"].tolist() == list(np.arange(4, 16, dtype=float))
    assert panel["history__RCYL__last"].tolist() == [2.0] * 12
    assert anchors["anchor_period"].tolist() == [pd.Period("2025-03", "M")]


def test_test_template_must_match_segment_end_next_month() -> None:
    history = _history()
    template = history.loc[history["NY"] >= "2025/04/01"].copy()
    template["RCYL"] = np.nan
    template["NY"] = template["NY"].map(
        lambda text: f"{pd.Timestamp(text).year}/{pd.Timestamp(text).month}/{pd.Timestamp(text).day}"
    )
    tables = MultiSourceTables(history, pd.DataFrame(), pd.DataFrame(), template)
    panel, reference, audit, _ = _build_test_panel(tables, _config())
    assert len(panel) == len(reference) == 12
    assert audit["template_mismatches"] == 0
    assert reference["NY"].tolist() == template["NY"].tolist()
    changed = template.copy()
    changed.loc[changed.index[0], "NY"] = "2025/05/01"
    with pytest.raises(DataContractError):
        _build_test_panel(MultiSourceTables(history, pd.DataFrame(), pd.DataFrame(), changed), _config())


def test_official_metric_monthly_losses_are_unnormalized_and_equal_well() -> None:
    frame = pd.DataFrame({"WELL_ID": ["synthetic_a"] * 12 + ["synthetic_b"] * 12,
                          "horizon": list(range(1, 13)) * 2,
                          "RCYL": [1.0] * 24})
    pred = np.zeros(24, dtype=float)
    monthly = _monthly_losses(frame, pred)
    scored = frame.copy()
    scored["prediction"] = pred
    official = official_twelve_month_score(scored, truth_column="RCYL",
                                           prediction_column="prediction").total
    assert sum(monthly[:4]) == pytest.approx(sum(2.0**-n for n in range(1, 5)) / (1 + 1e-6))
    assert official == pytest.approx(100.0 * (1 - sum(monthly)))


def test_result_zip_is_root_flat_and_byte_deterministic() -> None:
    reference = pd.DataFrame({"WELL_ID": ["synthetic_a"] * 12,
                              "NY": [pd.Period("2026-01", "M") + n for n in range(12)]})
    reference["NY"] = reference["NY"].map(lambda value: f"{value.year}/{value.month}/1")
    frame = reference.copy()
    frame["RCYL"] = np.arange(12, dtype=float)
    scratch = Path.cwd() / "experiments/a2b013/runtime_tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    first = scratch / "synthetic_first.zip"
    second = scratch / "synthetic_second.zip"
    assert write_result_zip(frame, reference, first) == {"wells": 1, "rows": 12, "zip_members": 1}
    write_result_zip(frame, reference, second)
    assert first.read_bytes() == second.read_bytes()
    assert validate_exact_result_zip(first, reference) == {"wells": 1, "rows": 12}
    with zipfile.ZipFile(first) as archive:
        assert len(archive.namelist()) == 1
        assert all("/" not in name for name in archive.namelist())
