from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .config import project_root, resolve_project_path
from .exceptions import ConfigurationError, DataContractError

SUPPORTED_SUFFIXES = {".csv", ".xlsx"}
SOURCE_ROLES = ("history", "layer", "plan", "template")


def resolve_declared_files(config: dict[str, Any], split: str) -> list[Path]:
    if split not in {"train", "test"}:
        raise ConfigurationError("Data split must be 'train' or 'test'.")
    return [item["path"] for item in resolve_declared_source_files(config, split)]


def resolve_declared_source_files(config: dict[str, Any], split: str) -> list[dict[str, Any]]:
    if split not in {"train", "test"}:
        raise ConfigurationError("Data split must be 'train' or 'test'.")
    data_config = config.get("data", {})
    sources = data_config.get("sources", {}).get(split)
    if sources is not None:
        if not isinstance(sources, dict):
            raise ConfigurationError(f"data.sources.{split} must be a mapping.")
        role_entries = []
        for role in SOURCE_ROLES:
            entries = sources.get(role, [])
            if not isinstance(entries, list):
                raise ConfigurationError(f"data.sources.{split}.{role} must be a list.")
            role_entries.extend((role, entry) for entry in entries)
    else:
        role_entries = [("history", entry) for entry in data_config.get(f"{split}_files", [])]
    declared = [entry for _, entry in role_entries]
    if not isinstance(declared, list) or not declared:
        raise ConfigurationError(f"data.sources.{split} must explicitly list at least one file.")

    base_value = data_config.get("input_dir")
    base = resolve_project_path(config, base_value) if base_value else project_root(config)
    resolved: list[dict[str, Any]] = []
    for role, item in role_entries:
        if not isinstance(item, str) or not item.strip():
            raise ConfigurationError(f"data.{split}_files contains an invalid entry.")
        candidate = Path(item).expanduser()
        path = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ConfigurationError("Only explicitly declared CSV and XLSX files are supported.")
        if not path.is_file():
            raise DataContractError(f"Declared {split} file is unavailable (entry is not logged).")
        resolved.append({"split": split, "role": role, "path": path})
    return resolved


def read_table(path: Path, config: dict[str, Any]) -> pd.DataFrame:
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            csv_config = config.get("data", {}).get("csv", {})
            return pd.read_csv(
                path,
                encoding=csv_config.get("encoding", "utf-8-sig"),
                sep=csv_config.get("delimiter", ","),
            )
        if suffix == ".xlsx":
            sheet = config.get("data", {}).get("excel", {}).get("sheet_name", 0)
            return pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    except Exception as exc:
        # Do not propagate third-party messages because they often contain absolute paths.
        raise DataContractError("Unable to read a declared data file; the path is suppressed.") from exc
    raise DataContractError("Unsupported table type.")


def load_declared_split(config: dict[str, Any], split: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for number, path in enumerate(resolve_declared_files(config, split), start=1):
        frame = read_table(path, config).copy()
        frame["__source_file_id"] = f"file_{number:03d}"
        frames.append(frame)
    if not frames:
        raise DataContractError(f"No frames were loaded for {split}.")
    columns = [list(frame.columns) for frame in frames]
    if any(current != columns[0] for current in columns[1:]):
        raise DataContractError(f"Declared {split} files do not share an identical column order.")
    return pd.concat(frames, ignore_index=True)


def write_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_no_duplicate_paths(paths: Iterable[Path]) -> None:
    resolved = [str(path.resolve()).casefold() for path in paths]
    if len(resolved) != len(set(resolved)):
        raise ConfigurationError("The declared file list contains duplicate entries.")
