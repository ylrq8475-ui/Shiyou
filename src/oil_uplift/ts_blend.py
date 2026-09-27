"""Round-3 candidates: A2B-013 information boundary + global sliding-window time-series model.

Information boundary (data-inferred, user-approved, NOT confirmed by the organizer):
- consecutive eligible CSLB months form one event; the anchor is the last month of the last segment;
- the forecast starts in the month after the anchor;
- the tree model sees well history strictly before the anchor month (A2B-013 boundary), no layer, no plan;
- the time-series model uses the same boundary (last observed month = anchor - 1).
Only aggregate information is printed. No raw rows, well IDs or raw category values are logged.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from .exceptions import DataContractError
from .multistep import _history_features, build_test_samples, build_training_samples, load_multisource_split
from .training import _fit_pipeline, _model_pipeline, predict_pipeline_output

TREE_MODEL = "extra_trees_log_ratio_last"
TS_COLUMNS = ["RCYL", "SCTS", "HS", "RCYL1", "YY", "TY", "PL", "BJ", "CC"]
TS_SEEDS = (0, 1, 2)
VARIANTS = {
    # name: (tree weight, ts weight, global multiplier)
    "S1": (0.7, 0.3, 1.0),
    "S3": (1.0, 0.0, float(np.exp(-0.15))),
    "A2B": (1.0, 0.0, 1.0),
    # S4: tree 0.5 + lean level-correction 0.5 (handled in predict_candidate)
    "S4": (0.5, 0.0, 1.0),
}
LEAN_WEIGHT = {"S4": 0.5}


def _period_ordinal(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.isna().any():
        raise DataContractError("History contains an invalid calendar date.")
    return parsed.dt.to_period("M").map(lambda p: p.ordinal)


def _runs(flags: np.ndarray) -> list[list[int]]:
    runs: list[list[int]] = []
    for index, flag in enumerate(flags):
        if flag:
            if runs and runs[-1][1] == index - 1:
                runs[-1][1] = index
            else:
                runs.append([index, index])
    return runs


# ---------------------------------------------------------------- tree model (A2B-013 boundary)
def _a2b_panel(config: dict[str, Any], tables, base: pd.DataFrame) -> pd.DataFrame:
    history = tables.history.copy()
    history["WELL_ID"] = history["WELL_ID"].astype(str)
    rows = []
    for well, group in base.groupby("WELL_ID", sort=False):
        anchor = pd.Timestamp(group["anchor_time"].iloc[0])
        cutoff = (anchor.to_period("M") - 1).to_timestamp()
        features = _history_features(history, well, cutoff, config)
        features["anchor_year"] = anchor.year
        features["anchor_month"] = anchor.month
        for _, row in group.iterrows():
            item = {"WELL_ID": well, "anchor_time": anchor, "horizon": row["horizon"], "forecast_step": row["forecast_step"], **features}
            if "RCYL" in group:
                item["RCYL"] = row["RCYL"]
            rows.append(item)
    return pd.DataFrame(rows)


def _tree_features(panel: pd.DataFrame) -> list[str]:
    return [
        column for column in panel.columns
        if (column in ("horizon", "forecast_step", "history_month_count") or str(column).startswith("history__"))
        and not panel[column].isna().all()
    ]


def fit_predict_tree(config, train_tables, test_tables, train_base, test_base) -> tuple[np.ndarray, dict[str, int]]:
    train = _a2b_panel(config, train_tables, train_base)
    test = _a2b_panel(config, test_tables, test_base)
    features = _tree_features(train)
    if any(str(c).startswith(("layer__", "plan_first__")) for c in features):
        raise DataContractError("The A2B boundary must exclude layer and plan features.")
    test = test.reindex(columns=list(dict.fromkeys(list(test.columns) + features)))
    estimator = _model_pipeline(TREE_MODEL, train[features], config)
    _fit_pipeline(estimator, TREE_MODEL, train[features], train["RCYL"], train["horizon"], train)
    prediction = np.clip(predict_pipeline_output(estimator, TREE_MODEL, test[features], test), 0.0, None)
    return prediction, {"tree_feature_count": len(features), "history_feature_count": sum(str(c).startswith("history__") for c in features)}


# ---------------------------------------------------------------- global sliding-window time-series model
def _grids(tables, eligible: list[str]) -> dict[str, dict[str, Any]]:
    history = tables.history.copy()
    history["WELL_ID"] = history["WELL_ID"].astype(str)
    history["__o"] = _period_ordinal(history["NY"])
    out: dict[str, dict[str, Any]] = {}
    for well, group in history.groupby("WELL_ID", sort=True):
        group = group.set_index("__o").sort_index()
        if group.index.duplicated().any():
            raise DataContractError("A well has duplicate monthly rows.")
        index = range(int(group.index.min()), int(group.index.max()) + 1)
        grid = {c: pd.to_numeric(group[c], errors="coerce").reindex(index).to_numpy(float) for c in TS_COLUMNS}
        flags = group["CSLB"].astype("string").str.strip().isin(eligible).fillna(False).reindex(index).fillna(False).to_numpy(bool)
        grid.update({"o0": int(group.index.min()), "n": len(index), "runs": _runs(flags)})
        out[well] = grid
    return out


def _ts_features(grid: dict[str, Any], last: int, gap: int) -> tuple[dict[str, float], float]:
    rcyl = grid["RCYL"]

    def at(column: str, i: int) -> float:
        values = grid[column]
        return float(values[i]) if 0 <= i < len(values) else np.nan

    level = rcyl[last]
    if not (np.isfinite(level) and level > 0):
        window = rcyl[max(0, last - 2): last + 1]
        window = window[np.isfinite(window) & (window > 0)]
        level = float(window.mean()) if len(window) else 1.0
    f: dict[str, float] = {"log_lvl": float(np.log(level))}
    for k in range(12):
        value = at("RCYL", last - k)
        f[f"lr_{k}"] = float(np.log1p(value / level)) if last - k >= 0 and np.isfinite(value) else np.nan
    for width in (3, 6, 12):
        seg = rcyl[max(0, last - width + 1): last + 1]
        seg = seg[np.isfinite(seg)]
        f[f"m{width}"] = float(np.log1p(seg.mean() / level)) if len(seg) else np.nan
        f[f"s{width}"] = float(seg.std() / level) if len(seg) > 1 else np.nan
        logs = np.log1p(seg / level)
        f[f"tr{width}"] = float(np.polyfit(np.arange(len(logs)), logs, 1)[0]) if len(logs) >= 3 else np.nan
    for column in ("SCTS", "HS", "YY", "TY", "PL", "BJ", "CC"):
        f[f"{column}_0"] = at(column, last)
        seg = grid[column][max(0, last - 2): last + 1]
        f[f"{column}_m3"] = float(np.nanmean(seg)) if np.isfinite(seg).any() else np.nan
    f["HS_d6"] = at("HS", last) - at("HS", last - 6)
    liquid = at("RCYL1", last)
    f["liq_ratio"] = liquid / level if np.isfinite(liquid) else np.nan
    runs = [r for r in grid["runs"] if r[0] <= last + gap]
    f["n_runs"] = len(runs)
    f["hist_len"] = last + 1
    if runs:
        start, end = runs[-1]
        f["since_end"] = (last + gap) - min(end, last + gap)
        f["run_len"] = min(end, last + gap) - start + 1
        f["ev_recent"] = int(f["since_end"] <= 0)
        pre = rcyl[max(0, start - 3): start]
        pre = pre[np.isfinite(pre)]
        f["lvl_over_pre"] = float(np.log1p(level / pre.mean())) if len(pre) and pre.mean() > 0 else np.nan
        if len(runs) > 1:
            p_start, p_end = runs[-2]
            f["gap_prev"] = start - p_end
            before = rcyl[max(0, p_start - 3): p_start]
            after = rcyl[p_end + 1: min(p_end + 4, start)]
            before, after = before[np.isfinite(before)], after[np.isfinite(after)]
            f["prev_uplift"] = float(np.log1p(after.mean() / before.mean())) if len(before) and len(after) and before.mean() > 0 else np.nan
    else:
        f.update({"since_end": 99, "run_len": 0, "ev_recent": 0})
    return f, float(level)


def _ts_training_rows(grids: dict[str, dict[str, Any]], gap: int = 1) -> tuple[pd.DataFrame, np.ndarray]:
    features, targets = [], []
    for well in sorted(grids):
        grid = grids[well]
        rcyl = grid["RCYL"]
        for last in range(5, grid["n"] - gap - 12):
            future = rcyl[last + gap + 1: last + gap + 13]
            if len(future) < 12 or not np.isfinite(future).all():
                continue
            f, level = _ts_features(grid, last, gap)
            event_origin = int(any(end == last + gap for _, end in grid["runs"]))
            for h in range(12):
                item = dict(f)
                item["h"] = h + 1
                item["event_origin"] = event_origin
                features.append(item)
                targets.append(np.log1p(max(float(future[h]), 0.0) / level))
    return pd.DataFrame(features), np.asarray(targets, dtype=float)


def fit_predict_ts(config, train_tables, test_tables, test_base) -> tuple[np.ndarray, dict[str, int]]:
    eligible = list(config["anchors"]["eligible_event_values"])
    train_grids = _grids(train_tables, eligible)
    test_grids = _grids(test_tables, eligible)
    x_train, y_train = _ts_training_rows(train_grids, gap=1)
    columns = list(x_train.columns)
    rows, levels = [], []
    for well, group in test_base.groupby("WELL_ID", sort=False):
        grid = test_grids[str(well)]
        anchor = pd.Timestamp(group["anchor_time"].iloc[0]).to_period("M").ordinal - grid["o0"]
        f, level = _ts_features(grid, anchor - 1, 1)
        for h in group["horizon"]:
            item = dict(f)
            item["h"] = int(h)
            item["event_origin"] = 1
            rows.append(item)
            levels.append(level)
    x_test = pd.DataFrame(rows).reindex(columns=columns)
    predictions = []
    for seed in TS_SEEDS:
        model = HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0, random_state=seed
        )
        model.fit(x_train, y_train)
        predictions.append(np.expm1(model.predict(x_test)))
    prediction = np.clip(np.mean(predictions, axis=0) * np.asarray(levels), 0.0, None)
    return prediction, {"ts_windows": int(len(x_train) // 12), "ts_feature_count": len(columns)}


# ---------------------------------------------------------------- orchestration and packaging
def _raw_template_dates(test_tables) -> dict[tuple[str, int], str]:
    history = test_tables.history
    missing = history.loc[pd.to_numeric(history["RCYL"], errors="coerce").isna()]
    out: dict[tuple[str, int], str] = {}
    for well, ny in zip(missing["WELL_ID"].astype(str), missing["NY"].astype(str)):
        out[(well, pd.Timestamp(pd.to_datetime(ny)).to_period("M").ordinal)] = ny
    return out


def predict_candidate(config: dict[str, Any], variant: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    if variant not in VARIANTS:
        raise DataContractError(f"Unknown variant: {variant}")
    tree_w, ts_w, multiplier = VARIANTS[variant]
    train_tables = load_multisource_split(config, "train")
    test_tables = load_multisource_split(config, "test")
    train_base = build_training_samples(train_tables, config)
    train_base["WELL_ID"] = train_base["WELL_ID"].astype(str)
    test_base = build_test_samples(test_tables, config)
    test_base["WELL_ID"] = test_base["WELL_ID"].astype(str)
    test_base = test_base.sort_values("__template_order", kind="mergesort").reset_index(drop=True)
    tree, audit = fit_predict_tree(config, train_tables, test_tables, train_base, test_base)
    blended = np.log(tree + 1e-3) * tree_w
    if ts_w > 0:
        ts, ts_audit = fit_predict_ts(config, train_tables, test_tables, test_base)
        audit.update(ts_audit)
        blended = blended + np.log(ts + 1e-3) * ts_w
    if variant in LEAN_WEIGHT:
        lean, lean_audit = fit_predict_lean(config, train_tables, test_tables, train_base, test_base)
        audit.update(lean_audit)
        blended = blended + np.log(lean + 1e-3) * LEAN_WEIGHT[variant]
    prediction = np.clip((np.exp(blended) - 1e-3) * multiplier, 0.0, None)
    raw_dates = _raw_template_dates(test_tables)
    periods = pd.to_datetime(test_base["NY"]).dt.to_period("M").map(lambda p: p.ordinal)
    dates = [raw_dates[(w, int(p))] for w, p in zip(test_base["WELL_ID"], periods)]
    frame = pd.DataFrame({"WELL_ID": test_base["WELL_ID"].to_numpy(), "NY": dates, "RCYL": prediction})
    if not np.isfinite(frame["RCYL"]).all() or (frame["RCYL"] < 0).any():
        raise DataContractError("Predictions must be finite and non-negative.")
    audit.update({"variant": variant, "wells": int(frame["WELL_ID"].nunique()), "rows": int(len(frame)), "train_wells": int(train_base["WELL_ID"].nunique())})
    return frame, audit


def write_result_zip(frame: pd.DataFrame, path: Path) -> None:
    from .submission import well_csv_filename

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for well, group in frame.groupby("WELL_ID", sort=False):
            info = zipfile.ZipInfo(well_csv_filename(str(well)), date_time=(2026, 9, 27, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, group.loc[:, ["WELL_ID", "NY", "RCYL"]].to_csv(index=False, float_format="%.6f").encode("utf-8-sig"))
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if any("/" in n or "\\" in n or not n.endswith(".csv") for n in names):
            raise DataContractError("result.zip root may contain only per-well CSV files.")
        back = pd.concat(
            [pd.read_csv(io.BytesIO(archive.read(n)), encoding="utf-8-sig", dtype={"WELL_ID": str, "NY": str}) for n in names],
            ignore_index=True,
        )
    if list(back.columns) != ["WELL_ID", "NY", "RCYL"] or len(back) != len(frame):
        raise DataContractError("result.zip content check failed.")
    if back.groupby("WELL_ID").size().ne(12).any():
        raise DataContractError("Each well must have exactly 12 rows.")
    if set(zip(back["WELL_ID"], back["NY"])) != set(zip(frame["WELL_ID"], frame["NY"])):
        raise DataContractError("result.zip keys differ from the template.")


# ---------------------------------------------------------------- S4: lean level-correction model
# Uses the adopted data-inferred boundary: the anchor month is observable (it ends before the
# forecast is issued) and the officially supplied target-month covariates in the test input
# (SCTS, YY, TY, BJ, CC, CC1, PL, BZ/CSLB presence) are used as known-in-advance inputs.
LEAN_COVARIATES = ["SCTS", "YY", "TY", "BJ", "CC", "CC1", "PL"]
from sklearn.ensemble import ExtraTreesRegressor  # noqa: E402


def _indexed_history(tables) -> pd.DataFrame:
    history = tables.history.copy()
    history["WELL_ID"] = history["WELL_ID"].astype(str)
    history["__o"] = _period_ordinal(history["NY"])
    for column in ["RCYL", "HS", *LEAN_COVARIATES]:
        history[column] = pd.to_numeric(history[column], errors="coerce")
    history["DISP"] = history["BJ"] ** 2 * history["CC"] * history["CC1"]
    return history.set_index(["WELL_ID", "__o"]).sort_index()


def _lean_features(config, tables, panel: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """panel: A2B panel (history before the anchor) in row order WELL_ID x horizon."""
    idx = _indexed_history(tables)
    eligible = set(config["anchors"]["eligible_event_values"])
    anchor_rows: dict[str, dict[str, float]] = {}
    for well in pd.unique(panel["WELL_ID"]):
        a = pd.Timestamp(panel.loc[panel["WELL_ID"] == well, "anchor_time"].iloc[0]).to_period("M").ordinal
        hw = idx.loc[well]
        rc = hw["RCYL"]
        flags = hw["CSLB"].astype("string").str.strip().isin(eligible).fillna(False)
        months = sorted(int(o) for o in hw.index[flags.to_numpy()] if o <= a)
        start = a
        while start - 1 in months:
            start -= 1
        prev = rc.get(a - 1, np.nan)
        pre = rc.reindex(range(start - 3, start)).mean()
        anc = rc.get(a, np.nan)
        anchor_rows[well] = {
            "anc_ratio_prev": np.log1p(anc / prev) if prev and prev > 0 else np.nan,
            "anc_ratio_pre": np.log1p(anc / pre) if pre and pre > 0 else np.nan,
            "anc_SCTS": hw["SCTS"].get(a, np.nan),
            "anc_HS": hw["HS"].get(a, np.nan),
            "anc_run_len": a - start + 1,
        }
    level = panel["history__RCYL__last"].where(panel["history__RCYL__last"] > 0, 1.0).fillna(1.0).to_numpy(float)
    rows = []
    for i, (well, at, h) in enumerate(zip(panel["WELL_ID"], panel["anchor_time"], panel["horizon"])):
        a = pd.Timestamp(at).to_period("M").ordinal
        lv = level[i]
        f = {
            "h": int(h), "log_lvl": float(np.log(lv)), **anchor_rows[well],
            "trend6": panel["history__RCYL__trend_6"].iloc[i] / lv,
            "std12": panel["history__RCYL__roll_12_std"].iloc[i] / lv,
            "m3": np.log1p(panel["history__RCYL__roll_3_mean"].iloc[i] / lv),
            "m12": np.log1p(panel["history__RCYL__roll_12_mean"].iloc[i] / lv),
            "scts_last": panel["history__SCTS__last"].iloc[i],
            "hist_n": panel["history_month_count"].iloc[i],
        }
        base = idx.loc[(well, a - 1)] if (well, a - 1) in idx.index else None
        row = idx.loc[(well, a + int(h))] if (well, a + int(h)) in idx.index else None
        for column in [*LEAN_COVARIATES, "DISP"]:
            rv = row[column] if row is not None else np.nan
            bv = base[column] if base is not None else np.nan
            f[f"futr__{column}"] = np.log((rv + 1e-3) / (bv + 1e-3)) if pd.notna(rv) and pd.notna(bv) and rv > 0 and bv > 0 else np.nan
        for column in ("BZ", "CSLB"):
            v = row[column] if row is not None else np.nan
            present = 0 if (pd.isna(v) or str(v).strip() == "") else 1
            f[f"futf__{column}"] = present
            if column == "BZ":
                f["futf__BZ_len"] = 0 if present == 0 else len(str(v))
        rows.append(f)
    x = pd.DataFrame(rows)
    wells = panel["WELL_ID"].to_numpy()
    for column in ("BZ", "CSLB"):
        x[f"futw__n{column}"] = x.groupby(wells)[f"futf__{column}"].transform(lambda s: s.iloc[:3].sum())
    for column in ("SCTS", "YY", "TY", "DISP"):
        x[f"futw__{column}"] = x.groupby(wells)[f"futr__{column}"].transform(lambda s: s.iloc[:3].mean())
    return x, level


def fit_predict_lean(config, train_tables, test_tables, train_base, test_base) -> tuple[np.ndarray, dict[str, int]]:
    train = _a2b_panel(config, train_tables, train_base)
    test = _a2b_panel(config, test_tables, test_base)
    x_train, level_train = _lean_features(config, train_tables, train)
    x_test, level_test = _lean_features(config, test_tables, test)
    x_test = x_test.reindex(columns=x_train.columns)
    y = np.log1p(np.clip(train["RCYL"].to_numpy(float), 0, None) / level_train)
    model = ExtraTreesRegressor(n_estimators=500, min_samples_leaf=10, max_features=0.5, n_jobs=-1, random_state=0)
    model.fit(x_train.fillna(-999), y)
    prediction = np.clip(np.expm1(model.predict(x_test.fillna(-999))) * level_test, 0.0, None)
    return prediction, {"lean_feature_count": int(x_train.shape[1])}
