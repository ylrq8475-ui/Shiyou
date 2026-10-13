"""账户A1（新接手）独立检查程序。

只使用虚构数据和公开匿名聚合；不读取赛事原始数据、不加载真实模型、不做真实拟合。
用法：
  python -I a1_independent_checks.py --source <B匿名包source目录> --final <A024 FINAL_RESULT.json> --out <结果JSON>
"""
import argparse
import datetime
import json
import math
import sys

import numpy as np

CHECKS = []


def check(name, ok, **detail):
    CHECKS.append({"name": name, "passed": bool(ok), **detail})
    return ok


# ---------- 1. 官方指标：独立实现 ----------
def a1_score(wells):
    """wells: list of (pred[12], truth[12]); 未归一化2^-t，先单井再井等权。"""
    per = []
    for p, y in wells:
        p, y = np.asarray(p, float), np.asarray(y, float)
        t = np.arange(1, 13)
        per.append(100 * (1 - np.sum(2.0 ** -t * np.abs(p - y) / (np.abs(p) + np.abs(y) + 1e-6))))
    return float(np.mean(per))


def metric_checks(src):
    sys.path.insert(0, src + "/src")
    import pandas as pd
    from oil_uplift.scoring import official_twelve_month_score
    rng = np.random.default_rng(1013)
    wells, rows = [], []
    for w in range(7):
        y = rng.gamma(2, 3, 12)
        y[rng.integers(0, 12)] = 0.0  # 含零真值
        p = np.clip(y * rng.lognormal(0, 0.4, 12), 0, None)
        p[rng.integers(0, 12)] = 0.0
        wells.append((p, y))
        for t in range(12):
            rows.append({"WELL_ID": f"W{w}", "horizon": t + 1, "RCYL": y[t], "prediction": p[t]})
    frame = pd.DataFrame(rows)
    proj = official_twelve_month_score(frame, truth_column="RCYL", prediction_column="prediction", epsilon=1e-6).total
    mine = a1_score(wells)
    check("metric_matches_project_function", abs(proj - mine) < 1e-10, abs_diff=abs(proj - mine))
    # 两端皆零：分母epsilon，单月损失为0
    check("metric_zero_zero_month_no_loss", abs(a1_score([(np.zeros(12), np.zeros(12))]) - 100) < 1e-12)
    # 权重未归一化：全错时总损失=1-2^-12
    full = a1_score([(np.ones(12), np.zeros(12))])
    check("metric_unnormalized_weights", abs(full - 100 * (2 ** -12)) < 1e-4, score_all_wrong=full)
    # 井等权：一口12行井与另一口井权重相同（与行数无关）
    a = a1_score([wells[0], wells[1]])
    check("metric_equal_well_average", abs(a - (a1_score([wells[0]]) + a1_score([wells[1]])) / 2) < 1e-12)


# ---------- 2. 旧A2B-013目标变换 与 R1-B0臂 等价 ----------
def transform_equivalence(src):
    sys.path.insert(0, src)
    sys.path.insert(0, src + "/src")
    import pandas as pd
    from oil_uplift import training
    from deployment_core import inverse_prediction
    raw = np.array([np.nan, -2.0, 0.0, 1.0, 0.37, 5.5, np.inf, 1e-9])
    z = np.linspace(-0.5, 2.0, raw.size)
    panel = pd.DataFrame({"history__RCYL__last": raw})

    class Fake:
        def predict(self, x):
            return z
    old = training.predict_pipeline_output(Fake(), "extra_trees_log_ratio_last", panel, panel)
    old = np.clip(old, 0, None)
    new_b0 = inverse_prediction(z, raw, "B0")
    check("old_A013_inverse_equals_R1_B0_inverse", np.array_equal(old, new_b0),
          cases=int(raw.size))
    y = pd.Series(np.linspace(0, 9, raw.size))
    old_target = training._transform_target(y, panel, "log_ratio_last")
    scale = np.where(np.isfinite(raw) & (raw > 0), raw, 1.0)
    check("old_A013_target_equals_B0_definition",
          np.allclose(old_target, np.log1p(y.to_numpy() / scale), rtol=0, atol=0))


