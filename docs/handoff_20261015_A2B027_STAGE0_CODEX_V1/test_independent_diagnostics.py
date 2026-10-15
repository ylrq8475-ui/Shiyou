"""Independent synthetic references. No competition data, model fit or SVD fit."""
import ast
import json
import math
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
import diagnostic_core as b
import privacy_check as privacy

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / "sources/B/run_stage0.py").read_text(encoding="utf-8")


def independent_score(y, p):
    losses = [math.fsum(2.0**(-t) * abs(float(a)-float(c)) /
                       (abs(float(a))+abs(float(c))+0.000001)
                       for t, (a, c) in enumerate(zip(yi, pi), 1)) for yi, pi in zip(y, p)]
    return 100.0 * (1.0 - math.fsum(losses) / len(losses))


def independent_gamma(histories):
    buckets, differences = {}, []
    for history in histories:
        for month in sorted(history):
            if month-1 not in history:
                continue
            a, c = history[month-1], history[month]
            if not (math.isfinite(a) and math.isfinite(c) and a >= 0 and c >= 0):
                continue
            v = math.log(c + 1e-6) - math.log(a + 1e-6)
            differences.append(v)
            buckets.setdefault(month, []).append(v)
    common = {m: math.fsum(v)/len(v) for m, v in buckets.items() if len(v) >= 5}
    def variance(v):
        center = math.fsum(v)/len(v)
        return math.fsum((x-center)**2 for x in v)/len(v)
    pairs = [(common[m-1], common[m]) for m in sorted(common) if m-1 in common]
    left, right = list(zip(*pairs))
    ml, mr = math.fsum(left)/len(left), math.fsum(right)/len(right)
    covariance = math.fsum((x-ml)*(z-mr) for x, z in pairs)
    corr = covariance / math.sqrt(math.fsum((x-ml)**2 for x in left)*math.fsum((z-mr)**2 for z in right))
    return variance(list(common.values()))/variance(differences), corr


def source_fragment(start, stop):
    code = SOURCE[SOURCE.index(start):SOURCE.index(stop)]
    import textwrap
    return compile(textwrap.dedent(code), "<locked-B-synthetic-fragment>", "exec")


