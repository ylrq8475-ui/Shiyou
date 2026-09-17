from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)

from .exceptions import ConfigurationError


MODEL_NAMES = (
    "median",
    "hist_gradient_boosting",
    "random_forest",
    "extra_trees",
    "gradient_boosting",
    "hist_gradient_boosting_poisson",
    "extra_trees_log",
)


class LogTargetRegressor(RegressorMixin, BaseEstimator):
    def __init__(self, estimator):
        self.estimator = estimator

    def fit(self, x, y, sample_weight=None):
        values = np.asarray(y, dtype=float)
        if (values < 0).any() or not np.isfinite(values).all():
            raise ValueError("LogTargetRegressor requires finite non-negative targets.")
        self.estimator_ = clone(self.estimator)
        kwargs = {} if sample_weight is None else {"sample_weight": sample_weight}
        self.estimator_.fit(x, np.log1p(values), **kwargs)
        return self

    def predict(self, x):
        return np.expm1(self.estimator_.predict(x))


def build_model(name: str, random_seed: int, params: dict[str, Any] | None = None):
    params = dict(params or {})
    if name == "median":
        return DummyRegressor(strategy="median", **params)
    if name == "hist_gradient_boosting":
        defaults = {"learning_rate": 0.05, "max_iter": 300, "l2_regularization": 0.1}
        defaults.update(params)
        return HistGradientBoostingRegressor(random_state=random_seed, **defaults)
    if name == "hist_gradient_boosting_poisson":
        defaults = {
            "loss": "poisson",
            "learning_rate": 0.05,
            "max_iter": 300,
            "l2_regularization": 0.1,
        }
        defaults.update(params)
        return HistGradientBoostingRegressor(random_state=random_seed, **defaults)
    if name == "random_forest":
        defaults = {"n_estimators": 400, "min_samples_leaf": 2, "n_jobs": -1}
        defaults.update(params)
        return RandomForestRegressor(random_state=random_seed, **defaults)
    if name == "extra_trees":
        defaults = {"n_estimators": 400, "min_samples_leaf": 2, "n_jobs": -1}
        defaults.update(params)
        return ExtraTreesRegressor(random_state=random_seed, **defaults)
    if name == "extra_trees_log":
        defaults = {"n_estimators": 400, "min_samples_leaf": 2, "n_jobs": -1}
        defaults.update(params)
        return LogTargetRegressor(ExtraTreesRegressor(random_state=random_seed, **defaults))
    if name == "gradient_boosting":
        defaults = {"n_estimators": 300, "learning_rate": 0.03, "max_depth": 3, "loss": "huber"}
        defaults.update(params)
        return GradientBoostingRegressor(random_state=random_seed, **defaults)
    raise ConfigurationError(f"Unknown model candidate: {name}. Available: {', '.join(MODEL_NAMES)}")
