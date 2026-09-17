from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .exceptions import DataContractError
from .schema import SchemaContract


def materialize_feature_frame(frame: pd.DataFrame, contract: SchemaContract) -> pd.DataFrame:
    missing = sorted(set(contract.feature_columns) - set(frame.columns))
    if missing:
        raise DataContractError(f"Feature columns are missing: {', '.join(missing)}")
    features = frame.loc[:, list(contract.feature_columns)].copy()
    for column in contract.datetime_columns:
        if column not in features.columns:
            continue
        parsed = pd.to_datetime(features[column], errors="coerce", utc=True)
        # Days since Unix epoch, with NaT left as NaN for fold-local imputation.
        features[column] = parsed.astype("int64").where(parsed.notna(), np.nan) / 86_400_000_000_000
    return features


def build_preprocessor(features: pd.DataFrame, contract: SchemaContract) -> ColumnTransformer:
    categorical = [column for column in contract.categorical_columns if column in features.columns]
    numeric = [column for column in contract.numeric_columns if column in features.columns]
    numeric.extend(column for column in contract.datetime_columns if column in features.columns and column not in numeric)
    classified = set(categorical) | set(numeric)
    for column in features.columns:
        if column in classified:
            continue
        if pd.api.types.is_numeric_dtype(features[column]):
            numeric.append(column)
        else:
            categorical.append(column)

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    transformers = []
    if numeric:
        transformers.append(("numeric", numeric_pipeline, numeric))
    if categorical:
        transformers.append(("categorical", categorical_pipeline, categorical))
    if not transformers:
        raise DataContractError("No numeric or categorical features are available.")
    return ColumnTransformer(transformers=transformers, remainder="drop", verbose_feature_names_out=True)
