from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

from oil_uplift.config import load_config
from oil_uplift.io import sha256_file, write_json
from oil_uplift.multistep import build_test_samples, load_multisource_split
from oil_uplift.packaging import create_result_zip
from oil_uplift.submission import validate_result_zip


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--simulation-zip", required=True)
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()
    if not args.authorized or os.environ.get("COMPETITION_DATA_ACCESS_ACK") != "I_AM_AUTHORIZED":
        print("SIMULATION_LINT_BLOCKED", file=sys.stderr)
        return 2

    config = load_config(args.config)
    project = Path(config["_runtime"]["project_root"]).resolve()
    candidate_dir = Path(args.candidate_dir).resolve()
    output_zip = Path(args.simulation_zip).resolve()
    submissions = (project / "submissions").resolve()
    if submissions not in output_zip.parents or "simulation" not in output_zip.name.casefold():
        print("SIMULATION_LINT_OUTPUT_SCOPE_ERROR", file=sys.stderr)
        return 2
    if output_zip.name.casefold() == "result.zip":
        print("SIMULATION_LINT_FORMAL_NAME_FORBIDDEN", file=sys.stderr)
        return 2

    test_panel = build_test_samples(load_multisource_split(config, "test"), config)
    reference = test_panel[["WELL_ID", "NY"]]
    create_result_zip(config, candidate_dir, output_zip)
    lint = validate_result_zip(output_zip, reference)
    with zipfile.ZipFile(output_zip) as archive:
        names = archive.namelist()
        root_flat = all("/" not in name and "\\" not in name for name in names)
        csv_only = all(name.lower().endswith(".csv") for name in names)
    if not root_flat or not csv_only:
        print("SIMULATION_LINT_ARCHIVE_LAYOUT_ERROR", file=sys.stderr)
        return 2
    summary = {
        **lint,
        "simulation_only": True,
        "archive_file_count": len(names),
        "root_flat": root_flat,
        "csv_only": csv_only,
        "sha256": sha256_file(output_zip),
    }
    write_json(summary, project / "private_logs" / f"{output_zip.stem}_lint.json")
    print(
        "SIMULATION_LINT_OK "
        f"wells={lint['wells']} rows={lint['rows']} files={len(names)} "
        f"root_flat={str(root_flat).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
