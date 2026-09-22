"""Train and reproduce the single authorized A2B-013 safe-boundary submission.

This entry point never uploads. Platform upload is a separate, one-attempt step
after external local gates have passed and both ZIP hashes have been locked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import zipfile
from pathlib import Path
from typing import Any


def source_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    for candidate in (script_dir, script_dir.parent):
        if (candidate / "src/oil_uplift/a2b013_safe.py").is_file():
            return candidate
    raise RuntimeError("A2B-013 packaged source tree is incomplete.")


ROOT = source_root()
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from oil_uplift.a2b013_safe import (  # noqa: E402
    build_safe_data,
    evaluate_fixed_oof,
    infer_from_artifact,
    result_frame,
    safe_config,
    train_final,
    write_result_zip,
)
from oil_uplift.config import load_config  # noqa: E402
from oil_uplift.exceptions import DataContractError  # noqa: E402


PLAN_SHA256 = "e3a7759dcb00bc5acde6ba8ef536227fc69bbc2d9dd700d13aa0823a5fd867cc"
PRIVATE_CONFIG_SHA256 = "89e60c301b1d553b1c7dab8e2f87d1d9a47b600abe4322f2e9895717201c0c72"
LOCKED_MODEL_NAME = "extra_trees_log_ratio_last"
CODE_FILES = (
    ("scripts/run_a2b013_safe_submission.py", "run_a2b013_safe_submission.py"),
    ("src/oil_uplift/__init__.py", "src/oil_uplift/__init__.py"),
    ("src/oil_uplift/a2b013_safe.py", "src/oil_uplift/a2b013_safe.py"),
    ("src/oil_uplift/config.py", "src/oil_uplift/config.py"),
    ("src/oil_uplift/exceptions.py", "src/oil_uplift/exceptions.py"),
    ("src/oil_uplift/io.py", "src/oil_uplift/io.py"),
    ("src/oil_uplift/models.py", "src/oil_uplift/models.py"),
    ("src/oil_uplift/multistep.py", "src/oil_uplift/multistep.py"),
    ("src/oil_uplift/scoring.py", "src/oil_uplift/scoring.py"),
    ("src/oil_uplift/submission.py", "src/oil_uplift/submission.py"),
    ("src/oil_uplift/training.py", "src/oil_uplift/training.py"),
    ("requirements.txt", "requirements.txt"),
    ("requirements-lock.txt", "requirements-lock.txt"),
    ("deliverables/a2b013_second_submission/README.md", "README.md"),
    ("experiments/a2b013/EXPERIMENT_PLAN.yaml", "experiments/a2b013/EXPERIMENT_PLAN.yaml"),
    ("experiments/a2b013/PLAN_LOCK_SHA256.txt", "experiments/a2b013/PLAN_LOCK_SHA256.txt"),
    ("tests/test_a2b013_safe_submission.py", "tests/test_a2b013_safe_submission.py"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def verify_plan_and_config(config_path: Path) -> None:
    plan = ROOT / "experiments/a2b013/EXPERIMENT_PLAN.yaml"
    lock = ROOT / "experiments/a2b013/PLAN_LOCK_SHA256.txt"
    if not plan.is_file() or not lock.is_file() or sha256(plan) != PLAN_SHA256:
        raise DataContractError("The preregistered A2B-013 plan changed.")
    expected_line = f"experiments/a2b013/EXPERIMENT_PLAN.yaml|{plan.stat().st_size}|{PLAN_SHA256}"
    if expected_line not in lock.read_text(encoding="utf-8"):
        raise DataContractError("The A2B-013 plan lock changed.")
    if not config_path.is_file() or sha256(config_path) != PRIVATE_CONFIG_SHA256:
        raise DataContractError("The private source configuration differs from the frozen input.")


def verify_frozen_predecessors() -> dict[str, int]:
    ledger = ROOT / "experiments/a2b013/FROZEN_BEFORE_AFTER_SHA256.txt"
    if not ledger.is_file():
        raise DataContractError("The predecessor freeze ledger is missing.")
    entries = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        parts = line.split("|")
        if len(parts) == 3 and len(parts[2]) == 64 and parts[1].isdigit():
            entries.append((parts[0], int(parts[1]), parts[2]))
    if len(entries) < 11 or len(entries) % 11:
        raise DataContractError("The predecessor freeze ledger has an invalid size.")
    failures = 0
    for relative, length, digest in entries:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size != length or sha256(path) != digest:
            failures += 1
    if failures:
        raise DataContractError("A frozen predecessor file changed.")
    return {"checked_entries": len(entries), "mismatches": 0}


def _fixed_zip_entry(name: str) -> zipfile.ZipInfo:
    entry = zipfile.ZipInfo(name, date_time=(2026, 9, 22, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.external_attr = 0o644 << 16
    return entry


def create_code_zip(output_path: Path) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_hashes: dict[str, str] = {}
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source_relative, archive_name in CODE_FILES:
            source = ROOT / source_relative
            if not source.is_file():
                raise DataContractError("A required code-package source file is missing.")
            body = source.read_bytes()
            file_hashes[archive_name] = hashlib.sha256(body).hexdigest()
            archive.writestr(_fixed_zip_entry(archive_name), body,
                             compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    if output_path.stat().st_size >= 5 * 1024**3:
        raise DataContractError("The code package exceeds the 5 GB limit.")
    with zipfile.ZipFile(output_path) as archive:
        actual = archive.namelist()
        expected = [item[1] for item in CODE_FILES]
        if actual != expected:
            raise DataContractError("The code package member list differs from the allowlist.")
        if any(hashlib.sha256(archive.read(name)).hexdigest() != file_hashes[name] for name in actual):
            raise DataContractError("A code package member failed extracted-hash verification.")
        if any(name.startswith(("data/", "private_logs/", "models/", "submissions/"))
               or name.endswith((".csv", ".xlsx", ".joblib", ".zip")) for name in actual):
            raise DataContractError("The code package contains a forbidden artifact type.")
    return {"member_count": len(file_hashes), "byte_length": output_path.stat().st_size,
            "sha256": sha256(output_path), "source_sha256": file_hashes}


def _metrics_payload(config_path: Path, input_dir: str | None, artifact_path: Path,
                     result_path: Path) -> tuple[dict[str, Any], Any]:
    started = time.perf_counter()
    original = load_config(config_path)
    config = safe_config(original, input_dir=input_dir)
    data = build_safe_data(config)
    validation = evaluate_fixed_oof(data, config)
    fitted = train_final(data, config, artifact_path, PRIVATE_CONFIG_SHA256, PLAN_SHA256)
    loaded_prediction = infer_from_artifact(artifact_path, data, PRIVATE_CONFIG_SHA256, PLAN_SHA256)
    repeated_prediction = infer_from_artifact(artifact_path, data, PRIVATE_CONFIG_SHA256, PLAN_SHA256)
    if not np.array_equal(fitted["test_prediction"], loaded_prediction) or not np.array_equal(
        loaded_prediction, repeated_prediction
    ):
        raise DataContractError("Repeated inference changed predictions.")
    submission = result_frame(data, loaded_prediction)
    output_check = write_result_zip(submission, data.reference, result_path)
    metrics = {
        "request_id": "A2B-013",
        "version": "END_T1_CM1_NL",
        "status": "local_model_and_result_built_not_platform_uploaded",
        "source_config_sha256": sha256(config_path),
        "plan_sha256": PLAN_SHA256,
        "model_name": LOCKED_MODEL_NAME,
        "model_params": {"n_estimators": 400, "min_samples_leaf": 6,
                          "max_features": 0.75, "n_jobs": -1, "random_seed": 20260916},
        "feature_policy": "history_pre_anchor_only_325_no_layer_no_plan",
        "data_audit": data.audit,
        "validation": validation,
        "result_contract": output_check,
        "final_model_sha256": sha256(artifact_path),
        "result_zip_sha256": sha256(result_path),
        "repeat_inference_exact": True,
        "row_level_oof_persisted": False,
        "no_score_based_model_adjustment": True,
        "runtime_seconds": round(time.perf_counter() - started, 3),
    }
    return metrics, data


def run_build(config_path: Path, input_dir: str | None, project_dir: Path) -> None:
    if project_dir.resolve() != ROOT.resolve():
        raise DataContractError("Build mode must run inside the approved B project root.")
    verify_plan_and_config(config_path)
    frozen = verify_frozen_predecessors()
    output = ROOT / "deliverables/a2b013_second_submission"
    model = output / "a2b013_safe_model.joblib"
    result = output / "result.zip"
    code = output / "submission_code.zip"
    metrics, _ = _metrics_payload(config_path, input_dir, model, result)
    metrics["code_package"] = create_code_zip(code)
    metrics["frozen_predecessors"] = verify_frozen_predecessors()
    if metrics["frozen_predecessors"]["mismatches"] or frozen["mismatches"]:
        raise DataContractError("A frozen first-round file changed during A2B-013.")
    _write_json(ROOT / "private_logs/a2b013_validation_metrics.json", metrics)
    print("A2B013_LOCAL_BUILD_OK", "train_wells=", metrics["data_audit"]["train"]["included_wells"],
          "test_wells=", metrics["data_audit"]["test"]["test_wells"],
          "features=", metrics["data_audit"]["feature_count"],
          "oof=", round(metrics["validation"]["official_oof"], 6))


def run_reproduce(config_path: Path, input_dir: str | None, output_dir: Path) -> None:
    verify_plan_and_config(config_path)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics, _ = _metrics_payload(config_path, input_dir, output_dir / "a2b013_safe_model.joblib",
                                  output_dir / "result.zip")
    _write_json(output_dir / "aggregate_validation.json", metrics)
    print("A2B013_REPRODUCE_OK", "result_sha256=", metrics["result_zip_sha256"],
          "oof=", round(metrics["validation"]["official_oof"], 6))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=["build", "reproduce"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--input-dir")
    parser.add_argument("--project-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()
    if not args.authorized or os.environ.get("COMPETITION_DATA_ACCESS_ACK") != "I_AM_AUTHORIZED":
        print("A2B013_DATA_ACCESS_BLOCKED", file=sys.stderr)
        return 2
    try:
        if args.mode == "build":
            if not args.project_dir or args.output_dir:
                raise DataContractError("Build mode requires only --project-dir as its output root.")
            run_build(Path(args.config).resolve(), args.input_dir, Path(args.project_dir))
        else:
            if not args.output_dir or args.project_dir:
                raise DataContractError("Reproduce mode requires only --output-dir as its output root.")
            run_reproduce(Path(args.config).resolve(), args.input_dir, Path(args.output_dir))
    except Exception as exc:
        # Deliberately suppress messages from filesystem/data libraries: they
        # can contain raw paths, well identifiers or sample values.
        if isinstance(exc, DataContractError):
            print(f"A2B013_FAILED DataContractError: {exc}", file=sys.stderr)
        else:
            print(f"A2B013_FAILED {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
