from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import config_fingerprint
from .exceptions import ConfigurationError, DataContractError
from .multistep import build_test_samples, load_multisource_split
from .submission import validate_submission_frame
from .training import baseline_predict, load_model_artifact, predict_pipeline_output


def predict_from_panel(
    panel: pd.DataFrame,
    artifact: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    if artifact.get("config_fingerprint") != config_fingerprint(config):
        raise ConfigurationError("The model artifact and current configuration fingerprints differ.")
    panel_policy = panel.attrs.get("anchor_policy")
    if artifact.get("anchor_policy") != panel_policy:
        raise ConfigurationError("The model artifact and test panel use different anchor policies.")
    required = {"WELL_ID", "NY", "horizon"}
    missing = sorted(required - set(panel.columns))
    if missing:
        raise DataContractError("Test panel columns are missing: " + ", ".join(missing))
    feature_columns = list(artifact.get("feature_columns", []))
    missing_features = sorted(set(feature_columns) - set(panel.columns))
    if missing_features:
        raise DataContractError("Test panel is missing trained features: " + ", ".join(missing_features))
    if artifact.get("deterministic_baseline"):
        prediction = baseline_predict(panel, artifact["model_name"])
    else:
        prediction = predict_pipeline_output(
            artifact["pipeline"],
            artifact["model_name"],
            panel.loc[:, feature_columns],
            panel,
        )
    prediction = np.asarray(prediction, dtype=float) * float(artifact["prediction_scale"])
    if prediction.shape != (len(panel),) or not np.isfinite(prediction).all():
        raise DataContractError("The model produced invalid predictions.")
    prediction = np.clip(prediction, 0.0, None)
    output = pd.DataFrame(
        {
            "WELL_ID": panel["WELL_ID"].astype(str).to_numpy(),
            "NY": panel["NY"].astype(str).to_numpy(),
            "RCYL": np.round(prediction, 6),
        }
    )
    validate_submission_frame(output, config, reference=panel[["WELL_ID", "NY"]])
    return output


def run_inference(
    config: dict[str, Any],
    model_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    artifact = load_model_artifact(model_path)
    tables = load_multisource_split(config, "test")
    panel = build_test_samples(tables, config)
    output = predict_from_panel(panel, artifact, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(
        output_path,
        index=False,
        encoding=config.get("submission", {}).get("encoding", "utf-8-sig"),
        float_format="%.6f",
    )
    return {"rows": len(output), "wells": int(output["WELL_ID"].nunique()), "model": artifact["model_name"]}
