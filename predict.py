from __future__ import annotations

import argparse
import copy
import sys
import tempfile
from pathlib import Path
from typing import Sequence

import pandas as pd

from oil_uplift.config import load_config, resolve_project_path
from oil_uplift.exceptions import ConfigurationError, OilUpliftError
from oil_uplift.inference import run_inference
from oil_uplift.multistep import require_confirmed_anchor_policy
from oil_uplift.submission import validate_submission_frame, well_csv_filename
from oil_uplift.training import run_training


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Predict 12 monthly RCYL values for each well")
    parser.add_argument("--data_dir", required=True, help="Authorized local competition data directory")
    parser.add_argument("--output", required=True, help="Output directory or combined CSV file")
    parser.add_argument("--mode", choices=("retrain", "load"), default="load")
    parser.add_argument("--model", default=None, help="Local model artifact path")
    parser.add_argument("--config", default=str(root / "configs" / "default.yaml"))
    return parser


def _write_per_well(combined_csv: Path, output_dir: Path, config: dict) -> tuple[int, int]:
    frame = pd.read_csv(
        combined_csv,
        encoding=config.get("submission", {}).get("encoding", "utf-8-sig"),
        dtype={"WELL_ID": "string", "NY": "string"},
    ).astype({"WELL_ID": object, "NY": object})
    validate_submission_frame(frame, config, reference=frame[["WELL_ID", "NY"]])
    output_dir.mkdir(parents=True, exist_ok=True)
    names: dict[str, str] = {}
    for well_id, group in frame.groupby("WELL_ID", sort=False):
        filename = well_csv_filename(well_id)
        folded = filename.casefold()
        if folded in names and names[folded] != well_id:
            raise ConfigurationError("Two WELL_ID values map to the same output filename.")
        names[folded] = well_id
        group.to_csv(
            output_dir / filename,
            index=False,
            encoding=config.get("submission", {}).get("encoding", "utf-8-sig"),
            float_format="%.6f",
        )
    return int(frame["WELL_ID"].nunique()), len(frame)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = copy.deepcopy(load_config(args.config))
        # Fail closed before checking or reading --data_dir.
        require_confirmed_anchor_policy(config)
        config.setdefault("data", {})["input_dir"] = str(Path(args.data_dir).expanduser().resolve())

        if args.mode == "load" and not args.model:
            raise ConfigurationError("--mode load requires --model with a local artifact path.")
        if args.model:
            model_path = Path(args.model).expanduser().resolve()
            config.setdefault("model", {})["artifact_path"] = str(model_path)
        else:
            model_path = resolve_project_path(
                config, config.get("model", {}).get("artifact_path", "artifacts/model.joblib")
            )
        if args.mode == "retrain":
            run_training(config)

        output = Path(args.output).expanduser().resolve()
        if output.suffix.lower() == ".csv":
            result = run_inference(config, model_path, output)
            wells, rows = result["wells"], result["rows"]
        elif output.suffix:
            raise ConfigurationError("--output must be a directory or a .csv file.")
        else:
            with tempfile.TemporaryDirectory(prefix="oil_uplift_") as temporary:
                combined = Path(temporary) / "combined.csv"
                run_inference(config, model_path, combined)
                wells, rows = _write_per_well(combined, output, config)
        print(f"Prediction complete: {wells} wells, {rows} rows.")
        return 0
    except OilUpliftError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
