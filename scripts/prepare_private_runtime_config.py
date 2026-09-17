from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

from secure_local_audit import read_table, role_of, split_hint


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--candidate-code", action="append", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--experiment-id", default="v1")
    parser.add_argument("--optimized-models", action="store_true")
    parser.add_argument("--top-models-only", action="store_true")
    parser.add_argument(
        "--safe-plus-layer",
        action="store_true",
        help="Reproduce the frozen v7 safe model without first-plan features or calibration.",
    )
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()
    if not args.authorized or os.environ.get("COMPETITION_DATA_ACCESS_ACK") != "I_AM_AUTHORIZED":
        print("PRIVATE_CONFIG_BLOCKED", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[a-z0-9_]+", args.experiment_id):
        print("PRIVATE_CONFIG_INVALID_EXPERIMENT_ID", file=sys.stderr)
        return 2

    raw = Path(args.raw_dir).resolve()
    project = Path(args.project_dir).resolve()
    if not raw.is_dir() or not project.is_dir():
        print("PRIVATE_CONFIG_INVALID_ROOT", file=sys.stderr)
        return 2

    source_paths: dict[str, list[str]] = {
        "train_history": [],
        "test_history": [],
        "layer": [],
        "plan": [],
    }
    suffix_counts: Counter[str] = Counter()
    encoding_counts: Counter[str] = Counter()
    delimiter_counts: Counter[str] = Counter()
    role_columns: dict[str, list[str]] = {}
    for path in sorted(p for p in raw.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".xlsx"}):
        frame, format_info = read_table(path)
        role = role_of(list(map(str, frame.columns)))
        if role in {"history", "layer", "plan"}:
            columns = list(map(str, frame.columns))
            if role in role_columns and role_columns[role] != columns:
                print("PRIVATE_CONFIG_SCHEMA_VARIANT", file=sys.stderr)
                return 2
            role_columns[role] = columns
        relative = path.relative_to(raw).as_posix()
        suffix_counts[path.suffix.lower()] += 1
        if "encoding" in format_info:
            encoding_counts[str(format_info["encoding"])] += 1
            delimiter_counts[str(format_info["delimiter"])] += 1
        if role == "history":
            split = split_hint(path)
            if split not in {"train", "test"}:
                print("PRIVATE_CONFIG_UNCLASSIFIED_HISTORY", file=sys.stderr)
                return 2
            source_paths[f"{split}_history"].append(relative)
        elif role in {"layer", "plan"}:
            source_paths[role].append(relative)

    expected = {"train_history": 88, "test_history": 10, "layer": 1, "plan": 1}
    actual = {key: len(value) for key, value in source_paths.items()}
    if actual != expected:
        print("PRIVATE_CONFIG_ROLE_COUNT_MISMATCH", file=sys.stderr)
        return 2
    if len(encoding_counts) != 1 or len(delimiter_counts) != 1:
        print("PRIVATE_CONFIG_MIXED_CSV_FORMAT", file=sys.stderr)
        return 2

    candidate_path = project / "private_logs" / "anchor_candidates_20260916.json"
    with candidate_path.open("r", encoding="utf-8") as handle:
        candidate_payload = json.load(handle)
    value_by_code = {
        item["code"]: item["raw_value"] for item in candidate_payload.get("candidates", [])
    }
    missing_codes = sorted(set(args.candidate_code) - set(value_by_code))
    if missing_codes:
        print("PRIVATE_CONFIG_CANDIDATE_CODE_MISSING", file=sys.stderr)
        return 2
    eligible_values = [value_by_code[code] for code in args.candidate_code]

    default_path = project / "configs" / "default.yaml"
    with default_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["data"]["input_dir"] = str(raw)
    config["data"]["csv"] = {
        "encoding": next(iter(encoding_counts)),
        "delimiter": next(iter(delimiter_counts)).strip("'"),
    }
    shared_layer = source_paths["layer"]
    shared_plan = source_paths["plan"]
    config["data"]["sources"] = {
        "train": {
            "history": source_paths["train_history"],
            "layer": shared_layer,
            "plan": shared_plan,
            "template": [],
        },
        "test": {
            "history": source_paths["test_history"],
            "layer": shared_layer,
            "plan": shared_plan,
            "template": source_paths["test_history"],
        },
    }
    layer_columns = role_columns["layer"]
    plan_columns = role_columns["plan"]
    if len(layer_columns) != 19 or len(plan_columns) != 12:
        print("PRIVATE_CONFIG_PUBLIC_SCHEMA_SIZE_MISMATCH", file=sys.stderr)
        return 2
    config["features"].update(
        {
            "layer_well_column": layer_columns[0],
            "layer_numeric_columns": [layer_columns[index] for index in (7, 8, 9, 10, 11, 13, 14, 15, 16)],
            "plan_well_column": plan_columns[0],
            "plan_date_column": plan_columns[1],
            "plan_numeric_columns": [plan_columns[index] for index in (4, 5, 6, 7, 8, 9, 11)],
            "plan_categorical_columns": [plan_columns[2], plan_columns[10]],
        }
    )
    config["data"]["audit_output"] = "private_logs/data_audit_runtime.json"
    config["anchors"].update(
        {
            "confirmed": True,
            "rule_version": "data_inferred_latest_record_v1",
            "approval_id": "B2U-001",
            "evidence_level": "data_inferred_user_approved",
            "event_semantics": "independent_monthly_events",
            "eligible_event_values": eligible_values,
            "continuous_event_strategy": "record_level_latest",
            "selection_strategy": "last_candidate_month",
            "same_month_tie_strategy": "error",
            "tie_break_columns": [],
            "first_forecast_month_offset": 1,
            "incomplete_training_window_strategy": "exclude_with_audit",
        }
    )
    if args.safe_plus_layer:
        config["model"].update(
            {
                "feature_policy": "plus_layer_v1",
                "calibration_policy": "none",
                "candidates": ["extra_trees_log_ratio_last"],
                "params": {
                    "extra_trees_log_ratio_last": {
                        "min_samples_leaf": 6,
                        "max_features": 0.75,
                        "n_estimators": 400,
                        "n_jobs": -1,
                    }
                },
            }
        )
    elif args.top_models_only:
        config["model"]["candidates"] = [
            "extra_trees_log",
            "extra_trees_ratio_last",
            "extra_trees_ratio_mean",
            "extra_trees_log_ratio_last",
            "extra_trees_log_ratio_mean",
        ]
    elif args.optimized_models:
        config["model"]["candidates"] = [
            "recent_value",
            "history_mean",
            "decline_curve",
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
        ]
    config["model"]["artifact_path"] = (
        f"models/data_inferred_latest_record_{args.experiment_id}.joblib"
    )
    config["model"]["metrics_output"] = (
        f"private_logs/validation_metrics_data_inferred_{args.experiment_id}.json"
    )

    output = project / "configs" / f"private_data_inferred_{args.experiment_id}.yaml"
    mode = "w" if args.overwrite else "x"
    with output.open(mode, encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, allow_unicode=True, sort_keys=False)
    print(
        "PRIVATE_CONFIG_OK "
        f"train_history={actual['train_history']} test_history={actual['test_history']} "
        f"candidate_count={len(eligible_values)} file_types={dict(sorted(suffix_counts.items()))} "
        f"csv_encoding={next(iter(encoding_counts))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
