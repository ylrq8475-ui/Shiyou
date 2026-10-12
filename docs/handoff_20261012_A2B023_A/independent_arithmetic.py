"""A-authored checks of published anonymous evidence; no fitting or raw targets."""
from pathlib import Path
from collections import Counter
from datetime import datetime
import hashlib, importlib.util, json, math, statistics
HERE=Path(__file__).resolve().parent;ROOT=HERE/'bundle'
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(ok,label):
    checks.append({'check':label,'passed':bool(ok)})
    if not ok:raise AssertionError(label)
def same(a,b,label):check(math.isclose(a,b,abs_tol=1e-10,rel_tol=0),label)
manifest=read(ROOT/'BUNDLE_MANIFEST.json')['files']
check(set(manifest)=={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}-{'BUNDLE_MANIFEST.json'},'exact_manifest_coverage')
for n,v in manifest.items():check(sha(ROOT/n)==v['sha256'],'hash:'+n)
lock=read(ROOT/'execution/IMPLEMENTATION_PRETRAIN_LOCK.json')
for item in read(ROOT/'PROVIDED_PRETRAIN_BINDINGS.json')['bindings']:
    h=sha(ROOT/item['package_path'])
    check(h==item['pretrain_source_sha256'] and h in lock['source_and_inputs'].values(),'actual_prefit_binding:'+item['package_path'])
events=[read(p) for p in sorted((ROOT/'execution/events').glob('*.json'))]
check(Counter(e['event'] for e in events)=={'model_fit_entered':60,'fit_completed':60,'fold_completed':30},'150_event_counts')
check(datetime.fromisoformat(read(ROOT/'runtime/SYNTHETIC_TEST_RESULTS.json')['sealed_at'])<datetime.fromisoformat(lock['locked_at'])<datetime.fromisoformat(events[0]['time']),'synthetic_lock_fit_order')
seeds=[None,20260917,20261031,20261219,20270107,20270303]
expected={(s,f,a) for s in seeds for f in range(1,6) for a in ['B0','C1']}
for event in ['model_fit_entered','fit_completed']:
    selected=[e for e in events if e['event']==event]
    check({(e['tag']['seed'],e['tag']['fold'],e['tag']['arm']) for e in selected}==expected,event+'_exact_queue')
    check(all(e['tag']['phase']=='CV' for e in selected),event+'_no_other_phase')
for e in events:
    if e['event']=='model_fit_entered':
        check(e['training_rows']==12*e['training_wells'] and e['training_wells'] in [64,65],'training_scope')
    elif e['event']=='fold_completed':
        check(e['well_intersection']==0 and e['train_wells']+e['valid_wells']==81,'isolation_claim')
families=[read(ROOT/'execution'/('FIXED_FIVE_FOLD.json' if s is None else f'REPEAT_{s}.json')) for s in seeds]
group_keys=['raw_scale_fallback','positive_scale_training_q25_low','other_positive_scale']
group_results={k:{'seed_net_score_deltas':[],'seed_group_score_deltas':[],'seed_early_net_score_deltas':[],'wells':[]} for k in group_keys}
for i,r in enumerate(families):
    fold_events=[e for e in events if e['event']=='fold_completed' and e['seed']==seeds[i]]
    b,c=r['arms']['B0'],r['arms']['C1']
    for a in ['B0','C1']:
        v=r['arms'][a];w=v['monthly_official_weighted_loss']
        check(v['well_count']==81 and len(w)==12,'cohort_and_horizons')
        same(v['official_score'],100*(1-math.fsum(w)),'official_score')
        for t,(raw,weighted) in enumerate(zip(v['monthly_unweighted_relative_error'],w),1):same(raw/2**t,weighted,'month_weight')
        for h in [1,2,4,12]:same(math.fsum(w[:h]),v['official_weighted_prefix_loss'][str(h)],'prefix')
        same(sum(e['valid_wells']*e['scores'][a] for e in fold_events)/81,v['official_score'],'equal_well_unequal_fold')
        same(statistics.pstdev(v['fold_scores']),v['fold_std_ddof0'],'ddof0')
    same(c['official_score']-b['official_score'],c['delta_vs_B0'],'paired_delta')
    contribution=[];counts=[]
    for k in group_keys:
        bg=b['diagnostics']['prediction_state_groups'][k];cg=c['diagnostics']['prediction_state_groups'][k]
        check(bg['status']==cg['status']=='RELEASED' and bg['group_wells']==cg['group_wells'],'group_pairing')
        n=bg['group_wells'];counts.append(n)
        net=100*n/81*(bg['full_mean_weighted_loss']-cg['full_mean_weighted_loss'])
        same(net,-100*cg['net_loss_change_contribution_all_wells'],'group_contribution')
        contribution.append(net)
        if i:
            g=group_results[k];g['seed_net_score_deltas'].append(net);g['wells'].append(n)
            g['seed_group_score_deltas'].append(cg['score_delta_vs_B0_in_group'])
            g['seed_early_net_score_deltas'].append(-100*cg['early_net_loss_change_contribution_all_wells'])
    check(sum(counts)==81,'group_partition');same(math.fsum(contribution),c['delta_vs_B0'],'group_sum')