class IndependentTests(unittest.TestCase):
    def test_metric_independent_reference(self):
        y = np.arange(1., 49.).reshape(4, 12)
        p = np.flip(y, axis=1).copy(); p[0, 0] = 0.
        self.assertAlmostEqual(b.official_summary(y, p)["official_score"], independent_score(y, p), places=12)

    def test_epsilon_always_added(self):
        y = np.zeros((1, 12)); p = y.copy(); p[0, 0] = 1e-6
        self.assertEqual(b.official_summary(y, p)["official_score"], 75.)

    def test_months_order_not_reversed(self):
        y = np.zeros((1, 12)); first = y.copy(); last = y.copy()
        first[0, 0] = 1.; last[0, 11] = 1.
        l1 = b.official_summary(y, first)["weighted_losses"]["m1_to_12"]
        l12 = b.official_summary(y, last)["weighted_losses"]["m1_to_12"]
        self.assertEqual(l1/l12, 2048.)

    def test_unnormalized_weights(self):
        y = np.zeros((2, 12)); p = np.ones((2, 12))
        self.assertAlmostEqual(b.official_summary(y, p)["weighted_losses"]["m1_to_12"], 4095/4096/(1+1e-6))

    def test_equal_wells_not_fold_mean(self):
        y = np.ones((3, 12)); p = y.copy(); p[0] = 0.
        actual = b.official_summary(y, p)["official_score"]
        wrong = (b.official_summary(y[:1], p[:1])["official_score"] + 100)/2
        self.assertAlmostEqual(actual, independent_score(y, p)); self.assertNotEqual(actual, wrong)

    def test_invalid_targets_and_predictions_rejected(self):
        for v in (np.nan, np.inf, -1.):
            for side in (0, 1):
                arrays = [np.ones((2, 12)), np.ones((2, 12))]
                arrays[side][0, 0] = v
                with self.subTest(v=str(v), side=side), self.assertRaises(b.GateError):
                    b.official_summary(*arrays)

    def test_shape_exact_boundaries_and_zero(self):
        y = np.ones((5, 12)); y[0, 3:6] = 1.11; y[1, 3:6] = .89
        y[2, 3:6] = 1.1; y[3, 3:6] = .9; y[4] = 0.
        self.assertEqual(b.shape_counts(y), {"上升": 1, "下降": 1, "稳产": 3, "含0值": 1})

    def test_projection_matches_manual_known_basis(self):
        mu = np.arange(12)/100; z = np.tile(mu, (3, 1)); z[:, 0] += .4; z[:, 7] += .6
        scale = np.array([1., 2., 3.])
        expected_z = np.tile(mu, (3, 1)); expected_z[:, 0] += .4
        np.testing.assert_allclose(b.project_oracle(z, mu, np.eye(12), scale, 2), np.expm1(expected_z)*scale[:, None])

    def test_projection_clips_after_inverse(self):
        p = b.project_oracle(-np.ones((1, 12)), np.zeros(12), np.eye(12), np.ones(1), 2)
        self.assertTrue((p == 0.).all())

    def test_actual_F1_source_scope_with_stub_not_SVD(self):
        from sklearn.model_selection import GroupKFold
        groups = np.repeat([f"SYNTH_{i:03d}" for i in range(81)], 12)
        y = 1. + (np.arange(972).reshape(81, 12) % 23)/10.
        scale = 1. + np.arange(81)/100
        panel = pd.DataFrame({"WELL_ID": groups, "horizon": np.tile(np.arange(1, 13), 81),
                              "RCYL": y.reshape(-1), "history__RCYL__last": np.repeat(scale, 12)})
        splits = list(GroupKFold(5).split(panel, groups=groups))
        traces, events = [], []
        def svd_stub(values, full_matrices=False):
            # A fixed basis is returned; no decomposition, estimation or fit occurs.
            traces.append(values.copy())
            return np.empty((len(values), 12)), np.arange(12., 0., -1), np.eye(12)
        def score(frame, **kwargs):
            prediction = frame[kwargs["prediction_column"]].to_numpy()
            return SimpleNamespace(total=independent_score(frame.RCYL.to_numpy().reshape(-1, 12), prediction.reshape(-1, 12)))
        namespace = dict(np=np, panel=panel, result={"hard_gates": {}}, splits=splits, counts={"preprocessor_fit_entered": 0, "preprocessor_fit_completed": 0, "preprocessor_fit_failed": 0},
                         store=SimpleNamespace(unchanged=lambda: True), own={}, sha=lambda _: None,
                         event=lambda name, **kwargs: events.append((name, kwargs)), require=b.require,
                         shape_counts=b.shape_counts, project_oracle=b.project_oracle,
                         official_summary=b.official_summary, official_twelve_month_score=score, EPSILON=1e-6)
        with patch.object(np.linalg, "svd", side_effect=svd_stub):
            exec(source_fragment("        # F1: exactly one real", "        result['Dalpha_status']"), namespace)
        self.assertEqual(len(traces), 5)
        for values, (tr, va) in zip(traces, splits):
            trw, vaw = np.unique(tr//12), np.unique(va//12)
            expected = np.log1p(y[trw]/scale[trw, None]); expected -= expected.mean(axis=0)
            np.testing.assert_allclose(values, expected)
            self.assertFalse(set(trw)&set(vaw))
        self.assertEqual(len(namespace["result"]["F1_SVD_records"]), 5)
        self.assertTrue(all(row["K_reuse"] == [1, 2, 3, 4] for row in namespace["result"]["F1_SVD_records"]))
        self.assertEqual(len(events), 10)

    def run_F0_fixture(self, invalid_pre_wells=0, future_value=10.):
        dictionary = json.loads((ROOT / "sources/B/FIELD_DICTIONARY.json").read_bytes())
        plan = json.loads((ROOT / "sources/B/PLAN_STAGE0.json").read_bytes())
        fields = [row[0] for row in dictionary["fields"]]
        rows = []
        for i in range(81):
            for prior in (True, False):
                row = {name: None for name in fields}
                row.update(WELL_ID=f"SYNTH_{i:03d}", NY="2000/01/01" if prior else "2000/03/01",
                           RCYL=5., RCYL1=(0. if i < invalid_pre_wells else 10.) if prior else future_value,
                           YY=3., TY=2., PL=20., BX=50., SXDL=4., XXDL=2., SCTS=10.)
                rows.append(row)
        history = pd.DataFrame(rows)
        pre = pd.Series(np.tile([True, False], 81), index=history.index)
        test = history.iloc[:2].drop(columns="RCYL").copy()
        captured = {}
        namespace = dict(HERE=ROOT / "sources/B", th=history, pre_mask=pre, pd=pd, np=np,
                         period=pd.to_datetime(history.NY).dt.to_period("M"), well="WELL_ID",
                         test=test, test_future=pd.Series([False, True], index=test.index),
                         test_pre=pd.Series([True, False], index=test.index),
                         full_set=set(history.WELL_ID), features=["history__YY__last"], plan=plan,
                         result={}, root=Path("SYNTHETIC_NO_OUTPUT"), json=json,
                         write_new=lambda path, value: captured.update(value), event=lambda *a, **k: None)
        exec(source_fragment("        # F0: official dictionary", "        # D-beta and D-gamma"), namespace)
        return captured

    def test_actual_F0_source_counts_independent_wells_not_rows(self):
        result = self.run_F0_fixture(invalid_pre_wells=1)
        row = result["combinations"][0]
        self.assertEqual(row["valid_complete_wells"], 80)
        self.assertEqual(row["coverage"], 80/81)

    def test_actual_F0_source_excludes_future_observations(self):
        before = self.run_F0_fixture(invalid_pre_wells=1, future_value=10.)
        after = self.run_F0_fixture(invalid_pre_wells=1, future_value=1e8)
        self.assertEqual(before["combinations"], after["combinations"])

    def test_actual_F0_source_exact_80percent_boundary(self):
        self.assertTrue(self.run_F0_fixture(invalid_pre_wells=16)["combinations"][0]["passes"])
        self.assertFalse(self.run_F0_fixture(invalid_pre_wells=17)["combinations"][0]["passes"])

    def test_history_contiguous_segment_end(self):
        self.assertEqual(b.eligible_segment_ends([15, 2, 1, 2, 16, 30]), [2, 16, 30])

    def test_history_gap_missing_nonfinite_negative(self):
        for bad in (None, np.nan, np.inf, -1.):
            values = {m: 1. for m in range(1, 40)}
            if bad is None: del values[8]
            else: values[8] = bad
            result = b.historical_event_counts(values, [1, 30], 30)
            self.assertEqual(result["qualified_events"], 0)
            self.assertEqual(result["rejected_nonconsecutive_or_missing"], 1)

    def test_history_refraction_inside_window(self):
        result = b.historical_event_counts({m: 1. for m in range(1, 60)}, [1, 2, 10, 40], 40)
        self.assertEqual(result["qualified_events"], 1)
        self.assertEqual(result["rejected_refracture"], 1)

    def test_history_cross_year_integer_calendar(self):
        start = 1200
        result = b.historical_event_counts({m: 1. for m in range(start, start+40)}, [start, start+30], start+30)
        self.assertEqual(result["new_m1_labels"], 1)
        self.assertEqual(result["new_m2_labels"], 1)

    def test_alpha_fold_labels_do_not_enter_current_choice(self):
        y = np.arange(1., 121.).reshape(10, 12); p = np.ones((10, 12)); folds = np.repeat(np.arange(5), 2)
        original, _ = b.cross_residual_adjust(y, p, folds)
        changed = y.copy(); changed[:2] *= 1e4
        other, _ = b.cross_residual_adjust(changed, p, folds)
        np.testing.assert_array_equal(original[:2], other[:2])

    def test_alpha_horizon_not_mixed(self):
        y = np.arange(1., 121.).reshape(10, 12); p = np.ones((10, 12)); folds = np.repeat(np.arange(5), 2)
        original, _ = b.cross_residual_adjust(y, p, folds)
        changed = y.copy(); changed[2:, 1] *= 100
        other, _ = b.cross_residual_adjust(changed, p, folds)
        np.testing.assert_array_equal(original[:2, 0], other[:2, 0])

    def test_alpha_candidates_and_loss_reference(self):
        y = 1. + np.arange(120.).reshape(10, 12)/7; p = 2.*np.ones((10, 12)); folds = np.repeat(np.arange(5), 2)
        actual, _ = b.cross_residual_adjust(y, p, folds)
        outcomes = [p[0, 0]*(y[j, 0]+1e-6)/(p[j, 0]+1e-6) for j in range(2, 10)]
        candidates = [0.] + outcomes
        expected = min(enumerate(candidates), key=lambda cv: (math.fsum(abs(cv[1]-v)/(cv[1]+v+1e-6) for v in outcomes), cv[0]))[1]
        self.assertAlmostEqual(actual[0, 0], expected)

    def test_gamma_independent_variance_and_autocorrelation(self):
        histories = [{m: float(np.exp((m%4)*.17 + i*.01*m)) for m in range(1, 10)} for i in range(6)]
        actual = b.lagged_common_trend(histories); share, corr = independent_gamma(histories)
        self.assertAlmostEqual(actual["Dgamma_share"], share, places=12)
        self.assertAlmostEqual(actual["Dgamma_lag1"], corr, places=12)

    def test_gamma_fewer_than_five_excluded(self):
        histories = [{m: float(np.exp((m%3)*.2)) for m in range(1, 9)} for _ in range(4)]
        with self.assertRaises(b.GateError): b.lagged_common_trend(histories)

    def test_gamma_calendar_gaps_not_compressed(self):
        histories = [{m: float(np.exp((m%3)*.2+i*.02)) for m in (1, 2, 3, 5, 6, 7, 8)} for i in range(5)]
        actual = b.lagged_common_trend(histories)
        self.assertEqual(actual["valid_well_month_differences"], 25)
        self.assertEqual(actual["adjacent_common_month_pairs"], 3)

    def test_F1_gray_zone_and_K4_not_threshold(self):
        source = json.loads((ROOT / "sources/B/RESULT_A2B027_STAGE0.json").read_bytes())
        source.update(F1_oracle_K1=80., F1_oracle_K2=84., F1_oracle_K3=88., F1_oracle_K4=99.)
        choice = b.decisions(source)["F1"]
        self.assertFalse(choice["passed"]); self.assertFalse(choice["route_2_rejected"])

    def test_missing_Dalpha_remains_unknown(self):
        source = json.loads((ROOT / "sources/B/RESULT_A2B027_STAGE0.json").read_bytes())
        self.assertIsNone(b.decisions(source)["D-α"]["passed"])

    def test_exact_decision_boundaries(self):
        source = dict(F0_combo_pass_count=1, F1_oracle_K1=90., F1_oracle_K2=90., F1_oracle_K3=90.,
                      Dalpha_delta=1., Dbeta_increase_m1=.3, Dbeta_increase_m2=0., Dgamma_share=.3, Dgamma_lag1=.5)
        self.assertTrue(all(row["passed"] for row in b.decisions(source).values()))

    def test_privacy_synthetic_positive_and_negative(self):
        markers = {"well": {"SYNTH_ONLY_WELL"}, "date": {"SYNTH_ONLY_DATE"}, "month": {"SYNTH_ONLY_MONTH"}, "candidate": {"SYNTH_ONLY_CANDIDATE"}}
        self.assertEqual(privacy.scan(b"anonymous aggregate", markers)["result"], "PASS")
        for token in ("SYNTH_ONLY_WELL", "SYNTH_ONLY_DATE", "SYNTH_ONLY_MONTH", "SYNTH_ONLY_CANDIDATE"):
            with self.subTest(token=token), self.assertRaises(AssertionError): privacy.scan(token.encode(), markers)

    def test_entry_does_not_call_Dalpha_or_estimator_fit(self):
        tree = ast.parse(SOURCE)
        called = [node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else "" for node in ast.walk(tree) if isinstance(node, ast.Call)]
        self.assertNotIn("cross_residual_adjust", called)
        self.assertNotIn("fit", called)
        self.assertIn("svd", called)


if __name__ == "__main__":
    unittest.main(verbosity=2)
