"""Run received synthetic/aggregate entry with independent no-fit guard."""
from pathlib import Path
import contextlib, hashlib, importlib.util, io, json, sys
HERE=Path(__file__).resolve().parent; ROOT=HERE/'bundle'
before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file()}
blocked=[]
def guard(frame,event,arg):
    if event=='call' and frame.f_globals.get('__name__','').startswith('sklearn.') and frame.f_code.co_name in {'fit','fit_transform','partial_fit','_fit'}:
        blocked.append(frame.f_globals.get('__name__','')+'.'+frame.f_code.co_name)
        raise RuntimeError('A_FORBIDS_ESTIMATOR_FIT')
spec=importlib.util.spec_from_file_location('b_readonly',ROOT/'review_only.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
stream=io.StringIO();sys.setprofile(guard)
try:
    with contextlib.redirect_stdout(stream):review.main(ROOT)
finally:sys.setprofile(None)
after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file()}
assert before==after
result=json.loads(stream.getvalue());result.update(A_no_fit_guard_triggered=blocked,A_bundle_unchanged=True,scope='Independent execution of B synthetic and aggregate checks, not real retraining')
with (HERE/'A_READONLY_CHECKS.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
