import numpy as np

from oil_uplift.ts_blend import VARIANTS, _runs, _ts_features


def test_runs_merge_consecutive_months():
    assert _runs(np.array([0, 1, 1, 0, 1, 0, 0, 1], dtype=bool)) == [[1, 2], [4, 4], [7, 7]]


def _grid(n=30):
    rng = np.random.default_rng(0)
    grid = {c: rng.uniform(1, 5, n) for c in ["RCYL", "SCTS", "HS", "RCYL1", "YY", "TY", "PL", "BJ", "CC"]}
    grid.update({"o0": 0, "n": n, "runs": [[10, 11], [20, 20]]})
    return grid


def test_ts_features_ignore_months_after_last_observed():
    grid = _grid()
    before, level = _ts_features(grid, 18, 1)
    grid["RCYL"][19:] = 1000.0
    grid["HS"][19:] = -5.0
    after, level_after = _ts_features(grid, 18, 1)
    assert level == level_after
    assert all((np.isnan(before[k]) and np.isnan(after[k])) or before[k] == after[k] for k in before)


def test_ts_features_event_context_uses_anchor_in_gap():
    features, _ = _ts_features(_grid(), 19, 1)
    assert features["n_runs"] == 2 and features["since_end"] == 0 and features["run_len"] == 1


def test_variant_weights_are_valid():
    from oil_uplift.ts_blend import LEAN_WEIGHT
    for name, (tree_w, ts_w, multiplier) in VARIANTS.items():
        assert abs(tree_w + ts_w + LEAN_WEIGHT.get(name, 0.0) - 1.0) < 1e-12 and multiplier > 0
