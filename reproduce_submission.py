from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from oil_uplift.config import load_config
from oil_uplift.packaging import create_result_zip


CANDIDATE_CODES = ("CSLB_012", "CSLB_032")
EXPERIMENT_ID = "trial_safe_plus_layer"


def _run(arguments: list[str], *, root: Path, environment: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, *arguments],
        cwd=root,
        env=environment,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild the approved safe model and create a root-flat result.zip."
    )
    parser.add_argument("--data-dir", required=True, help="Authorized official competition data directory")
    parser.add_argument("--output-dir", default="reproduction_output")
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()

    if not args.authorized:
        print("REPRODUCTION_BLOCKED: pass --authorized only in an approved local environment.", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent
    data_dir = Path(args.data_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = (root / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    environment = dict(os.environ)
    environment["COMPETITION_DATA_ACCESS_ACK"] = "I_AM_AUTHORIZED"

    _run(
        [
            "scripts/analyze_anchor_candidates.py",
            "--raw-dir",
            str(data_dir),
            "--project-dir",
            str(root),
            "--authorized",
        ],
        root=root,
        environment=environment,
    )

    prepare = [
        "scripts/prepare_private_runtime_config.py",
        "--raw-dir",
        str(data_dir),
        "--project-dir",
        str(root),
        "--experiment-id",
        EXPERIMENT_ID,
        "--safe-plus-layer",
        "--authorized",
    ]
    for code in CANDIDATE_CODES:
        prepare.extend(["--candidate-code", code])
    _run(prepare, root=root, environment=environment)

    config_path = root / "configs" / f"private_data_inferred_{EXPERIMENT_ID}.yaml"
    predictions = output_dir / "prediction_files"
    _run(
        [
            "predict.py",
            "--data_dir",
            str(data_dir),
            "--output",
            str(predictions),
            "--mode",
            "retrain",
            "--config",
            str(config_path),
        ],
        root=root,
        environment=environment,
    )

    config = load_config(config_path)
    result_zip = output_dir / "result.zip"
    validation = create_result_zip(config, predictions, result_zip)
    print(
        "REPRODUCTION_OK "
        f"wells={validation['wells']} rows={validation['rows']} result={result_zip}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
