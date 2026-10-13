"""零拟合诊断参考实现的纯合成测试。运行：python -E -B -m unittest test_diagnostics_reference"""
import unittest

import numpy as np

import diagnostics_reference as d


def curve(a, b):
    return a * np.exp(-b * np.arange(12))


class Tests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(26)

    def test_perfect_score(self):
        y = curve(10, 0.1)
        self.assertAlmostEqual(d.score([(y, y)]), 100.0, places=9)

    def test_zero_mass_counts(self):
        y1 = curve(5, 0.1); y1[0] = 0
        y2 = curve(5, 0.1)
        r = d.zero_month_mass([y1, y2])
        self.assertEqual(r["wells_with_any_zero_month"], 1)
        self.assertAlmostEqual(r["max_recoverable_points_if_perfect_zero_detection"], 100 * 0.5 / 2)
        self.assertAlmostEqual(r["zero_month_fraction"], 1 / 24)

    def test_zero_mass_matches_loss_gain(self):
        y = curve(5, 0.1); y[1] = 0
        p = curve(5, 0.1) * 1.2
        gain = d.score([(np.where(y == 0, 0, p), y)]) - d.score([(p, y)])
        self.assertAlmostEqual(gain, d.zero_month_mass([y])["max_recoverable_points_if_perfect_zero_detection"],
                               places=3)

    def test_informative_anchor_wins(self):
        T, am, am1 = [], [], []
        for _ in range(40):
            level = self.rng.lognormal(2, 0.5)
            y = curve(level, 0.08) * self.rng.lognormal(0, 0.05, 12)
            T.append(y); am.append(level * self.rng.lognormal(0, 0.05))
            am1.append(level / self.rng.lognormal(0.7, 0.6))   # 措施前水平，与响应弱相关
        r = d.compare_anchors(T, am, am1)
        self.assertEqual(r["wells_compared"], 40)
        self.assertGreater(r["delta_score_M_minus_M1"], 2.0)
        self.assertLess(r["delta_first2_loss_M_minus_M1"], 0)

    def test_uninformative_anchor_does_not_win(self):
        T, am, am1 = [], [], []
        for _ in range(40):
            level = self.rng.lognormal(2, 0.5)
            T.append(curve(level, 0.08))
            am.append(level * self.rng.lognormal(0, 0.8))      # 噪声锚点
            am1.append(level * self.rng.lognormal(0, 0.05))
        self.assertLess(d.compare_anchors(T, am, am1)["delta_score_M_minus_M1"], 0)

    def test_compare_skips_nonpositive_anchors(self):
        T = [curve(5, 0.1)] * 6
        r = d.compare_anchors(T, [1, 0, np.nan, 2, 3, 4], [1, 1, 1, -1, 2, 2])
        self.assertEqual(r["wells_compared"], 3)

    def test_loo_excludes_own_well(self):
        T = [curve(5, 0.1), curve(5, 0.1), curve(50, 0.1)]
        r = d.anchored_persistence_score(T, [5, 5, 5])
        self.assertLess(r["score"], 100.0)

    def test_smooth_oracle_exact_on_smooth_curve(self):
        y = curve(7, 0.12)
        r = d.smooth_oracle_scores([y])
        self.assertGreater(r["smooth_oracle_score"], 99.0)

    def test_smooth_oracle_penalised_by_noise(self):
        y = curve(7, 0.12) * self.rng.lognormal(0, 0.4, 12)
        self.assertLess(d.smooth_oracle_scores([y])["smooth_oracle_score"], 95.0)

    def test_zero_oracle_not_worse(self):
        y = curve(7, 0.12); y[[0, 5]] = 0
        r = d.smooth_oracle_scores([y])
        self.assertGreater(r["smooth_plus_zero_oracle_score"], r["smooth_oracle_score"])

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            d.well_loss(np.ones(11), np.ones(11))
        with self.assertRaises(ValueError):
            d.anchored_persistence_score([curve(1, 0)], [0.0])
        with self.assertRaises(ValueError):
            d.anchored_persistence_score([curve(1, 0)] * 2, [1.0, 1.0])

    def test_decision_thresholds_locked(self):
        self.assertEqual(d.DECISION["G_INFO"]["run_route_A_stage1_if_delta_score_ge"], 2.0)
        self.assertEqual(d.DECISION["G_CEIL"]["declare_95_not_credible_if_smooth_plus_zero_oracle_lt"], 90.0)
        self.assertEqual(d.DECISION["G_ZERO"]["activate_route_B_if_points_ge"], 2.0)


if __name__ == "__main__":
    unittest.main()
