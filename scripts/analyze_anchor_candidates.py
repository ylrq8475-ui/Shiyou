from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from secure_local_audit import read_table, role_of, split_hint


def month_offset(left: pd.Period, right: pd.Period) -> int:
    return int(left.ordinal - right.ordinal)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()
    if not args.authorized or os.environ.get("COMPETITION_DATA_ACCESS_ACK") != "I_AM_AUTHORIZED":
        print("ANCHOR_ANALYSIS_BLOCKED", file=sys.stderr)
        return 2

    raw = Path(args.raw_dir).resolve()
    project = Path(args.project_dir).resolve()
    histories: list[tuple[str, pd.DataFrame]] = []
    plans: list[pd.DataFrame] = []
    for path in sorted(p for p in raw.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".xlsx"}):
        frame, _ = read_table(path)
        role = role_of(list(map(str, frame.columns)))
        if role == "history":
            histories.append((split_hint(path), frame))
        elif role == "plan":
            plans.append(frame)

    raw_values: set[str] = set()
    for _, frame in histories:
        values = frame["CSLB"].astype("string").str.strip().dropna()
        raw_values.update(value for value in values.tolist() if value)
    ordered_values = sorted(raw_values, key=lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest())
    code_for = {value: f"CSLB_{index:03d}" for index, value in enumerate(ordered_values, start=1)}

    stats: dict[str, dict[str, Any]] = {
        code: {
            "code": code,
            "raw_value": value,
            "train_rows": 0,
            "train_wells": 0,
            "test_rows": 0,
            "test_wells": 0,
            "test_nearest_offset_counts": Counter(),
            "train_complete_12m_windows": 0,
            "train_incomplete_12m_windows": 0,
            "consecutive_month_pairs": 0,
        }
        for value, code in code_for.items()
    }

    by_value_train_wells: dict[str, set[str]] = defaultdict(set)
    by_value_test_wells: dict[str, set[str]] = defaultdict(set)
    test_first_missing: dict[str, pd.Period] = {}
    events_by_test_well: dict[str, dict[str, list[pd.Period]]] = defaultdict(lambda: defaultdict(list))
    near_wells_by_value: dict[str, set[str]] = defaultdict(set)
    nearest_any_offsets: Counter[str] = Counter()

    for split, frame in histories:
        local = frame.copy()
        local["__month"] = pd.to_datetime(local["NY"], errors="coerce").dt.to_period("M")
        local["__event"] = local["CSLB"].astype("string").str.strip()
        well = str(local["WELL_ID"].dropna().iloc[0]) if local["WELL_ID"].notna().any() else ""
        if split == "test":
            missing = pd.to_numeric(local["RCYL"], errors="coerce").isna()
            if missing.any():
                test_first_missing[well] = local.loc[missing, "__month"].min()
        for value, group in local.loc[local["__event"].notna() & local["__event"].ne("")].groupby("__event"):
            value = str(value)
            if value not in code_for:
                continue
            code = code_for[value]
            stats[code][f"{split}_rows"] += int(len(group))
            if split == "train":
                by_value_train_wells[value].add(well)
            elif split == "test":
                by_value_test_wells[value].add(well)
                events_by_test_well[well][value].extend(group["__month"].dropna().tolist())
            months = sorted(set(group["__month"].dropna().tolist()))
            stats[code]["consecutive_month_pairs"] += sum(
                right.ordinal - left.ordinal == 1 for left, right in zip(months, months[1:])
            )

        if split == "train":
            target = pd.to_numeric(local["RCYL"], errors="coerce")
            for value, group in local.loc[local["__event"].notna() & local["__event"].ne("")].groupby("__event"):
                value = str(value)
                if value not in code_for:
                    continue
                anchor = group["__month"].max()
                future = local.loc[local["__month"].map(lambda period: period.ordinal if pd.notna(period) else -10**9).between(anchor.ordinal, anchor.ordinal + 11)]
                expected = {anchor.ordinal + step for step in range(12)}
                present = set(future["__month"].dropna().map(lambda period: period.ordinal))
                complete = expected == present and pd.to_numeric(future["RCYL"], errors="coerce").notna().all()
                key = "train_complete_12m_windows" if complete else "train_incomplete_12m_windows"
                stats[code_for[value]][key] += 1

    for value, code in code_for.items():
        stats[code]["train_wells"] = len(by_value_train_wells[value])
        stats[code]["test_wells"] = len(by_value_test_wells[value])
    for well, target_month in test_first_missing.items():
        all_before_or_at: list[pd.Period] = []
        for value, months in events_by_test_well.get(well, {}).items():
            before_or_at = [month for month in months if month <= target_month]
            if before_or_at:
                nearest = max(before_or_at)
                offset = month_offset(nearest, target_month)
                stats[code_for[value]]["test_nearest_offset_counts"][str(offset)] += 1
                if offset in {-1, 0}:
                    near_wells_by_value[value].add(well)
                all_before_or_at.extend(before_or_at)
        if all_before_or_at:
            nearest_any_offsets[str(month_offset(max(all_before_or_at), target_month))] += 1

    plan_summary: dict[str, dict[str, int]] = {
        code: {"plan_wells_matching_any_event_month": 0, "plan_wells_matching_first_event_month": 0, "plan_wells_matching_last_event_month": 0}
        for code in stats
    }
    if plans:
        plan = pd.concat(plans, ignore_index=True)
        plan["__month"] = pd.to_datetime(plan["完工日期"], errors="coerce").dt.to_period("M")
        plan_pairs = set(zip(plan["井号"].astype(str), plan["__month"].astype(str)))
        for value, code in code_for.items():
            events = []
            for split, frame in histories:
                local = frame.copy()
                event = local["CSLB"].astype("string").str.strip().eq(value)
                month = pd.to_datetime(local.loc[event, "NY"], errors="coerce").dt.to_period("M")
                events.extend(zip(local.loc[event, "WELL_ID"].astype(str), month.astype(str)))
            any_pairs = set(events)
            grouped: dict[str, list[str]] = defaultdict(list)
            for well, month in events:
                grouped[well].append(month)
            first_pairs = {(well, min(months)) for well, months in grouped.items()}
            last_pairs = {(well, max(months)) for well, months in grouped.items()}
            plan_summary[code] = {
                "plan_wells_matching_any_event_month": len({well for well, month in plan_pairs if (well, month) in any_pairs}),
                "plan_wells_matching_first_event_month": len({well for well, month in plan_pairs if (well, month) in first_pairs}),
                "plan_wells_matching_last_event_month": len({well for well, month in plan_pairs if (well, month) in last_pairs}),
            }

    serializable = []
    for code, item in stats.items():
        clean = dict(item)
        clean["test_nearest_offset_counts"] = dict(item["test_nearest_offset_counts"])
        clean.update(plan_summary[code])
        serializable.append(clean)
    private = project / "private_logs"
    reports = project / "reports"
    private.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    (private / "anchor_candidates_20260916.json").write_text(
        json.dumps({"candidates": serializable}, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    ranked = sorted(
        serializable,
        key=lambda item: (
            item["test_nearest_offset_counts"].get("-1", 0) + item["test_nearest_offset_counts"].get("0", 0),
            item["train_complete_12m_windows"],
            item["train_wells"],
        ),
        reverse=True,
    )
    uncovered = set(test_first_missing)
    greedy_codes: list[tuple[str, int]] = []
    while uncovered:
        best_value = max(ordered_values, key=lambda value: len(near_wells_by_value[value] & uncovered), default=None)
        if best_value is None:
            break
        covered = near_wells_by_value[best_value] & uncovered
        if not covered:
            break
        greedy_codes.append((code_for[best_value], len(covered)))
        uncovered -= covered
    lines = [
        "# 压裂锚点候选分析",
        "",
        "该分析仅使用匿名候选代码和聚合计数，不公开 CSLB 原始取值、井号或逐井记录。候选分析不等于官方规则确认。",
        "",
        f"- CSLB 非空精确取值候选数：{len(serializable)}",
        f"- 测试井目标窗口数：{len(test_first_missing)}",
        f"- 任意非空 CSLB 在首个空目标月偏移 -1/0 的联合覆盖：{len(set(test_first_missing) - uncovered)}/{len(test_first_missing)}",
        f"- 匿名候选贪心覆盖：{', '.join(f'{code}:{count}' for code, count in greedy_codes) or '无'}",
        f"- 各测试井最近任意 CSLB 相对首个空目标月的偏移分布：{dict(sorted(nearest_any_offsets.items()))}",
        "",
        "|候选代码|训练井覆盖|测试井覆盖|测试首个空目标月偏移-1/0覆盖|完整训练12月窗口|连续月对|方案匹配首次/末次|",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in ranked[:10]:
        offsets = item["test_nearest_offset_counts"]
        near = offsets.get("-1", 0) + offsets.get("0", 0)
        lines.append(
            f"|{item['code']}|{item['train_wells']}|{item['test_wells']}|{near}|"
            f"{item['train_complete_12m_windows']}|{item['consecutive_month_pairs']}|"
            f"{item['plan_wells_matching_first_event_month']}/{item['plan_wells_matching_last_event_month']}|"
        )
    lines.extend(
        [
            "",
            "P0 仍未关闭：必须由主办方或经用户批准的跨账户复核确认候选含义、连续事件起始月及预测首月偏移后，才能写入正式配置。",
        ]
    )
    (reports / "anchor_candidate_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    top_near = 0 if not ranked else ranked[0]["test_nearest_offset_counts"].get("-1", 0) + ranked[0]["test_nearest_offset_counts"].get("0", 0)
    print(f"ANCHOR_ANALYSIS_OK candidates={len(ranked)} top_near_window_coverage={top_near}/{len(test_first_missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
