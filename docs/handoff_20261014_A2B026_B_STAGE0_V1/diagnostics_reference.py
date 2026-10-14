"""95+方向零拟合诊断参考实现（独立方案研究账户：95+方向评估 起草）。

纯 numpy；不读数据、不拟合任何机器学习模型。执行方在内存中把每口训练井的
12 个真实目标月 y、锚点月 M 与 M−1 的原始 RCYL 传入，只把返回的聚合数写盘。
"""
import math

import numpy as np

EPS = 1e-6
W = 2.0 ** -np.arange(1, 13)


def well_loss(p, y):
    p, y = np.asarray(p, float), np.asarray(y, float)
    if p.shape != (12,) or y.shape != (12,) or not (np.isfinite(p).all() and np.isfinite(y).all()):
        raise ValueError("each well needs 12 finite months")
    return float(np.sum(W * np.abs(p - y) / (np.abs(p) + np.abs(y) + EPS)))


def score(pairs):
    return 100.0 * (1.0 - float(np.mean([well_loss(p, y) for p, y in pairs])))


# ---------- D1 停产月质量 ----------
def zero_month_mass(targets):
    """targets: list of 12-month truth arrays. 返回零值月占比与“从不预测0时零月最多可挽回的分数”。"""
    Y = np.vstack([np.asarray(t, float) for t in targets])
    zero = Y == 0
    per_well = (zero * W).sum(axis=1)
    return {
        "wells": int(Y.shape[0]),
        "zero_month_fraction": float(zero.mean()),
        "zero_month_fraction_by_horizon": [float(x) for x in zero.mean(axis=0)],
        "wells_with_any_zero_month": int(zero.any(axis=1).sum()),
        "max_recoverable_points_if_perfect_zero_detection": float(100 * per_well.mean()),
        "note": "若基线从不输出精确0，此值即完美停产识别的分数上界（不含对正值月的影响）",
    }


# ---------- D2 锚点信息量：留一井水平乘子的“锚定持平”预测 ----------
def anchored_persistence_score(targets, anchors):
    """p_t = c_t × anchor，c_t 为留一井（leave-one-well-out）各 horizon 比值 y_t/anchor 的中位数。
    只用于比较两个锚点（M 与 M−1）携带的水平信息；anchor 须有限且>0。"""
    Y = np.vstack([np.asarray(t, float) for t in targets])
    a = np.asarray(anchors, float)
    if not (np.isfinite(a).all() and (a > 0).all()):
        raise ValueError("anchors must be finite and positive")
    if len(a) < 3:
        raise ValueError("leave-one-well-out needs at least 3 wells")
    R = Y / a[:, None]
    pairs = []
    for i in range(len(a)):
        c = np.median(np.delete(R, i, axis=0), axis=0)
        pairs.append((c * a[i], Y[i]))
    first2 = float(np.mean([np.sum(W[:2] * np.abs(p[:2] - y[:2]) / (np.abs(p[:2]) + np.abs(y[:2]) + EPS))
                            for p, y in pairs]))
    return {"wells": len(a), "score": score(pairs), "first2_weighted_loss": first2}


def compare_anchors(targets, anchor_m, anchor_m1):
    """只在两个锚点都有限且>0的井上比较；返回差值（M − M−1）。"""
    am, am1 = np.asarray(anchor_m, float), np.asarray(anchor_m1, float)
    keep = np.isfinite(am) & (am > 0) & np.isfinite(am1) & (am1 > 0)
    T = [t for t, k in zip(targets, keep) if k]
    m = anchored_persistence_score(T, am[keep])
    m1 = anchored_persistence_score(T, am1[keep])
    return {"wells_compared": int(keep.sum()), "anchor_M": m, "anchor_M_minus_1": m1,
            "delta_score_M_minus_M1": m["score"] - m1["score"],
            "delta_first2_loss_M_minus_M1": m["first2_weighted_loss"] - m1["first2_weighted_loss"]}


# ---------- D4 平滑曲线上限（标签神谕，仅诊断） ----------
_B_GRID = np.linspace(-0.3, 1.0, 261)
_A_GRID = np.exp(np.linspace(math.log(0.05), math.log(20.0), 801))


def best_smooth_fit(y, keep_true_zeros=False):
    """每井在 p_t = a·exp(−b·(t−1)) 族中选使官方损失最小的 (a,b)。
    a 以真实12月均值为尺度在对数网格搜索；keep_true_zeros=True 时在真实零月输出0（停产识别神谕）。"""
    y = np.asarray(y, float)
    t = np.arange(12)
    scale = y.mean() if y.mean() > 0 else 1.0
    best = (float("inf"), None)
    zero = y == 0
    for b in _B_GRID:
        base = np.exp(-b * t)
        base = base / base.mean()
        for a in _A_GRID:
            p = a * scale * base
            if keep_true_zeros:
                p = np.where(zero, 0.0, p)
            loss = float(np.sum(W * np.abs(p - y) / (np.abs(p) + np.abs(y) + EPS)))
            if loss < best[0]:
                best = (loss, p)
    return best[1]


def smooth_oracle_scores(targets):
    plain = [(best_smooth_fit(y), np.asarray(y, float)) for y in targets]
    zeros = [(best_smooth_fit(y, keep_true_zeros=True), np.asarray(y, float)) for y in targets]
    return {"wells": len(targets), "smooth_oracle_score": score(plain),
            "smooth_plus_zero_oracle_score": score(zeros),
            "note": "标签神谕：任何输出两参数指数平滑曲线的预测器在完美参数下的上界；不是可部署分数"}


DECISION = {
    "G_ZERO": {"activate_route_B_if_points_ge": 2.0, "eliminate_route_B_if_points_lt": 1.0},
    "G_INFO": {"run_route_A_stage1_if_delta_score_ge": 2.0, "eliminate_route_A_if_delta_score_le": 0.0,
               "also_require_first2_loss_lower": True},
    "G_CEIL": {"declare_95_not_credible_if_smooth_plus_zero_oracle_lt": 90.0},
}
