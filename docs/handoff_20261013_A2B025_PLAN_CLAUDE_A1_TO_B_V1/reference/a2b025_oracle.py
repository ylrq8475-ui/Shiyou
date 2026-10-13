"""A2B-025 井级水平误差上限诊断：参考实现（账户A1（Claude）起草）。

纯 numpy，不读数据、不拟合。B 在内存中对固定回放 B0 的 OOF 预测调用这些函数，
只把聚合数写盘。函数输入是一口井 12 个月的预测 p 与真值 y（顺序为 horizon 1..12）。
"""
import math

import numpy as np

EPS = 1e-6
WEIGHTS = 2.0 ** -np.arange(1, 13)
DECISION_THRESHOLD = 90.0


def well_loss(p, y):
    p, y = np.asarray(p, float), np.asarray(y, float)
    if p.shape != (12,) or y.shape != (12,):
        raise ValueError("each well needs exactly 12 months")
    if not (np.isfinite(p).all() and np.isfinite(y).all()):
        raise ValueError("non-finite input")
    return float(np.sum(WEIGHTS * np.abs(p - y) / (np.abs(p) + np.abs(y) + EPS)))


def official_score(wells):
    """wells: iterable of (p, y). 未归一化 2^-t，先单井再井等权。"""
    losses = [well_loss(p, y) for p, y in wells]
    return 100.0 * (1.0 - float(np.mean(losses)))


def level_oracle(p, y):
    """主诊断：保持预测的月度形状，把整条预测按真实年总量缩放（“水平完全猜对”）。"""
    p, y = np.clip(np.asarray(p, float), 0, None), np.asarray(y, float)
    sp, sy = p.sum(), y.sum()
    if sp > 0:
        return p * (sy / sp)
    return np.full(12, sy / 12.0)


def best_scalar_oracle(p, y, grid=None):
    """次要（仅报告）：在对数网格上为每口井选使官方损失最小的单一倍数，给出任何整井倍率修正的更紧上限。"""
    p = np.clip(np.asarray(p, float), 0, None)
    if grid is None:
        grid = np.exp(np.linspace(math.log(0.05), math.log(20.0), 4001))
    if p.sum() <= 0:
        return level_oracle(p, y)
    losses = [well_loss(p * c, y) for c in grid]
    return p * grid[int(np.argmin(losses))]


def shape_oracle(p, y):
    """对照（仅报告）：保持预测的年均水平，换成真实的月度形状。"""
    p, y = np.clip(np.asarray(p, float), 0, None), np.asarray(y, float)
    if y.sum() > 0:
        return y * (p.mean() / y.mean())
    return p.copy()


def diagnose(wells):
    """wells: list of (p, y) for all 81 OOF wells. 返回只含聚合数的结果。"""
    wells = [(np.asarray(p, float), np.asarray(y, float)) for p, y in wells]
    base = official_score(wells)
    level = official_score([(level_oracle(p, y), y) for p, y in wells])
    best = official_score([(best_scalar_oracle(p, y), y) for p, y in wells])
    shape = official_score([(shape_oracle(p, y), y) for p, y in wells])
    return {
        "wells": len(wells),
        "baseline_oof": base,
        "level_oracle_oof": level,
        "best_scalar_oracle_oof": best,
        "shape_oracle_oof": shape,
        "decision_threshold": DECISION_THRESHOLD,
        "decision": "MAY_OPEN_NEW_PREREGISTRATION" if level >= DECISION_THRESHOLD
        else "CEILING_BELOW_95_KEEP_CURRENT_MODEL",
    }


def anchor_month_counts(values):
    """values: 每口井锚点月 M 的原始 RCYL（缺记录用 None）。只返回计数。"""
    n = len(values)
    present = [v for v in values if v is not None]
    finite = [v for v in present if isinstance(v, (int, float)) and math.isfinite(v)]
    return {"wells": n, "record_present": len(present), "finite": len(finite),
            "finite_positive": sum(v > 0 for v in finite)}