# ---------- 3. 路由：独立实现 vs 部署实现 ----------
def routing_checks(src):
    from deployment_core import predict_system, digest
    import pandas as pd

    feats = [f"f{i}" for i in range(325)]

    class Model:
        def __init__(self):
            self.params = {"a": 1}

        def get_params(self):
            return self.params

    class Pipe:
        def __init__(self, z):
            self.z = z
            self.named_steps = {"model": Model()}
            self.feature_names_in_ = np.array(feats)

        def predict(self, x):
            return np.full(len(x), self.z)

    def frame(raws):
        rows = []
        for w, r in enumerate(raws):
            for h in range(1, 13):
                rows.append({"WELL_ID": f"W{w}", "NY": f"2024/{h:02d}/01", "horizon": h,
                             "history__RCYL__last": r, **{f: 0.0 for f in feats}})
        return pd.DataFrame(rows)

    art = {"feature_columns": feats, "feature_order_sha256": digest(feats), "mode": "R1",
           "pipelines": {"B0": Pipe(0.5), "C1": Pipe(1.5)}, "model_parameters": {"a": 1}}
    raws = [np.nan, 0.0, -1.0, 1.0, 2.5, np.inf]
    f = frame(raws)
    ans, arms = predict_system(art, f)
    mine = []
    for r in raws:
        pos = math.isfinite(r) and r > 0
        mine += [np.expm1(0.5) * r if pos else np.expm1(1.5)] * 12
    check("route_independent_equals_deployment", np.allclose(ans, mine, rtol=0, atol=1e-12),
          wells=len(raws))
    check("route_positive_one_uses_B0", abs(ans[36] - np.expm1(0.5)) < 1e-15)
    allpos = frame([0.3, 1.0, 7.0])
    ans2, arms2 = predict_system(art, allpos)
    check("all_positive_test_R1_exactly_equals_B0", np.array_equal(ans2, arms2["B0"]))


# ---------- 4. ExtraTrees 确定性与行序敏感性（虚构数据） ----------
def determinism_checks():
    from sklearn.ensemble import ExtraTreesRegressor
    rng = np.random.default_rng(7)
    X = rng.normal(size=(300, 20))
    y = X[:, 0] + rng.normal(0, 0.3, 300)
    Xt = rng.normal(size=(50, 20))
    kw = dict(n_estimators=100, min_samples_leaf=6, max_features=0.75, random_state=20260916)
    a = ExtraTreesRegressor(n_jobs=-1, **kw).fit(X, y).predict(Xt)
    b = ExtraTreesRegressor(n_jobs=1, **kw).fit(X, y).predict(Xt)
    check("same_data_seed_same_predictions_across_n_jobs", np.max(np.abs(a - b)) < 1e-12,
          max_abs=float(np.max(np.abs(a - b))))
    check("six_decimal_lexemes_equal", all(f"{u:.6f}" == f"{v:.6f}" for u, v in zip(a, b)))
    perm = rng.permutation(300)
    c = ExtraTreesRegressor(n_jobs=1, **kw).fit(X[perm], y[perm]).predict(Xt)
    # 发现：bootstrap=False 的ExtraTrees对训练行序不敏感（阈值在节点最小/最大值间均匀抽取）
    check("extratrees_row_order_invariant_synthetic", np.max(np.abs(a - c)) < 1e-12,
          max_abs=float(np.max(np.abs(a - c))))
    # GroupKFold：按组标签排序分配，虚构数据中与行序无关。A013勘误所称“行序改变OOF”的机制未由A1复现（P3，未核验）
    from sklearn.model_selection import GroupKFold
    groups = np.repeat(np.arange(81), 12)
    Xg = np.zeros((972, 1))
    f1 = {g: k for k, (_, v) in enumerate(GroupKFold(5).split(Xg, groups=groups)) for g in set(groups[v])}
    order = rng.permutation(81)
    groups2 = np.repeat(order, 12)
    f2 = {g: k for k, (_, v) in enumerate(GroupKFold(5).split(Xg, groups=groups2)) for g in set(groups2[v])}
    moved = sum(1 for g in range(81) if len({f1[g]} ^ {f2[g]}) or
                sorted(h for h in range(81) if f1[h] == f1[g]) != sorted(h for h in range(81) if f2[h] == f2[g]))
    check("groupkfold_row_order_invariant_synthetic", moved == 0, wells_with_changed_fold_mates=moved)


