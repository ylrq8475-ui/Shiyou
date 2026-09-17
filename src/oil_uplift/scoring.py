from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any

import numpy as np
import pandas as pd

from .exceptions import ConfigurationError, DataContractError, PolicyBlockedError


@dataclass(frozen=True)
class ScoreResult:
    total: float
    components: dict[str, float]
    direction: str
    formula_version: str


def official_twelve_month_score(
    frame: pd.DataFrame,
    *,
    truth_column: str,
    prediction_column: str,
    well_column: str = "WELL_ID",
    horizon_column: str = "horizon",
    epsilon: float = 1e-6,
) -> ScoreResult:
    """Exact official score: weighted monthly error, then equal mean over wells.

    The monthly error intentionally has no leading factor of two.
    """
    required = {truth_column, prediction_column, well_column, horizon_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DataContractError(f"Official scoring columns are missing: {', '.join(missing)}")
    if epsilon != 1e-6:
        raise ConfigurationError("The official epsilon is fixed at 1e-6.")
    truth = pd.to_numeric(frame[truth_column], errors="coerce")
    prediction = pd.to_numeric(frame[prediction_column], errors="coerce")
    horizon = pd.to_numeric(frame[horizon_column], errors="coerce")
    if truth.isna().any() or prediction.isna().any() or horizon.isna().any():
        raise DataContractError("Official scoring inputs must be numeric and non-missing.")
    if not np.isfinite(truth).all() or not np.isfinite(prediction).all():
        raise DataContractError("Official scoring values must be finite.")

    work = frame.loc[:, [well_column]].copy()
    work["truth"] = truth.to_numpy(dtype=float)
    work["prediction"] = prediction.to_numpy(dtype=float)
    work["horizon"] = horizon.to_numpy(dtype=int)
    expected = list(range(1, 13))
    well_scores: dict[str, float] = {}
    for well, group in work.groupby(well_column, sort=False):
        ordered = group.sort_values("horizon", kind="mergesort")
        if ordered["horizon"].tolist() != expected:
            raise DataContractError("Each well must contain each horizon from 1 through 12 exactly once.")
        weights = np.power(0.5, ordered["horizon"].to_numpy(dtype=float))
        numerator = np.abs(ordered["prediction"].to_numpy() - ordered["truth"].to_numpy())
        denominator = (
            np.abs(ordered["prediction"].to_numpy())
            + np.abs(ordered["truth"].to_numpy())
            + epsilon
        )
        smape = float(np.sum(weights * numerator / denominator))
        well_scores[str(well)] = 100.0 * (1.0 - smape)
    if not well_scores:
        raise DataContractError("Official scoring requires at least one well.")
    return ScoreResult(
        total=float(np.mean(list(well_scores.values()))),
        components=well_scores,
        direction="maximize",
        formula_version="official_12m_smape_v1",
    )


def _arrays(y_true: Any, y_pred: Any) -> tuple[np.ndarray, np.ndarray]:
    truth = np.asarray(y_true, dtype=float).reshape(-1)
    pred = np.asarray(y_pred, dtype=float).reshape(-1)
    if truth.shape != pred.shape or truth.size == 0:
        raise DataContractError("Truth and prediction must be non-empty one-dimensional arrays of equal length.")
    if not np.isfinite(truth).all() or not np.isfinite(pred).all():
        raise DataContractError("Truth and prediction must contain only finite values.")
    return truth, pred


def _weights(values: Any, size: int) -> np.ndarray:
    if values is None:
        return np.ones(size, dtype=float)
    weights = np.asarray(values, dtype=float).reshape(-1)
    if weights.size != size or not np.isfinite(weights).all():
        raise DataContractError("Sample weights must be finite and match the sample count.")
    if (weights < 0).any() or float(weights.sum()) <= 0:
        raise DataContractError("Sample weights must be non-negative with a positive sum.")
    return weights


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average(values, weights=weights))


