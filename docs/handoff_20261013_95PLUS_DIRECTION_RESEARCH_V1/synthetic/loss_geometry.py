"""纯合成推导：官方单月损失与对数误差尺度的关系。不读赛事数据、不拟合模型。
用法：python -I loss_geometry.py <输出JSON>
"""
import json, math, sys
import numpy as np

W = 2.0 ** -np.arange(1, 13)
SW = W.sum()
EPS = 1e-6

def month_loss(p, y):
    return np.abs(p - y) / (np.abs(p) + np.abs(y) + EPS)

def identity_check(rng):
    y = rng.gamma(2, 3, 20000) + 0.5
    z = rng.normal(0, 0.7, 20000)
    p = y * np.exp(z)
    return float(np.max(np.abs(month_loss(p, y) - np.tanh(np.abs(z) / 2))))

def expected_loss(sigma, n=400000, seed=7):
    """z~N(0,sigma^2) 时 E[tanh(|z|/2)]，即每月同分布对数误差下的期望单月损失。"""
    z = np.random.default_rng(seed).normal(0, sigma, n)
    return float(np.mean(np.tanh(np.abs(z) / 2)))

def sigma_for_score(score):
    target = (1 - score / 100) / SW
    lo, hi = 1e-4, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if expected_loss(mid) < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def score_for_sigma(s):
    return 100 * (1 - SW * expected_loss(s))

rng = np.random.default_rng(13)
out = {"identity_max_abs_err": identity_check(rng),
       "identity": "|p-y|/(p+y) = tanh(|ln(p/y)|/2)，epsilon 可忽略时成立",
       "model": "各月对数误差 z~N(0,σ²) 同分布时，Score = 100·(1 − ΣW·E[tanh(|z|/2)])，ΣW=1−2^-12"}
points = {"B0_OOF_fixed": 73.71410733861434, "platform_reported": 86.2003, "target_95": 95.0,
          "level_oracle_OOF": 80.94413529978314, "shape_oracle_OOF": 81.21752992148006,
          "best_scalar_oracle_OOF": 88.17733827575375}
out["equivalent_log_error_sigma"] = {k: sigma_for_score(v) for k, v in points.items()}
s = out["equivalent_log_error_sigma"]
# 独立可加检验：σ_total² ?= σ_level_resid² + σ_shape_resid²
# level_oracle 去掉水平误差 → 剩余为形状误差 σS；shape_oracle 去掉形状误差 → 剩余为水平误差 σL
sS, sL, sT = s["level_oracle_OOF"], s["shape_oracle_OOF"], s["B0_OOF_fixed"]
out["independent_additive_check"] = {
    "sigma_shape_residual_from_level_oracle": sS, "sigma_level_residual_from_shape_oracle": sL,
    "sqrt_sum_squares": math.hypot(sS, sL), "sigma_total_B0": sT,
    "ratio": math.hypot(sS, sL) / sT,
    "note": "比值接近1说明“水平+形状独立相加”的近似可用；只是量级模型，不是分解定理"}
# 95 所需的 (σL, σS) 组合
grid = {}
for sl in (0.0, 0.05, 0.08, 0.10, 0.12):
    rem = s["target_95"] ** 2 - sl ** 2
    grid[f"sigma_level={sl}"] = math.sqrt(rem) if rem > 0 else None
out["target95_max_sigma_shape_given_sigma_level"] = grid
out["reduction_needed_platform_to_95_in_sigma"] = 1 - s["target_95"] / s["platform_reported"]
out["score_if_sigma"] = {str(x): score_for_sigma(x) for x in (0.10, 0.125, 0.15, 0.2, 0.25, 0.3, 0.35, 0.5, 0.7)}
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
