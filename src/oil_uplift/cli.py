from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .audit import audit_declared_files, require_local_audit_authorization
from .config import load_config, resolve_project_path
from .exceptions import OilUpliftError
from .inference import run_inference
from .io import assert_no_duplicate_paths, resolve_declared_files, write_json
from .packaging import create_code_zip, create_result_zip
from .submission import read_submission, validate_submission_frame
from .training import run_training


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oil-uplift")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit explicitly declared local data files")
    audit.add_argument("--config", required=True)
    audit.add_argument("--split", choices=("train", "test", "both"), default="both")
    audit.add_argument("--authorized", action="store_true")

    train = subparsers.add_parser("train", help="Train and validate local models")
    train.add_argument("--config", required=True)

    infer = subparsers.add_parser("infer", help="Load a local artifact and predict")
    infer.add_argument("--config", required=True)
    infer.add_argument("--model", required=True)
    infer.add_argument("--output", required=True)

    validate = subparsers.add_parser("validate-submission", help="Validate an official candidate submission")
    validate.add_argument("--config", required=True)
    validate.add_argument("--submission", required=True)

    package = subparsers.add_parser("package", help="Create root-flat result and code ZIP files")
    package.add_argument("--config", required=True)
    package.add_argument("--submission", required=True)
    package.add_argument("--result-zip", required=True)
    package.add_argument("--code-zip", required=True)
    return parser


def _audit(args, config) -> None:
    require_local_audit_authorization(args.authorized)
    splits = ("train", "test") if args.split == "both" else (args.split,)
    paths = []
    for split in splits:
        paths.extend(resolve_declared_files(config, split))
    assert_no_duplicate_paths(paths)
    report = audit_declared_files(paths, config)
    output = resolve_project_path(config, config.get("data", {}).get("audit_output", "artifacts/audit_report.json"))
    write_json(report, output)
    print(f"Audit complete: {report['file_count']} anonymized file entries written.")


def _validate(args, config) -> None:
    frame = read_submission(Path(args.submission).expanduser().resolve(), config)
    result = validate_submission_frame(frame, config)
    print(f"Submission valid: {result['rows']} rows.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "audit":
            _audit(args, config)
        elif args.command == "train":
            result = run_training(config)
            print(f"Training complete. Selected model: {result['selected_model']}.")
        elif args.command == "infer":
            result = run_inference(
                config,
                Path(args.model).expanduser().resolve(),
                Path(args.output).expanduser().resolve(),
            )
            print(f"Inference complete: {result['rows']} candidate rows.")
        elif args.command == "validate-submission":
            _validate(args, config)
        elif args.command == "package":
            submission = Path(args.submission).expanduser().resolve()
            create_result_zip(config, submission, Path(args.result_zip).expanduser().resolve())
            code = create_code_zip(config, Path(args.code_zip).expanduser().resolve())
            print(f"Packaging complete: code archive contains {code['file_count']} files.")
        return 0
    except OilUpliftError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
