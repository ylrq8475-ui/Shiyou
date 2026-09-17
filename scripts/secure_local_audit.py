from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np


SUPPORTED = {".csv", ".xlsx"}
KNOWN_HISTORY = {"WELL_ID", "NY", "RCYL", "CSLB"}
KNOWN_LAYER = {"WELL_ID", "XH", "CW"}
KNOWN_PLAN = {"井号", "完工日期"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_format(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()[:65536]
    encoding = None
    text = None
    for candidate in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(candidate)
            encoding = candidate
            break
        except UnicodeDecodeError:
            continue
    if text is None or encoding is None:
        raise ValueError("unsupported CSV encoding")
    try:
        delimiter = csv.Sniffer().sniff(text, delimiters=",\t;").delimiter
    except csv.Error:
        delimiter = ","
    return encoding, delimiter


def read_table(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        encoding, delimiter = csv_format(path)
        return pd.read_csv(path, encoding=encoding, sep=delimiter), {
            "encoding": encoding,
            "delimiter": repr(delimiter),
        }
    return pd.read_excel(path, engine="openpyxl"), {"sheet": 0}


def role_of(columns: list[str]) -> str:
    values = set(columns)
    if KNOWN_HISTORY.issubset(values):
        return "history"
    if KNOWN_PLAN.issubset(values):
        return "plan"
    if KNOWN_LAYER.issubset(values):
        return "layer"
    return "unknown"


def split_hint(path: Path) -> str:
    text = str(path).casefold()
    if any(token in text for token in ("train", "训练")):
        return "train"
    if any(token in text for token in ("test", "测试")):
        return "test"
    return "unknown"


def month_series(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    return parsed.dt.to_period("M")


def profile_table(frame: pd.DataFrame, role: str) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "rows": int(len(frame)),
        "columns": list(map(str, frame.columns)),
        "column_count": int(len(frame.columns)),
        "duplicate_rows": int(frame.duplicated().sum()),
        "dtypes": {str(name): str(dtype) for name, dtype in frame.dtypes.items()},
        "missing_count": {str(name): int(frame[name].isna().sum()) for name in frame.columns},
        "unique_count": {str(name): int(frame[name].nunique(dropna=True)) for name in frame.columns},
    }
    if "WELL_ID" in frame:
        profile["well_count"] = int(frame["WELL_ID"].nunique(dropna=True))
    if "NY" in frame:
        parsed = pd.to_datetime(frame["NY"], errors="coerce")
        profile["invalid_date_count"] = int(parsed.isna().sum() - frame["NY"].isna().sum())
        profile["date_min"] = None if parsed.dropna().empty else parsed.min().isoformat()
        profile["date_max"] = None if parsed.dropna().empty else parsed.max().isoformat()
        if "WELL_ID" in frame:
            profile["duplicate_well_month"] = int(
                pd.DataFrame({"well": frame["WELL_ID"], "month": parsed.dt.to_period("M")})
                .duplicated(["well", "month"])
                .sum()
            )
    if role == "history":
        target = pd.to_numeric(frame["RCYL"], errors="coerce")
        profile["target_missing_count"] = int(target.isna().sum())
        profile["target_nonfinite_count"] = int(
            (~target.isna() & ~target.map(lambda value: bool(np.isfinite(value)))).sum()
        )
        profile["target_negative_count"] = int((target < 0).sum())
        event = frame["CSLB"].astype("string").str.strip()
        profile["event_distinct_count"] = int(event.nunique(dropna=True))
        missing_target = target.isna()
        profile["missing_target_well_count"] = int(frame.loc[missing_target, "WELL_ID"].nunique(dropna=True))
        profile["missing_target_rows_per_well"] = sorted(
            map(int, frame.loc[missing_target].groupby("WELL_ID").size().unique().tolist())
        )
        profile["missing_by_column_inside_target_window"] = {
            str(name): int(frame.loc[missing_target, name].isna().sum()) for name in frame.columns
        }
    return profile


def cross_source_checks(tables: list[tuple[str, pd.DataFrame]]) -> dict[str, Any]:
    histories = [frame for role, frame in tables if role == "history"]
    plans = [frame for role, frame in tables if role == "plan"]
    result: dict[str, Any] = {"history_table_count": len(histories), "plan_table_count": len(plans)}
    if not histories or not plans:
        result["plan_history_mapping_checked"] = False
        return result
    history = pd.concat(histories, ignore_index=True)
    plan = pd.concat(plans, ignore_index=True)
    plan_keys = plan.loc[:, ["井号", "完工日期"]].copy()
    plan_keys["month"] = month_series(plan_keys["完工日期"])
    result.update(
        {
            "plan_history_mapping_checked": False,
            "mapping_note": "Event-specific mapping requires a private runtime selection and is not persisted in public code.",
            "history_well_count": int(history["WELL_ID"].nunique(dropna=True)),
            "plan_rows": int(len(plan_keys)),
            "plan_well_count": int(plan_keys["井号"].nunique(dropna=True)),
        }
    )
    return result


def write_once(path: Path, text: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError("immutable audit artifact already exists with different content")
        return
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, 0o444)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()
    if not args.authorized or os.environ.get("COMPETITION_DATA_ACCESS_ACK") != "I_AM_AUTHORIZED":
        print("AUDIT_BLOCKED: authorization acknowledgement missing", file=sys.stderr)
        return 2

    raw = Path(args.raw_dir).resolve()
    project = Path(args.project_dir).resolve()
    private = project / "private_logs"
    reports = project / "reports"
    private.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    all_files = sorted(path for path in raw.rglob("*") if path.is_file())
    manifest = []
    tables_private = []
    table_frames: list[tuple[str, pd.DataFrame]] = []
    errors = []
    role_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    well_counts: Counter[str] = Counter()

    for index, path in enumerate(all_files, start=1):
        relative = path.relative_to(raw).as_posix()
        item = {
            "file_id": f"raw_{index:03d}",
            "relative_path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "suffix": path.suffix.lower(),
        }
        manifest.append(item)
        if path.suffix.lower() not in SUPPORTED:
            continue
        try:
            frame, format_info = read_table(path)
            columns = list(map(str, frame.columns))
            role = role_of(columns)
            split = split_hint(path)
            role_counts[role] += 1
            split_counts[split] += 1
            profile = profile_table(frame, role)
            if "well_count" in profile:
                well_counts[f"{split}_{role}"] += profile["well_count"]
            tables_private.append(
                {
                    "file_id": item["file_id"],
                    "role": role,
                    "split_hint": split,
                    "format": format_info,
                    "profile": profile,
                }
            )
            table_frames.append((role, frame))
        except Exception as exc:
            errors.append({"file_id": item["file_id"], "error_type": type(exc).__name__})

    manifest_doc = {
        "raw_root_not_recorded": True,
        "file_count": len(manifest),
        "files": manifest,
    }
    manifest_text = json.dumps(manifest_doc, ensure_ascii=False, indent=2, sort_keys=True)
    manifest_path = private / "raw_manifest_20260916.json"
    write_once(manifest_path, manifest_text)
    write_once(
        private / "raw_manifest_20260916.json.sha256",
        hashlib.sha256(manifest_text.encode("utf-8")).hexdigest() + "  raw_manifest_20260916.json\n",
    )

    private_doc = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "table_count": len(tables_private),
        "tables": tables_private,
        "cross_source": cross_source_checks(table_frames),
        "errors": errors,
    }
    (private / "data_audit_20260916.json").write_text(
        json.dumps(private_doc, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )

    lines = [
        "# 数据质量摘要",
        "",
        "本报告由账户 B 在获准的本地环境执行只读审计生成，不包含文件名、样本行、井号、逐井记录或原始字段值。",
        "",
        f"- 原始文件数：{len(all_files)}",
        f"- 可读取表格数：{len(tables_private)}",
        f"- 读取失败表格数：{len(errors)}",
        f"- 角色计数：history={role_counts['history']}，layer={role_counts['layer']}，plan={role_counts['plan']}，unknown={role_counts['unknown']}",
        f"- 划分提示计数：train={split_counts['train']}，test={split_counts['test']}，unknown={split_counts['unknown']}",
        f"- 训练井史井数汇总：{well_counts['train_history']}",
        f"- 测试井史井数汇总：{well_counts['test_history']}",
        "- SHA-256 清单：已写入 private_logs，并采用只写一次策略。",
        "- 详细字段、缺失、重复、日期范围和跨源匹配统计：仅保存在 private_logs。",
        "",
        "正式标签仍受末次压裂规则、CSLB 精确值和连续事件起始月口径约束；本审计不把候选分析自动升级为官方规则。",
    ]
    (reports / "data_quality_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        "AUDIT_OK "
        f"files={len(all_files)} tables={len(tables_private)} errors={len(errors)} "
        f"history={role_counts['history']} layer={role_counts['layer']} plan={role_counts['plan']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
