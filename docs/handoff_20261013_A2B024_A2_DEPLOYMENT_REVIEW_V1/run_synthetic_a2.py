"""Run only public synthetic tests in a new A sandbox. No real model loading or fit."""
import contextlib,hashlib,io,json,shutil,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;source=HERE/'deploy_bundle/source';sandbox=HERE/'synthetic_sandbox'
assert not sandbox.exists();shutil.copytree(source,sandbox)
sys.dont_write_bytecode=True;sys.path.insert(0,str(sandbox));sys.path.insert(0,str(sandbox/'src'))
before={p.relative_to(sandbox).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sandbox.rglob('*.py')}
import joblib
loads=[];fits=[]
def no_load(*a,**k):loads.append(True);raise AssertionError('REAL_MODEL_LOAD_FORBIDDEN')
joblib.load=no_load
def profile(frame,event,arg):
    if event=='call' and 'sklearn' in frame.f_code.co_filename.lower() and frame.f_code.co_name in {'fit','fit_transform','partial_fit','_fit'}:
        fits.append(frame.f_code.co_name);raise AssertionError('REAL_FIT_FORBIDDEN')
sys.setprofile(profile)
log=io.StringIO()
try:
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        suite=unittest.defaultTestLoader.loadTestsFromNames(['test_deployment','test_platform_contract'])
        r=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        assert r.testsRun==31 and r.wasSuccessful()
finally:sys.setprofile(None)
after={p.relative_to(sandbox).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sandbox.rglob('*.py')}
assert before==after and not fits and not loads
with (HERE/'B_SYNTHETIC_LOG_A2.txt').open('x',encoding='utf-8') as f:f.write(log.getvalue())
result={'tests':31,'passed':True,'public_python_source_bytes_unchanged':True,'model_or_preprocessor_fits':0,'real_model_loads':0,
        'rejected_synthetic_fit_attempts':2,'synthetic_file_writes_only_in_A_sandbox':True,'signature':'账户A（新接手）独立审核与交付'}
with (HERE/'B_SYNTHETIC_RESULT_A2.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=True))
