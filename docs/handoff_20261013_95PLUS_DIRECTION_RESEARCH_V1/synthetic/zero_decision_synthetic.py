"""纯合成推导：官方指标下“停产月(真值=0)”的损失与最优零预测判据。不读赛事数据、不拟合真实模型。
用法：python -I zero_decision_synthetic.py <输出JSON>
"""
import json, sys
import numpy as np

EPS = 1e-6
ml = lambda p, y: np.abs(p - y) / (np.abs(p) + np.abs(y) + EPS)
out = {}
# 1 单月损失的离散性
out["y0_p0"] = float(ml(np.array(0.0), np.array(0.0)))
out["y0_p_small_positive"] = float(ml(np.array(1e-3), np.array(0.0)))
out["y_positive_p0"] = float(ml(np.array(0.0), np.array(5.0)))
out["note_1"] = "真值为0时，任何≥1e-3的正预测损失≈1；只有输出精确0才得0。B0输出expm1(z)·s，只有叶内目标全为0才会恰为0"

# 2 最优判据：设 q=P(y=0)，ℓ+=真值为正时正预测的期望单月损失
#    预测0的期望损失 = (1-q)·1；预测正值 = q·1 + (1-q)·ℓ+
#    预测0 当且仅当 q > (1-ℓ+)/(2-ℓ+)
out["zero_threshold_formula"] = "predict exact 0 iff P(y=0) > (1-l_plus)/(2-l_plus)"
out["threshold_by_l_plus"] = {str(l): (1 - l) / (2 - l) for l in (0.1, 0.2, 0.25, 0.3, 0.4)}
# 蒙特卡洛核对
rng = np.random.default_rng(3)
n = 400000
check = {}
for q in (0.2, 0.35, 0.43, 0.5, 0.7):
    zero = rng.random(n) < q
    y = np.where(zero, 0.0, rng.gamma(2, 3, n) + 0.5)
    p_pos = np.where(zero, rng.gamma(2, 3, n) + 0.5, y * np.exp(rng.normal(0, 0.6, n)))
    l_plus = float(np.mean(ml(p_pos[~zero], y[~zero])))
    check[str(q)] = {"loss_predict_positive": float(np.mean(ml(p_pos, y))),
                     "loss_predict_zero": float(np.mean(ml(np.zeros(n), y))),
                     "l_plus": l_plus, "threshold": (1 - l_plus) / (2 - l_plus)}
out["monte_carlo"] = check

# 3 停产月对分数的影响（量级）：零月占比 f 且模型从不输出0时，这些月按权重满额计损
W = 2.0 ** -np.arange(1, 13)
out["score_loss_if_zero_months_uniform_and_never_predicted"] = {
    str(f): 100 * f * W.sum() for f in (0.02, 0.05, 0.08, 0.1, 0.15)}
out["note_3"] = "若零月在各月均匀占比f，模型从不预测0，则这部分直接扣约100·f分；零月若集中在早期月份，扣分更多。真实占比未知，需零拟合诊断D1/D3测定"
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
