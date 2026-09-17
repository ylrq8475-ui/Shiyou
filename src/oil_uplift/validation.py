from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import pandas as pd

from .exceptions import ConfigurationError, DataContractError


@dataclass(frozen=True)
class FoldBoundary:
    fold: int
    train_end: str
    validation_start: str
    validation_end: str
    train_rows: int
    validation_rows: int
    purged_train_rows: int


class GroupedTemporalSplit:
    """Expanding-window time split with an optional group-overlap purge."""

    def __init__(
        self,
        n_splits: int = 5,
        time_gap_rows: int = 0,
        purge_group_overlap: bool = True,
        min_train_rows: int = 1,
        min_validation_rows: int = 1,
    ) -> None:
        if n_splits < 1:
            raise ConfigurationError("validation.n_splits must be at least 1.")
        if time_gap_rows < 0:
            raise ConfigurationError("validation.time_gap_rows cannot be negative.")
        self.n_splits = n_splits
        self.time_gap_rows = time_gap_rows
        self.purge_group_overlap = purge_group_overlap
        self.min_train_rows = min_train_rows
        self.min_validation_rows = min_validation_rows
        self.boundaries_: list[FoldBoundary] = []

    def split(self, times, groups) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        parsed = pd.to_datetime(pd.Series(times).reset_index(drop=True), errors="coerce", utc=True)
        group_series = pd.Series(groups).reset_index(drop=True)
        if len(parsed) != len(group_series) or len(parsed) == 0:
            raise DataContractError("Times and groups must be non-empty and have equal length.")
        if parsed.isna().any() or group_series.isna().any():
            raise DataContractError("Times and groups cannot contain missing values.")
        unique_times = np.array(sorted(parsed.unique()))
        if len(unique_times) < self.n_splits + 1:
            raise DataContractError("Not enough unique timestamps for the requested temporal folds.")
        blocks = np.array_split(unique_times, self.n_splits + 1)
        self.boundaries_ = []
        row_positions = np.arange(len(parsed))

        for fold in range(1, self.n_splits + 1):
            validation_times = blocks[fold]
            validation_mask = parsed.isin(validation_times).to_numpy()
            train_mask = (parsed < pd.Timestamp(validation_times[0])).to_numpy()
            train_index = row_positions[train_mask]
            validation_index = row_positions[validation_mask]
            if self.time_gap_rows:
                train_index = train_index[np.argsort(parsed.iloc[train_index].to_numpy())]
                train_index = train_index[: max(0, len(train_index) - self.time_gap_rows)]

            before_purge = len(train_index)
            if self.purge_group_overlap:
                validation_groups = set(group_series.iloc[validation_index].tolist())
                keep = ~group_series.iloc[train_index].isin(validation_groups).to_numpy()
                train_index = train_index[keep]
            purged = before_purge - len(train_index)
            if len(train_index) < self.min_train_rows:
                raise DataContractError(
                    f"Fold {fold} has {len(train_index)} training rows after gap/purge; "
                    f"minimum is {self.min_train_rows}."
                )
            if len(validation_index) < self.min_validation_rows:
                raise DataContractError(
                    f"Fold {fold} has {len(validation_index)} validation rows; "
                    f"minimum is {self.min_validation_rows}."
                )
            train_times = parsed.iloc[train_index]
            valid_times = parsed.iloc[validation_index]
            if train_times.max() >= valid_times.min():
                raise DataContractError("Temporal split invariant failed: training is not strictly earlier.")
            if self.purge_group_overlap:
                overlap = set(group_series.iloc[train_index]) & set(group_series.iloc[validation_index])
                if overlap:
                    raise DataContractError("Group purge invariant failed.")
            self.boundaries_.append(
                FoldBoundary(
                    fold=fold,
                    train_end=train_times.max().isoformat(),
                    validation_start=valid_times.min().isoformat(),
                    validation_end=valid_times.max().isoformat(),
                    train_rows=len(train_index),
                    validation_rows=len(validation_index),
                    purged_train_rows=purged,
                )
            )
            yield train_index, validation_index


def splitter_from_config(config: dict) -> GroupedTemporalSplit:
    values = config.get("validation", {})
    return GroupedTemporalSplit(
        n_splits=int(values.get("n_splits", 5)),
        time_gap_rows=int(values.get("time_gap_rows", 0)),
        purge_group_overlap=bool(values.get("purge_group_overlap", True)),
        min_train_rows=int(values.get("min_train_rows", 1)),
        min_validation_rows=int(values.get("min_validation_rows", 1)),
    )
