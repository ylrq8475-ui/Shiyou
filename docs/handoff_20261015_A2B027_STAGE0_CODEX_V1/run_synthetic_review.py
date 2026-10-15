"""Run B's 16 tests plus A's independent tests; all fitting is disabled."""
import argparse
import contextlib
import importlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "sources/B"))
sys.path.insert(0, str(ROOT))
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import sklearn.ensemble, sklearn.preprocessing, sklearn.impute, sklearn.tree, sklearn.decomposition

def forbidden(*args, **kwargs):
    raise AssertionError("A_SIDE_ANY_ACTUAL_MODEL_PREPROCESSING_OR_SVD_FIT_FORBIDDEN")

def main(label=""):
    stream = io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(np.linalg, "svd", side_effect=forbidden))
        patched = set()
        for module in (sklearn.ensemble, sklearn.preprocessing, sklearn.impute, sklearn.tree, sklearn.decomposition):
            for cls in vars(module).values():
                if isinstance(cls, type) and issubclass(cls, BaseEstimator):
                    for name in ("fit", "fit_transform", "partial_fit"):
                        if hasattr(cls, name) and (cls, name) not in patched:
                            stack.enter_context(patch.object(cls, name, forbidden)); patched.add((cls, name))
        for cls in (Pipeline, ColumnTransformer):
            for name in ("fit", "fit_transform"):
                stack.enter_context(patch.object(cls, name, forbidden))
        b_suite = unittest.defaultTestLoader.loadTestsFromName("test_diagnostics")
        a_suite = unittest.defaultTestLoader.loadTestsFromName("test_independent_diagnostics")
        b_count, a_count = b_suite.countTestCases(), a_suite.countTestCases()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite([b_suite, a_suite]))
    payload = {"B_synthetic_cases": b_count, "A_independent_cases": a_count, "total_tests": result.testsRun,
               "passed": result.wasSuccessful(), "failures": len(result.failures), "errors": len(result.errors),
               "actual_model_fits": 0, "actual_preprocessor_fits": 0, "actual_numerical_SVD_calls": 0,
               "F1_scope_test_uses_fixed_stub_basis_not_a_fit": True, "competition_data_read": False,
               "private_markers_read": False, "completed_real_B_entry_not_executed": True}
    suffix = "_" + label if label else ""
    with (ROOT / ("SYNTHETIC_REVIEW_CODEX" + suffix + ".json")).open("x", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2); output.write("\n")
    with (ROOT / ("SYNTHETIC_REVIEW_LOG_CODEX" + suffix + ".txt")).open("x", encoding="utf-8") as output:
        output.write(stream.getvalue())
    print(stream.getvalue())
    print(json.dumps(payload, ensure_ascii=False))
    if not result.wasSuccessful(): raise SystemExit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--run-label", default="")
    main(parser.parse_args().run_label)