for g in group_results.values():
    g['mean_net_score_delta']=statistics.mean(g['seed_net_score_deltas'])
    g['positive_seeds']=sum(x>0 for x in g['seed_net_score_deltas'])
    g['mean_group_score_delta']=statistics.mean(g['seed_group_score_deltas'])
    g['mean_early_net_score_delta']=statistics.mean(g['seed_early_net_score_deltas'])
comparison=read(ROOT/'MODEL_COMPARISON.json')
deltas=[r['arms']['C1']['delta_vs_B0'] for r in families[1:]]
same(statistics.mean(deltas),comparison['gate']['repeat_mean_delta'],'repeat_mean')
check(all(d<0 for d in deltas),'five_negative_seeds')
check(comparison['gate']['passed'] is False,'gate_fail')
final=read(ROOT/'execution/FINAL_RESULT.json')
check(final['artifacts']=={} and final['budget']['model_completed']==60,'no_retention_or_confirmation_fits')
# A pure-Python metric oracle, independent of B.
def official(rows,pred):
    if len(rows)!=len(pred):raise ValueError('length')
    wells={}
    for (well,t,y),p in zip(rows,pred,strict=True):
        if isinstance(t,bool) or not isinstance(t,int) or not 1<=t<=12:raise ValueError('month')
        if not all(math.isfinite(float(v)) and v>=0 for v in [y,p]):raise ValueError('value')
        item=wells.setdefault(well,{})
        if t in item:raise ValueError('duplicate')
        item[t]=abs(p-y)/(abs(p)+abs(y)+1e-6)/2**t
    if not wells or any(set(v)!=set(range(1,13)) for v in wells.values()):raise ValueError('window')
    return 100*(1-statistics.mean(math.fsum(v.values()) for v in wells.values()))
from types import SimpleNamespace
a=SimpleNamespace(official=official)
rows=[('SYNTHETIC_A',t,1.) for t in range(1,13)]
same(a.official(rows,[1.]*12),100.,'synthetic_perfect')
p=[1.]*12;p[0]=0.
same(a.official(rows,p),100*(1-.5/1.000001),'synthetic_first_month_epsilon')
same(a.official(rows,[0.]*12),100*(1-(1-2**-12)/1.000001),'synthetic_unnormalized')
same(a.official(rows+[(w.replace('A','B'),t,y) for w,t,y in rows],[1.]*12+[0.]*12),(100+a.official(rows,[0.]*12))/2,'synthetic_equal_well')
spec=importlib.util.spec_from_file_location('b_core',ROOT/'upstream/a2b021/experiment_core.py')
bc=importlib.util.module_from_spec(spec);spec.loader.exec_module(bc)
import pandas as pd
for p in [[1.]*12,[0.]*12,[.5,2.]*6]:
    same(bc.score_summary(pd.DataFrame(rows,columns=['WELL_ID','horizon','RCYL']),p)['official_score'],a.official(rows,p),'A_B_synthetic_metric')
for invalid in [float('nan'),float('inf'),-1.]:
    try:a.official(rows,[invalid]+[1.]*11)
    except ValueError:check(True,'invalid_prediction_rejected')
    else:check(False,'invalid_prediction_accepted')
result={'source_commit':'4ea326798ca1da0736cde4bc41f33b7ff8b58cf9','check_count':len(checks),'all_passed':True,'provided_prefit_bindings':48,'model_fits_by_A':0,
 'scope':'A independent aggregate arithmetic and synthetic metric; real fits and raw-window reconstruction NOT performed',
 'private_or_historical_unprovided_evidence':'UNKNOWN; B integrity reports not independently verified on remote machine',
 'fixed_delta':families[0]['arms']['C1']['delta_vs_B0'],'repeat_mean_delta':statistics.mean(deltas),'group_findings':group_results,
 'fixed_bad_folds':sum(x<0 for x in families[0]['arms']['C1']['paired_fold_deltas']),
 'fixed_months_worsened':sum(c>b for c,b in zip(families[0]['arms']['C1']['monthly_official_weighted_loss'],families[0]['arms']['B0']['monthly_official_weighted_loss'])),
 'repeat_months_worsened':sum(sum(r['arms']['C1']['monthly_official_weighted_loss'][t] for r in families[1:])>sum(r['arms']['B0']['monthly_official_weighted_loss'][t] for r in families[1:]) for t in range(12)),
 'checks':checks}
with (HERE/'A_INDEPENDENT_ARITHMETIC.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2))
