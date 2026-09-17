from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .exceptions import ConfigurationError


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).expanduser().resolve()
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError("Unable to load the configuration file.") from exc
    if not isinstance(config, dict):
        raise ConfigurationError("The configuration root must be a mapping.")
    _validate_safety_policy(config)
    config["_runtime"] = {
        "config_path": str(config_path),
        "project_root": str(config_path.parent.parent),
    }
    return config


def _validate_safety_policy(config: dict[str, Any]) -> None:
    project = config.get("project", {})
    if project.get("allow_external_data") is not False:
        raise ConfigurationError("External data must remain disabled for this project.")
    if project.get("allow_pretrained_weights") is not False:
        raise ConfigurationError("Pretrained weights must remain disabled for this project.")


def project_root(config: dict[str, Any]) -> Path:
    runtime = config.get("_runtime", {})
    root = runtime.get("project_root")
    if root:
        return Path(root)
    return Path.cwd().resolve()


def resolve_project_path(config: dict[str, Any], value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (project_root(config) / path).resolve()


def config_fingerprint(config: dict[str, Any]) -> str:
    """Return a stable hash without machine-specific paths or runtime metadata."""
    normalized = copy.deepcopy(config)
    normalized.pop("_runtime", None)
    data = normalized.get("data", {})
    for key in ("input_dir", "train_files", "test_files", "audit_output"):
        data.pop(key, None)
    model = normalized.get("model", {})
    for key in ("artifact_path", "metrics_output"):
        model.pop(key, None)
    payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def require_keys(mapping: dict[str, Any], keys: list[str], context: str) -> None:
    missing = [key for key in keys if mapping.get(key) in (None, "", [])]
    if missing:
        raise ConfigurationError(f"{context} is incomplete; missing: {', '.join(missing)}")