# ---------- 5. 日期补零语义 ----------
def date_checks():
    pairs = [("2023/12/1", "2023/12/01"), ("2024/1/1", "2024/01/01"), ("2024/10/1", "2024/10/01")]
    ok = all(datetime.datetime.strptime(a, "%Y/%m/%d") == datetime.datetime.strptime(b, "%Y/%m/%d")
             for a, b in pairs)
    check("zero_padding_preserves_date_semantics", ok)


# ---------- 6. A024 原研究门槛：从公开FINAL_RESULT独立复算 ----------
def a024_gates(final):
    d = json.load(open(final, encoding="utf-8"))
    later = [s for s in d["research"] if s["stage"] == "five_later_splits"]
    deltas = [s["arms"]["R1"]["official_score"] - s["arms"]["B0"]["official_score"] for s in later]
    mean = float(np.mean(deltas))
    check("A024_later_mean_delta", abs(mean - 0.478483932139153) < 1e-9, value=mean)
    check("A024_later_5of5_positive", sum(x > 0 for x in deltas) == 5)
    c = d["confirmation"]["arms"]
    cd = c["R1"]["official_score"] - c["B0"]["official_score"]
    check("A024_confirm_delta_below_0p20", cd < 0.20, value=cd)
    f2 = d["confirmation"]["first2_score_delta"]
    l1 = c["B0"]["monthly_official_weighted_loss"][:2]
    l2 = c["R1"]["monthly_official_weighted_loss"][:2]
    recomputed = 100 * (sum(l1) - sum(l2))
    check("A024_confirm_first2_below_0", recomputed < 0 and abs(recomputed - f2) < 1e-9, value=recomputed)
    check("A024_confirmation_FAILED_maintained", not d["confirmation_gate"]["passed"] and
          d["budget"]["stage_successes"]["conditional_private_full_fit"] == 0)
    return d


# ---------- 7. 95+ 上限算术（只用公开聚合） ----------
def ceiling(d):
    W = sum(2.0 ** -t for t in range(1, 13))
    out = {}
    for target in (86.2003, 90.0, 95.0):
        loss = 1 - target / 100
        r = loss / W  # 若各月相对误差相同
        k = (1 + r) / (1 - r)  # p/y 倍数
        out[str(target)] = {"mean_weighted_loss": loss, "uniform_relative_error_r": r,
                            "allowed_ratio_band": [1 / k, k]}
    b0 = d["confirmation"]["arms"]["B0"]
    rel = b0["monthly_unweighted_relative_error"]
    out["confirm_B0_monthly_relative_error_min_max"] = [min(rel), max(rel)]
    oof = [s["arms"]["B0"]["official_score"] for s in d["research"]] + [b0["official_score"]]
    out["B0_oof_range_7_splits"] = [min(oof), max(oof)]
    out["needed_platform_loss_reduction_to_95"] = 1 - (1 - 0.95) / (1 - 0.862003)
    # 同等比例的损失降幅换到OOF上所需分数
    oof_loss = 1 - b0["official_score"] / 100
    out["equivalent_OOF_if_same_relative_loss_cut"] = 100 * (1 - oof_loss * (0.05 / 0.137997))
    check("ceiling_flat_error_profile", max(rel) / min(rel) < 1.35, ratio=max(rel) / min(rel),
          note="误差在12个月近乎平坦：主要是井级产量水平误差，不是衰减形状")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--final", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    metric_checks(a.source)
    transform_equivalence(a.source)
    routing_checks(a.source)
    determinism_checks()
    date_checks()
    d = a024_gates(a.final)
    ceil = ceiling(d)
    res = {"author": "账户A（新接手）独立审核与交付", "real_fits": 0, "real_data_read": 0,
           "checks": CHECKS, "passed": sum(c["passed"] for c in CHECKS), "total": len(CHECKS),
           "ceiling_arithmetic": ceil}
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(res["passed"], "/", res["total"])
    return 0 if res["passed"] == res["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
