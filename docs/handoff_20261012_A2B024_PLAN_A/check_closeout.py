"""A read-only receipt and pure synthetic review; no training code imported."""
from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE/'bundle'
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*') if p.is_file()}
m=read(ROOT/'BUNDLE_SHA256SUMS.json')['files']
assert set(m)==set(before)-{'BUNDLE_SHA256SUMS.json'}
for n,v in m.items():assert before[n]==v['sha256'] and (ROOT/n).stat().st_size==v['bytes']
receipt=read(ROOT/'RECEIPT_VERIFICATION.json')
original=HERE.parent/'A23_R1_20261012/delivery_A'
assert len(receipt['files'])==20
for n,v in receipt['files'].items():assert sha(original/n)==v['sha256'] and (original/n).stat().st_size==v['bytes']
assert read(ROOT/'A_ROUTE_SIGNAL.json')==read(original/'A_ROUTE_SIGNAL.json')
old_evidence=read(HERE.parent/'A23_R1_20261012/bundle/execution/FINAL_RESULT.json')
derived=read(ROOT/'B_AGGREGATE_EVIDENCE.json')
for old,new in zip(old_evidence['research'],derived['families'],strict=True):
    assert old['seed']==new['seed']
    for a in ['B0','C1']:
        assert old['arms'][a]['official_score']==new[a+'_score']
        assert old['arms'][a]['monthly_official_weighted_loss']==new[a+'_monthly_weighted_loss']
    assert old['arms']['C1']['diagnostics']['prediction_state_groups']['raw_scale_fallback']==new['fallback_group']
logs={}
for name in ['test_route.py','verify_evidence.py']:
    r=subprocess.run([sys.executable,'-E','-B',str(ROOT/name)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=60)
    assert r.returncode==0,(name,r.stdout,r.stderr)
    logs[name]=r.stdout+r.stderr
assert before=={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*') if p.is_file()}
# The difference between two minima does not measure worst paired deterioration.
b=[60.,80.,75.,72.,74.];r=[61.,75.,76.,73.,75.]
min_difference=min(r)-min(b);worst_paired=min(x-y for x,y in zip(r,b))
assert min_difference==1. and worst_paired==-5.
result={'source_commit':'57c78bde28f877212d3a711d92352a299a5f558c','bundle_manifest_files':len(m),
 'A_previous_delivery_hashes_matched':20,'six_families_bound_to_A_received_original_B':True,
 'B_synthetic_tests_executed':19,'B_aggregate_checks_executed':90,'all_passed':True,'received_bundle_unchanged':True,
 'new_model_or_preprocess_fits':0,'new_performance_result':False,'private_training_data_read_for_checks':False,
 'synthetic_worst_fold_counterexample':{'difference_of_minima':min_difference,'minimum_paired_delta':worst_paired},
 'interpretation':'Plan review only. Pure router shape checks do not demonstrate real well/date alignment or integrated training correctness.',
 'logs':logs}
with (HERE/'A_CLOSEOUT_CHECKS.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='logs'},ensure_ascii=False,indent=2))
