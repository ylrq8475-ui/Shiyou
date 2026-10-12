"""Read-only synthetic and anonymous evidence review; never fit a model."""
from pathlib import Path
import contextlib, hashlib, importlib, io, json, math, runpy, sys, unittest
HERE=Path(__file__).resolve().parent
B=HERE/'bundle'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {p.name:digest(p) for p in B.iterdir() if p.is_file()}
before=snapshot()
manifest=json.loads((B/'BUNDLE_SHA256SUMS.json').read_bytes())['files']
assert set(manifest)==set(before)-{'BUNDLE_SHA256SUMS.json'}
assert all(before[n]==v['sha256'] for n,v in manifest.items())
for p in (HERE/'received').iterdir():
    if (B/p.name).is_file():assert p.read_bytes()==(B/p.name).read_bytes()
old=HERE.parent/'A23_CLOSEOUT_R1_20261012/bundle'
for n in ['B_AGGREGATE_EVIDENCE.json','A_ROUTE_SIGNAL.json','A_ARITHMETIC_SUMMARY.json','route_core.py','test_route.py','verify_evidence.py']:
    assert (B/n).read_bytes()==(old/n).read_bytes()
sys.path.insert(0,str(B));sys.dont_write_bytecode=True
fit_calls=[]
def guard(frame,event,arg):
    if event=='call' and frame.f_code.co_name in {'fit','fit_transform','partial_fit','_fit'}:
        fit_calls.append(frame.f_code.co_name)
        raise AssertionError('UNAUTHORIZED_FIT')
sys.setprofile(guard)
log=io.StringIO()
try:
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        results=[]
        for module,count in [('test_pretrain_contracts',26),('test_route',19)]:
            suite=unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(module))
            r=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
            assert r.wasSuccessful() and r.testsRun==count
            results.append({'module':module,'tests':r.testsRun,'passed':True})
        runpy.run_path(str(B/'verify_evidence.py'),run_name='__main__')
    from pretrain_contracts import Arm,ExecutionGuard,COMMON_FIELDS,raw_digest,ContractFailure
    # A-authored cross-year and official-score oracle: invented values only.
    raw=(('A_SYNTH_1',0.),('A_SYNTH_2',1.),('A_SYNTH_3',float('nan')))
    months=[202611,202612]+list(range(202701,202711))
    keys=tuple((w,m) for w,x in raw for m in months)
    identity={k:'synthetic_'+k for k in COMMON_FIELDS};identity['raw_state']=raw_digest(raw)
    b=Arm(keys,tuple(float(i+1) for i in range(36)),dict(identity))
    c=Arm(keys,tuple(float(2*i+2) for i in range(36)),dict(identity))
    routed=ExecutionGuard().validate_and_route(b,c,raw,keys,identity)
    assert routed==c.predictions[:12]+b.predictions[12:24]+c.predictions[24:]
    truth=tuple(float(i%7) for i in range(36))
    def loss(pred,w):return sum(2.**(-t-1)*abs(pred[12*w+t]-truth[12*w+t])/(abs(pred[12*w+t])+abs(truth[12*w+t])+1e-6) for t in range(12))
    delta=100*sum(loss(b.predictions,w)-loss(routed,w) for w in range(3))/3
    expected=100*sum(loss(b.predictions,w)-loss(c.predictions,w) for w in (0,2))/3
    assert math.isclose(delta,expected,abs_tol=1e-12)
    assert sum(2.**(-t) for t in range(1,13))==1-2.**-12
    # Complete non-consecutive calendar must fail, even if both arms agree.
    bad=list(keys);bad[1]=(bad[1][0],202610);bad=tuple(bad)
    g=ExecutionGuard()
    try:g.validate_and_route(Arm(bad,b.predictions,identity),Arm(bad,c.predictions,identity),raw,bad,identity)
    except ContractFailure:pass
    else:raise AssertionError('CALENDAR_FAIL_OPEN')
    assert g.blocked
    for stage in ('confirmation','full_fit','save'):
        try:g.assert_stage_allowed(stage)
        except ContractFailure:pass
        else:raise AssertionError('DOWNSTREAM_FAIL_OPEN')
finally:sys.setprofile(None)
assert not fit_calls and snapshot()==before
plan=json.loads((B/'PLAN_R2.json').read_bytes())
assert plan['candidate_count']==1 and not plan['integrated_training_entry_implemented']
assert plan['stages'][2]['minimum_paired_fold_delta_min']==-1
assert sum(s['model_fits'] for s in plan['stages'])==72
assert plan['budgets']['preprocessor_completions_max']==74
output={'source_commit':'1866c13e6872930b9418248a5feaa517401e1711','bundle_manifest_verified':len(manifest),
 'B_synthetic_results':results,'aggregate_checks':90,'A_additional_checks':['cross_year_whole_well_route','independent_official_group_identity','unnormalized_weight_mass','nonconsecutive_calendar_rejection','post_failure_stage_blocking'],
 'all_passed':True,'bundle_unchanged':True,'old_aggregate_source_bytes_match':True,
 'new_model_or_preprocess_fits':0,'new_performance_evidence':False,
 'runtime_implementation_accepted':False,'plan_and_pure_contracts_accepted':True,
 'entry_sha256':{n:before[n] for n in ['pretrain_contracts.py','route_core.py','PLAN_R2.json']},
 'limits':['no actual training entry in bundle','remote seed inventory not independently rescanned','no real-data numerical rerun','no formal submission approval']}
for n,data in [('A_PLAN_CHECKS.json',json.dumps(output,ensure_ascii=False,indent=2)+'\n'),('A_TEST_LOG.txt',log.getvalue())]:
    with (HERE/n).open('x',encoding='utf-8') as f:f.write(data)
print(json.dumps(output,ensure_ascii=False))
