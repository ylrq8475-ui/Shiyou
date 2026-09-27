"""One-command retrain + inference + packaging for the round-3 candidates (S1 / S3)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from oil_uplift.config import load_config  # noqa: E402
from oil_uplift.ts_blend import VARIANTS, predict_candidate, write_result_zip  # noqa: E402

CANDIDATE_CODES = ("CSLB_012", "CSLB_032")
EXPERIMENT_ID = "trial_safe_plus_layer"


def main() -> int:
    default_variant = json.loads((ROOT / "submission_variant.json").read_text(encoding="utf-8"))["variant"]
    parser = argparse.ArgumentParser(description="Retrain and package a round-3 candidate result.zip.")
    parser.add_argument("--data-dir", required=True, help="Authorized official competition data directory")
    parser.add_argument("--output-dir", default="reproduction_output")
    parser.add_argument("--variant", default=default_variant, choices=sorted(VARIANTS))
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()
    if not args.authorized:
        print("REPRODUCTION_BLOCKED: pass --authorized only in an approved local environment.", file=sys.stderr)
        return 2
    data_dir = Path(args.data_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = (ROOT / output_dir).resolve()
    env = dict(os.environ)
    env["COMPETITION_DATA_ACCESS_ACK"] = "I_AM_AUTHORIZED"
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run([sys.executable, "scripts/analyze_anchor_candidates.py", "--raw-dir", str(data_dir), "--project-dir", str(ROOT), "--authorized"], cwd=ROOT, env=env, check=True)
    prepare = [sys.executable, "scripts/prepare_private_runtime_config.py", "--raw-dir", str(data_dir), "--project-dir", str(ROOT),
               "--experiment-id", EXPERIMENT_ID, "--safe-plus-layer", "--overwrite", "--authorized"]
    for code in CANDIDATE_CODES:
        prepare += ["--candidate-code", code]
    subprocess.run(prepare, cwd=ROOT, env=env, check=True)
    config = load_config(ROOT / "configs" / f"private_data_inferred_{EXPERIMENT_ID}.yaml")
    frame, audit = predict_candidate(config, args.variant)
    result = output_dir / "result.zip"
    write_result_zip(frame, result)
    print("REPRODUCTION_OK " + " ".join(f"{k}={v}" for k, v in sorted(audit.items())) + f" result={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
