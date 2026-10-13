"""A2B-025 参考实现的纯合成测试。运行：python -I -m unittest test_a2b025_oracle"""
import math
import unittest

import numpy as np

import a2b025_oracle as o


class OracleTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(25)
        self.y = rng.gamma(2, 3, 12) + 0.1
        self.p = self.y * rng.lognormal(0, 0.4, 12)

    def test_perfect_prediction_scores_100(self):
        self.assertAlmostEqual(o.official_score([(self.y, self.y)]), 100.0, places=9)

    def test_unnormalized_weights(self):
        s = o.official_score([(np.ones(12), np.zeros(12))])
        self.assertAlmostEqual(s, 100 * (1 - (1 - 2 ** -12) / (1 + 1e-6)), places=10)

    def test_equal_well_average(self):
        w1, w2 = (self.p, self.y), (self.y * 2, self.y)
        self.assertAlmostEqual(o.official_score([w1, w2]),
                               (o.official_score([w1]) + o.official_score([w2])) / 2, places=12)

    def test_level_oracle_matches_true_total(self):
        q = o.level_oracle(self.p, self.y)
        self.assertAlmostEqual(q.sum(), self.y.sum(), places=9)

    def test_level_oracle_invariant_to_prediction_scale(self):
        a = o.level_oracle(self.p, self.y)
        b = o.level_oracle(self.p * 7.3, self.y)
        self.assertTrue(np.allclose(a, b, rtol=1e-12))

    def test_level_oracle_exact_when_shape_right(self):
        q = o.level_oracle(self.y * 0.4, self.y)
        self.assertAlmostEqual(o.official_score([(q, self.y)]), 100.0, places=6)

    def test_level_oracle_zero_prediction(self):
        q = o.level_oracle(np.zeros(12), self.y)
        self.assertTrue(np.allclose(q, self.y.mean()))

    def test_best_scalar_not_worse_than_level(self):
        lv = o.official_score([(o.level_oracle(self.p, self.y), self.y)])
        bs = o.official_score([(o.best_scalar_oracle(self.p, self.y), self.y)])
        self.assertGreaterEqual(bs + 1e-6, lv)

    def test_shape_oracle_keeps_predicted_level(self):
        q = o.shape_oracle(self.p, self.y)
        self.assertAlmostEqual(q.mean(), self.p.mean(), places=9)

    def test_negative_predictions_clipped(self):
        p = self.p.copy(); p[0] = -5
        self.assertGreaterEqual(o.level_oracle(p, self.y).min(), 0)

    def test_decision_boundary(self):
        y = self.y
        good = [(o.level_oracle(y * 1.0, y), y)] * 3
        self.assertEqual(o.diagnose(good)["decision"], "MAY_OPEN_NEW_PREREGISTRATION")
        bad = [(np.full(12, y.mean()) * np.r_[np.ones(6) * 3, np.ones(6) * 0.1], y)]
        r = o.diagnose(bad)
        self.assertEqual(r["decision"], "CEILING_BELOW_95_KEEP_CURRENT_MODEL"
                         if r["level_oracle_oof"] < 90 else "MAY_OPEN_NEW_PREREGISTRATION")

    def test_threshold_is_inclusive(self):
        self.assertEqual(o.DECISION_THRESHOLD, 90.0)

    def test_diagnose_outputs_only_aggregates(self):
        r = o.diagnose([(self.p, self.y)] * 4)
        self.assertEqual(set(r), {"wells", "baseline_oof", "level_oracle_oof", "best_scalar_oracle_oof",
                                  "shape_oracle_oof", "decision_threshold", "decision"})
        self.assertTrue(all(not isinstance(v, (list, np.ndarray)) for v in r.values()))

    def test_anchor_month_counts(self):
        c = o.anchor_month_counts([None, float("nan"), 0.0, 3.2, -1.0, math.inf])
        self.assertEqual(c, {"wells": 6, "record_present": 5, "finite": 3, "finite_positive": 1})

    def test_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            o.well_loss(np.ones(11), np.ones(11))


if __name__ == "__main__":
    unittest.main()
