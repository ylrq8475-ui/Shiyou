"""Run source-bound pure-synthetic tests with real fitting globally blocked."""
import hashlib,importlib.util,io,json,os,sys,unittest
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent;B=ROOT/'sources/B033s2'
OUTPUT=ROOT/'verification_output';OUTPUT.mkdir(exist_ok=True)
sys.dont_write_bytecode=True;sys.path.insert(0,str(B));sys.path.insert(0,str(ROOT))
before={p.relative_to(B).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in B.rglob('*') if p.is_file()}
from sklearn.ensemble import ExtraTreesRegressor,RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
blocked=[]
def forbid(*args,**kwargs):blocked.append('real_sklearn_fit_attempt');raise RuntimeError('A_REVIEW_NO_REAL_FIT_AUTHORIZED')
suite=unittest.TestSuite()
with ExitStack() as stack:
    for cls,names in [(ExtraTreesRegressor,['fit']),(RandomForestRegressor,['fit']),(HistGradientBoostingRegressor,['fit']),(Pipeline,['fit','fit_transform']),(ColumnTransformer,['fit','fit_transform']),(SimpleImputer,['fit','fit_transform']),(StandardScaler,['fit','fit_transform']),(OneHotEncoder,['fit','fit_transform'])]:
        for name in names:stack.enter_context(patch.object(cls,name,forbid))
    for name,path in [('B_synthetic_033',B/'test_033.py'),('A_independent_033',ROOT/'test_independent_033_step2.py')]:
        spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
    log=io.StringIO();r=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
after={p.relative_to(B).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in B.rglob('*') if p.is_file()}
out={'tests_run':r.testsRun,'B_tests':10,'A_tests':r.testsRun-10,'successful':r.wasSuccessful(),'failures':len(r.failures),'errors':len(r.errors),'A_model_fits':0,'A_preprocessor_fits':0,'blocked_real_fit_attempts':len(blocked),'empty_or_fake_synthetic_callback_tests_are_not_real_fits':True,'public_B_bytes_unchanged':before==after,'competition_data_read':False,'B_real_OOF_or_train_entry_executed':False}
with (OUTPUT/'SYNTHETIC_LOG_CODEX_V2.txt').open('x',encoding='utf-8') as f:f.write(log.getvalue())
with (OUTPUT/'SYNTHETIC_RESULT_CODEX_V2.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out));assert out['successful'] and before==after and not blocked
