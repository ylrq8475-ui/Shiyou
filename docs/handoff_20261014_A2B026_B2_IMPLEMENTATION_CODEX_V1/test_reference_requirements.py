"""Independent, synthetic specification checks. NOT tests of unprovided B code."""
import json
import math
import unittest
from pathlib import Path

EPS = 1e-6

def valid(values):
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('FINITE_NONNEGATIVE_REQUIRED')

def monthly(p, y):
    valid([p, y])
    return abs(p - y) / (abs(p) + abs(y) + EPS)

def loss(pred, truth):
    if len(pred) != 12 or len(truth) != 12:
        raise ValueError('TWELVE_MONTHS_REQUIRED')
    return sum(2 ** (-t) * monthly(p, y) for t, (p, y) in enumerate(zip(pred, truth), 1))

def official(wells):
    if not wells:
        raise ValueError('WELLS_REQUIRED')
    return 100 * (1 - sum(loss(p, y) for p, y in wells) / len(wells))

def positive_loss(wells):
    eligible = []
    for pred, truth in wells:
        loss(pred, truth)
        weights = [2 ** (-t) for t, y in enumerate(truth, 1) if y > 0]
        if weights:
            eligible.append(sum(2 ** (-t) * monthly(p, y) for t, (p, y) in enumerate(zip(pred, truth), 1) if y > 0) / sum(weights))
    if not eligible:
        raise ValueError('POSITIVE_INNER_FOLD_REQUIRED')
    return sum(eligible) / len(eligible)

def threshold(inner_folds):
    if len(inner_folds) != 3:
        raise ValueError('THREE_INNER_FOLDS_REQUIRED')
    ell = sum(positive_loss(wells) for wells in inner_folds) / 3
    if not math.isfinite(ell) or not 0 <= ell <= 1:
        raise ValueError('INVALID_ELL_PLUS')
    return (1 - ell) / (2 - ell)

def qzero(classes, probabilities):
    if len(classes) != len(probabilities) or len(set(classes)) != len(classes) or not set(classes) <= {0, 1}:
        raise ValueError('INVALID_CLASSES')
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities) or not math.isclose(sum(probabilities), 1.0):
        raise ValueError('INVALID_PROBABILITY')
    return probabilities[classes.index(1)] if 1 in classes else 0.0

def routed(base, q, tau):
    valid(base)
    if len(base) != len(q) or not math.isfinite(tau) or not 0 <= tau <= 1 or any(not math.isfinite(v) or not 0 <= v <= 1 for v in q):
        raise ValueError('INVALID_ROUTE_INPUT')
    return [0.0 if prob > tau else p for p, prob in zip(base, q)]

class ReferenceRequirements(unittest.TestCase):
    def test_identical_and_all_zero_score(self):
        self.assertEqual(official([([0.] * 12, [0.] * 12)]), 100.0)

    def test_unnormalized_time_weights(self):
        self.assertAlmostEqual(loss([1.] * 12, [0.] * 12), (1 - 2 ** -12) / (1 + EPS))

    def test_early_late_order(self):
        early = [1.] + [0.] * 11
        late = [0.] * 11 + [1.]
        self.assertAlmostEqual(loss(early, [0.] * 12) / loss(late, [0.] * 12), 2048)

    def test_equal_well_mean(self):
        a = ([0.] * 12, [0.] * 12)
        b = ([1.] * 12, [0.] * 12)
        self.assertAlmostEqual(official([a, b]), (official([a]) + official([b])) / 2)

    def test_invalid_target_and_prediction_rejected(self):
        for value in [float('nan'), float('inf'), -1.]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                loss([value] + [0.] * 11, [0.] * 12)

    def test_twelve_months_required(self):
        with self.assertRaises(ValueError):
            loss([0.] * 11, [0.] * 11)

    def test_positive_conditional_loss_not_official_loss(self):
        p = [2.] + [0.] * 11
        y = [1.] + [0.] * 11
        self.assertAlmostEqual(positive_loss([(p, y)]), 1 / (3 + EPS))
        self.assertAlmostEqual(loss(p, y), 0.5 / (3 + EPS))

    def test_equal_three_fold_mean_not_pooled_wells(self):
        accurate = ([1.] * 12, [1.] * 12)
        missed = ([0.] * 12, [1.] * 12)
        folds = [[accurate] * 3, [missed], [missed]]
        ell = (2 / (1 + EPS)) / 3
        self.assertAlmostEqual(threshold(folds), (1 - ell) / (2 - ell))
        pooled_ell = 2 / (5 * (1 + EPS))
        self.assertNotAlmostEqual(threshold(folds), (1 - pooled_ell) / (2 - pooled_ell))

    def test_undefined_inner_positive_loss_stops(self):
        zeros = ([0.] * 12, [0.] * 12)
        with self.assertRaises(ValueError):
            threshold([[zeros], [zeros], [zeros]])

    def test_exact_zero_not_near_zero(self):
        self.assertEqual([int(y == 0) for y in [0., -0., 1e-15, 1.]], [1, 1, 0, 0])

    def test_probability_class_order_and_single_class(self):
        self.assertEqual(qzero([1, 0], [.3, .7]), .3)
        self.assertEqual(qzero([0], [1.]), 0.)
        self.assertEqual(qzero([1], [1.]), 1.)

    def test_strict_threshold_and_B0_unchanged(self):
        self.assertEqual(routed([2., 3., 4.], [.5, .6, .1], .5), [2., 0., 4.])

    def test_invalid_probability_stops(self):
        for p in [-.1, 1.1, float('nan')]:
            with self.subTest(value=p), self.assertRaises(ValueError):
                routed([1.], [p], .5)

    def test_zero_gain_and_false_zero_cost_close(self):
        truth = [[0.] * 12, [1.] * 12]
        base = [[1.] * 12, [1.] * 12]
        pred = [[0.] * 12, [0.] * 12]
        delta = official(list(zip(pred, truth))) - official(list(zip(base, truth)))
        positive_gain = loss(base[0], truth[0]) - loss(pred[0], truth[0])
        false_zero_cost = loss(base[1], truth[1]) - loss(pred[1], truth[1])
        self.assertLess(false_zero_cost, 0)
        self.assertAlmostEqual(delta, 100 * (positive_gain + false_zero_cost) / 2)

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReferenceRequirements)
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    evidence = {'scope': 'Independent synthetic mathematical reference only; no B-2 code was provided or exercised',
                'tests_run': outcome.testsRun, 'failures': len(outcome.failures), 'errors': len(outcome.errors),
                'passed': outcome.wasSuccessful(), 'B_implementation_verified': False,
                'model_fits': 0, 'preprocessor_fits': 0, 'real_data_read': False}
    with Path(__file__).with_name('REFERENCE_SYNTHETIC_RESULTS.json').open('x', encoding='utf-8') as out:
        json.dump(evidence, out, ensure_ascii=False, indent=2)
        out.write('\n')
    raise SystemExit(not outcome.wasSuccessful())
