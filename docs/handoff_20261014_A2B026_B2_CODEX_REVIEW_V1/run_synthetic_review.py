"""Run B's 19 tests plus A's synthetic tests with real fitting forbidden."""
import contextlib, importlib, importlib.metadata, io, json, os, sys, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'sources/B'),str(ROOT/'sources/project_src'),str(ROOT)]
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[key]='1'
blocked=[]
def forbidden(*args,**kwargs):
    blocked.append('REAL_ESTIMATOR_FIT_ATTEMPT');raise AssertionError('Real fitting forbidden in A synthetic audit')
suite=unittest.TestSuite()
for name in ['test_route_b','test_runner_faults','test_independent_b2']:
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name)))
log=io.StringIO()
with contextlib.ExitStack() as guard:
    for target in ['sklearn.ensemble.ExtraTreesRegressor.fit','sklearn.ensemble.ExtraTreesClassifier.fit','sklearn.compose.ColumnTransformer.fit','sklearn.compose.ColumnTransformer.fit_transform','sklearn.pipeline.Pipeline.fit']:
        guard.enter_context(patch(target,side_effect=forbidden))
    outcome=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
evidence={'B_existing_tests':19,'A_additional_tests':outcome.testsRun-19,'tests_run':outcome.testsRun,'failures':len(outcome.failures),'errors':len(outcome.errors),'passed':outcome.wasSuccessful(),'real_fit_attempts':len(blocked),'actual_model_fits':0,'actual_preprocessor_fits':0,'real_data_read':False,'scope':'B numeric and actual-runner function probes plus independent math/calendar/privacy synthetic checks; not a real-data retraining or full failure-run reproduction','A_runtime':{'python':sys.version.split()[0],'versions':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scikit-learn','PyYAML']}}}
with (ROOT/'SYNTHETIC_REVIEW_CODEX.json').open('x',encoding='utf-8') as out:json.dump(evidence,out,ensure_ascii=False,indent=2);out.write('\n')
with (ROOT/'SYNTHETIC_REVIEW_LOG_CODEX.txt').open('x',encoding='utf-8') as out:out.write(log.getvalue())
print(json.dumps(evidence,ensure_ascii=False));print(log.getvalue())
raise SystemExit(not outcome.wasSuccessful())
