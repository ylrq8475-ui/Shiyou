import sys
from pathlib import Path

import pandas as pd
import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_uplift.exceptions import DataContractError
from oil_uplift.scoring import official_twelve_month_score


def make_well(well_id: str, truth: float, prediction: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "WELL_ID": [well_id] * 12,
            "horizon": range(1, 13),
            "actual": [truth] * 12,
            "prediction": [prediction] * 12,
        }
    )


def score(frame: pd.DataFrame):
    return official_twelve_month_score(
        frame,
        truth_column="actual",
        prediction_column="prediction",
    )


def test_perfect_predictions_score_100():
    frame = pd.concat([make_well("A", 10.0, 10.0), make_well("B", 3.0, 3.0)])
    result = score(frame)
    assert result.total == pytest.approx(100.0)
    assert result.components == {"A": 100.0, "B": 100.0}


def test_all_zero_truth_and_prediction_score_100():
    assert score(make_well("A", 0.0, 0.0)).total == pytest.approx(100.0)


def test_zero_truth_one_prediction_uses_exact_month_weights_without_factor_two():
    result = score(make_well("A", 0.0, 1.0))
    weight_sum = sum(2.0 ** (-t) for t in range(1, 13))
    expected = 100.0 * (1.0 - weight_sum / (1.0 + 1e-6))
    assert result.total == pytest.approx(expected)


def test_wells_are_averaged_equally_not_by_row_or_volume():
    perfect = make_well("small", 1.0, 1.0)
    imperfect = make_well("large", 0.0, 1.0)
    combined = score(pd.concat([perfect, imperfect], ignore_index=True))
    separate_mean = (score(perfect).total + score(imperfect).total) / 2.0
    assert combined.total == pytest.approx(separate_mean)


def test_zero_and_nonzero_months_follow_unormalized_weights():
    frame = make_well("A", 0.0, 0.0)
    frame.loc[0, ["actual", "prediction"]] = [0.0, 1.0]
    frame.loc[1, ["actual", "prediction"]] = [2.0, 1.0]
    expected_error = 0.5 * (1.0 / (1.0 + 1e-6)) + 0.25 * (1.0 / (3.0 + 1e-6))
    assert score(frame).total == pytest.approx(100.0 * (1.0 - expected_error))


def test_negative_predictions_are_not_silently_clipped_by_scorer_but_model_clip_improves_score():
    raw = make_well("A", 1.0, 1.0)
    raw.loc[0, "prediction"] = -1.0
    clipped = raw.copy()
    clipped["prediction"] = clipped["prediction"].clip(lower=0.0)
    assert score(clipped).total > score(raw).total


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_nan_and_infinity_are_rejected(bad):
    frame = make_well("A", 1.0, 1.0)
    frame.loc[0, "prediction"] = bad
    with pytest.raises(DataContractError):
        score(frame)


@pytest.mark.parametrize("kind", ["missing", "duplicate"])
def test_missing_or_duplicate_horizon_is_rejected(kind):
    frame = make_well("A", 1.0, 1.0)
    if kind == "missing":
        frame = frame.iloc[:-1].copy()
    else:
        frame.loc[11, "horizon"] = 11
    with pytest.raises(DataContractError, match="horizon"):
        score(frame)