def metric_value(
    metric: str,
    y_true: Any,
    y_pred: Any,
    *,
    sample_weight: Any = None,
    zero_division: str = "error",
    epsilon: float = 1e-8,
) -> float:
    truth, pred = _arrays(y_true, y_pred)
    weights = _weights(sample_weight, truth.size)
    error = pred - truth
    name = metric.casefold()
    if name == "mae":
        return _weighted_mean(np.abs(error), weights)
    if name == "mse":
        return _weighted_mean(np.square(error), weights)
    if name == "rmse":
        return sqrt(_weighted_mean(np.square(error), weights))
    if name in {"mape", "smape"}:
        denominator = np.abs(truth) if name == "mape" else (np.abs(truth) + np.abs(pred)) / 2.0
        zero = denominator == 0
        if zero.any():
            if zero_division == "error":
                raise DataContractError(f"{name.upper()} encountered a zero denominator.")
            if zero_division == "epsilon":
                denominator = np.where(zero, epsilon, denominator)
            elif zero_division == "ignore":
                keep = ~zero
                if not keep.any():
                    raise DataContractError(f"{name.upper()} has no valid denominators.")
                denominator, error, weights = denominator[keep], error[keep], weights[keep]
            else:
                raise ConfigurationError("scoring.zero_division must be error, epsilon, or ignore.")
        return 100.0 * _weighted_mean(np.abs(error) / denominator, weights)
    if name == "r2":
        mean = _weighted_mean(truth, weights)
        denominator = float(np.sum(weights * np.square(truth - mean)))
        if denominator == 0:
            raise DataContractError("R2 is undefined for a constant target.")
        numerator = float(np.sum(weights * np.square(error)))
        return 1.0 - numerator / denominator
    raise ConfigurationError(f"Unsupported scoring metric: {metric}")


class OfficialWeightedScorer:
    """Configuration-exact scorer that refuses to run before confirmation."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        scoring = config.get("scoring", {})
        if scoring.get("confirmed") is not True:
            raise PolicyBlockedError("The official scoring formula is not confirmed.")
        if not scoring.get("formula_version"):
            raise PolicyBlockedError("A confirmed scoring formula requires formula_version.")
        if scoring.get("direction") not in {"minimize", "maximize"}:
            raise ConfigurationError("scoring.direction must be minimize or maximize.")
        if scoring.get("aggregation") not in {"weighted_mean", "weighted_sum"}:
            raise ConfigurationError("scoring.aggregation must be weighted_mean or weighted_sum.")
        components = scoring.get("components", [])
        if not components:
            raise PolicyBlockedError("The confirmed scoring formula has no components.")
        for component in components:
            if not component.get("metric") or component.get("coefficient") is None:
                raise ConfigurationError("Every scoring component needs metric and coefficient.")
            if float(component["coefficient"]) < 0:
                raise ConfigurationError("Scoring coefficients must be non-negative.")
        if sum(float(item["coefficient"]) for item in components) <= 0:
            raise ConfigurationError("Scoring coefficients must have a positive sum.")

    def score(
        self,
        y_true: Any,
        y_pred: Any,
        *,
        context: pd.DataFrame | None = None,
    ) -> ScoreResult:
        scoring = self.config["scoring"]
        parts: dict[str, float] = {}
        weighted_total = 0.0
        coefficient_total = 0.0
        for number, component in enumerate(scoring["components"], start=1):
            column = component.get("sample_weight_column")
            sample_weight = None
            if column:
                if context is None or column not in context.columns:
                    raise DataContractError(f"Scoring weight column is unavailable: {column}")
                sample_weight = context[column]
            value = metric_value(
                component["metric"],
                y_true,
                y_pred,
                sample_weight=sample_weight,
                zero_division=scoring.get("zero_division", "error"),
                epsilon=float(scoring.get("epsilon", 1e-8)),
            )
            key = component.get("name") or f"{component['metric']}_{number}"
            if key in parts:
                raise ConfigurationError(f"Duplicate scoring component name: {key}")
            parts[key] = value
            coefficient = float(component["coefficient"])
            weighted_total += coefficient * value
            coefficient_total += coefficient
        if scoring["aggregation"] == "weighted_mean":
            weighted_total /= coefficient_total
        return ScoreResult(
            total=float(weighted_total),
            components=parts,
            direction=scoring["direction"],
            formula_version=str(scoring["formula_version"]),
        )
