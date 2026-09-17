from __future__ import annotations

from typing import Any

import pandas as pd

from .exceptions import ConfigurationError, DataContractError, PolicyBlockedError


def require_confirmed_label_policy(config: dict[str, Any]) -> None:
    labels = config.get("labels", {})
    if labels.get("enabled") is not True:
        raise PolicyBlockedError("Formal label generation is disabled in configuration.")

    last_rule = labels.get("official_last_fracture_rule", {})
    if last_rule.get("confirmed") is not True:
        raise PolicyBlockedError("The official last-fracture rule is not confirmed.")
    required_rule_values = ["version", "group_keys", "order_by"]
    missing_rule = [key for key in required_rule_values if last_rule.get(key) in (None, "", [])]
    if missing_rule:
        raise PolicyBlockedError(
            "The confirmed last-fracture rule is incomplete: " + ", ".join(missing_rule)
        )
    event_values = last_rule.get("eligible_event_values", [])
    if event_values and not last_rule.get("event_type_column"):
        raise PolicyBlockedError("Eligible event values require an event-type column.")

    target = labels.get("target_definition", {})
    if target.get("confirmed") is not True:
        raise PolicyBlockedError("The official target definition is not confirmed.")
    missing_target = [key for key in ("name", "unit") if target.get(key) in (None, "")]
    if missing_target:
        raise PolicyBlockedError("The confirmed target definition is incomplete: " + ", ".join(missing_target))


def select_official_last_fractures(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Select rows only after an explicit official rule has passed validation."""
    require_confirmed_label_policy(config)
    rule = config["labels"]["official_last_fracture_rule"]
    group_keys = list(rule["group_keys"])
    order_by = list(rule["order_by"])
    tie_break = list(rule.get("tie_break_columns", []))
    required = group_keys + order_by + tie_break
    event_column = rule.get("event_type_column")
    event_values = list(rule.get("eligible_event_values", []))
    if event_values:
        required.append(event_column)
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise DataContractError(f"Columns required by the official fracture rule are missing: {', '.join(missing)}")

    eligible = frame
    if event_values:
        eligible = eligible.loc[eligible[event_column].isin(event_values)]
    if eligible.empty:
        raise DataContractError("No rows satisfy the confirmed fracture eligibility rule.")

    sort_columns = group_keys + order_by + tie_break
    ordered = eligible.sort_values(sort_columns, kind="mergesort")
    if not tie_break and ordered.duplicated(group_keys + order_by, keep=False).any():
        raise DataContractError("The official order has ties; configure confirmed tie-break columns.")
    return ordered.groupby(group_keys, sort=False, as_index=False).tail(1).copy()


def build_formal_training_rows(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    selected = select_official_last_fractures(frame, config)
    labels = config["labels"]
    source = labels.get("source")
    target_column = config.get("schema", {}).get("mapping", {}).get("target")
    if source == "precomputed_column":
        if not target_column:
            raise ConfigurationError("schema.mapping.target is required for precomputed labels.")
        if target_column not in selected.columns:
            raise DataContractError("The configured target column is missing.")
        target = pd.to_numeric(selected[target_column], errors="coerce")
        if target.isna().any():
            raise DataContractError("The formal target contains missing or non-numeric values.")
        selected[target_column] = target
        return selected
    if source == "formula":
        raise PolicyBlockedError(
            "Formula labels require a reviewed implementation after the official formula is confirmed."
        )
    raise ConfigurationError("labels.source must be 'precomputed_column' or 'formula'.")
