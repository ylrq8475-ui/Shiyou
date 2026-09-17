import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_uplift.exceptions import DataContractError, PolicyBlockedError
from oil_uplift.multistep import (
    MultiSourceTables,
    build_test_samples,
    build_training_samples,
    identify_last_fracture_anchors,
)


def config():
    return {
        "anchors": {
            "confirmed": True,
            "rule_version": "synthetic-only",
            "approval_id": "B2U-001",
            "evidence_level": "data_inferred_user_approved",
            "event_semantics": "independent_monthly_events",
            "well_column": "WELL_ID",
            "date_column": "NY",
            "event_column": "CSLB",
            "eligible_event_values": ["F"],
            "continuous_event_strategy": "record_level_latest",
            "selection_strategy": "last_candidate_month",
            "same_month_tie_strategy": "error",
            "first_forecast_month_offset": 1,
            "incomplete_training_window_strategy": "exclude_with_audit",
            "horizon_months": 12,
            "tie_break_columns": [],
        },
        "schema": {"mapping": {"target": "RCYL"}},
        "features": {
            "history_numeric_columns": ["RCYL", "SCTS"],
            "history_categorical_columns": ["CYFS"],
            "target_lags": [1, 2, 3],
            "rolling_windows": [3],
            "trend_windows": [3],
            "layer_well_column": "WELL_ID",
            "layer_numeric_columns": ["KXD"],
            "plan_well_column": "井号",
            "plan_date_column": "完工日期",
            "plan_numeric_columns": ["石英砂用量"],
            "plan_categorical_columns": ["压裂方式"],
        },
    }


def history(target_shift=0.0, include_future=True):
    dates = pd.date_range("2021-01-01", periods=25, freq="MS")
    frame = pd.DataFrame(
        {
            "WELL_ID": ["SYNTHETIC"] * len(dates),
            "NY": dates,
            "RCYL": np.arange(1, len(dates) + 1, dtype=float),
            "SCTS": [28.0] * len(dates),
            "CYFS": ["X"] * len(dates),
            "CSLB": [None] * len(dates),
        }
    )
    frame.loc[12, "CSLB"] = "F"  # synthetic anchor: 2022-01
    if target_shift:
        frame.loc[13:24, "RCYL"] += target_shift
    if not include_future:
        frame.loc[13:24, "RCYL"] = np.nan
    return frame


def layer():
    return pd.DataFrame({"WELL_ID": ["SYNTHETIC", "SYNTHETIC"], "KXD": [10.0, 20.0]})


def plan():
    return pd.DataFrame(
        {
            "井号": ["SYNTHETIC"],
            "完工日期": ["2020/06/01"],
            "石英砂用量": [30.0],
            "压裂方式": ["P"],
        }
    )


def template():
    dates = pd.date_range("2022-02-01", periods=12, freq="MS")
    return pd.DataFrame(
        {"WELL_ID": ["SYNTHETIC"] * 12, "NY": dates.strftime("%Y/%m/%d")}
    )


def test_training_panel_has_twelve_horizons_static_joins_and_no_future_feature_leakage():
    tables = MultiSourceTables(history=history(), layer=layer(), plan=plan())
    shifted = MultiSourceTables(history=history(target_shift=1000.0), layer=layer(), plan=plan())
    first = build_training_samples(tables, config())
    second = build_training_samples(shifted, config())

    assert first["horizon"].tolist() == list(range(1, 13))
    assert first["forecast_step"].tolist() == list(range(1, 13))
    assert len(first) == 12
    assert not first["RCYL"].equals(second["RCYL"])
    feature_columns = [column for column in first if column not in {"RCYL"}]
    pd.testing.assert_frame_equal(first[feature_columns], second[feature_columns])
    assert first["layer__KXD__mean"].iloc[0] == pytest.approx(15.0)
    assert first["plan_first__石英砂用量"].iloc[0] == pytest.approx(30.0)
    assert first["history__RCYL__last"].iloc[0] == pytest.approx(13.0)
    assert first.attrs["training_window_audit"]["included_wells"] == 1
    assert first.attrs["anchor_policy"]["approval_id"] == "B2U-001"
    assert "F" not in str(first.attrs["anchor_policy"])


def test_test_panel_preserves_official_template_keys_and_order():
    tables = MultiSourceTables(
        history=history(include_future=False), layer=layer(), plan=plan(), template=template()
    )
    panel = build_test_samples(tables, config())
    assert len(panel) == 12
    assert panel[["WELL_ID", "NY"]].astype(str).equals(template().astype(str))
    assert panel["horizon"].tolist() == list(range(1, 13))
    assert panel["forecast_step"].tolist() == list(range(1, 13))


def test_full_test_history_is_reduced_to_the_twelve_missing_template_rows():
    test_history = history(include_future=False)
    tables = MultiSourceTables(
        history=test_history,
        layer=layer(),
        plan=plan(),
        template=test_history,
    )
    panel = build_test_samples(tables, config())
    expected = test_history.loc[test_history["RCYL"].isna(), ["WELL_ID", "NY"]].reset_index(drop=True)
    expected["NY"] = pd.to_datetime(expected["NY"]).dt.strftime("%Y/%m/%d")
    assert len(panel) == 12
    assert panel[["WELL_ID", "NY"]].astype(str).equals(expected.astype(str))


def test_template_dates_are_normalized_without_changing_rows_or_order():
    loose_template = template()
    loose_template.loc[0, "NY"] = "2022/2/1"
    tables = MultiSourceTables(
        history=history(include_future=False),
        layer=layer(),
        plan=plan(),
        template=loose_template,
    )
    panel = build_test_samples(tables, config())
    assert panel.loc[0, "NY"] == "2022/02/01"
    assert panel["NY"].tolist()[1:] == template()["NY"].tolist()[1:]


def test_approved_policy_selects_latest_candidate_month_and_rejects_same_month_duplicates():
    local = history()
    local.loc[13, "CSLB"] = "F"
    anchors = identify_last_fracture_anchors(local, config())
    assert anchors["__anchor_time"].iloc[0] == pd.Timestamp("2022-02-01")

    duplicate = local.iloc[[13]].copy()
    duplicate["NY"] = pd.Timestamp("2022-02-15")
    with pytest.raises(DataContractError, match="same month"):
        identify_last_fracture_anchors(pd.concat([local, duplicate], ignore_index=True), config())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("continuous_event_strategy", None),
        ("same_month_tie_strategy", None),
        ("approval_id", "UNAPPROVED"),
        ("first_forecast_month_offset", 0),
    ],
)
def test_approved_policy_fails_closed_when_a_control_is_missing_or_changed(field, value):
    blocked = copy.deepcopy(config())
    blocked["anchors"][field] = value
    with pytest.raises(PolicyBlockedError):
        build_training_samples(MultiSourceTables(history=history(), layer=layer(), plan=plan()), blocked)


def test_unconfirmed_anchor_policy_blocks_before_formal_panel_construction():
    blocked = copy.deepcopy(config())
    blocked["anchors"]["confirmed"] = False
    with pytest.raises(PolicyBlockedError):
        build_training_samples(MultiSourceTables(history=history(), layer=layer(), plan=plan()), blocked)
