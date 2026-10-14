"""Run unmodified reference tests on synthetic inputs; never import B's real entry."""
import hashlib, io, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'sources/reference/reference'
sys.dont_write_bytecode=True
sys.path.insert(0,str(SOURCE))
attempts=[]
def guard(frame,event,arg):
    if event=='call' and frame.f_code.co_name in {'fit','fit_transform','partial_fit'}:
        attempts.append(frame.f_code.co_name)
        raise RuntimeError('FITTING_FORBIDDEN_IN_CODEX_REVIEW')
sys.setprofile(guard)
try:
    suite=unittest.defaultTestLoader.loadTestsFromName('test_diagnostics_reference')
    log=io.StringIO()
    outcome=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
finally:
    sys.setprofile(None)
result={'account':'Codex（账户A2）独立审核','tests_run':outcome.testsRun,
        'passed':outcome.wasSuccessful(),'failures':len(outcome.failures),'errors':len(outcome.errors),
        'fit_attempts':len(attempts),'competition_data_read':False,'B_real_entry_executed':False,
        'reference_sha256':hashlib.sha256((SOURCE/'diagnostics_reference.py').read_bytes()).hexdigest(),
        'test_sha256':hashlib.sha256((SOURCE/'test_diagnostics_reference.py').read_bytes()).hexdigest()}
for name,payload in [('SYNTHETIC_REVIEW_LOG.txt',log.getvalue()),('SYNTHETIC_REVIEW_CODEX.json',json.dumps(result,ensure_ascii=False,indent=2))]:
    with (ROOT/name).open('x',encoding='utf-8') as out: out.write(payload)
print(json.dumps(result,ensure_ascii=False))
if not result['passed'] or result['tests_run']!=12 or attempts: raise SystemExit(1)
