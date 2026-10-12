"""Account A successor: independently written, standard-library-only audit.

Inputs are public anonymous aggregates and event records, never private rows.
No experiment module is imported. This does not reconstruct per-well OOF.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

SIGNATURE = '账户A（替代接手）独立审核与交付'
TOL = 1e-10

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_bytes())
def mean(xs): return math.fsum(xs) / len(xs)
def official_score(truth, pred):
    """Independent full formula for invented matrices only, equal weight per well."""
    if not truth or len(truth) != len(pred): raise ValueError('well shape')
    losses=[]
    for y,p in zip(truth,pred,strict=True):
        if len(y)!=12 or len(p)!=12: raise ValueError('twelve months required')
        if any(not math.isfinite(v) or v<0 for v in [*y,*p]): raise ValueError('invalid value')
        losses.append(math.fsum(abs(a-b)/(abs(a)+abs(b)+1e-6)/2**t
                                for t,(a,b) in enumerate(zip(y,p,strict=True),1)))
    return 100*(1-mean(losses))

class Audit:
    def __init__(self): self.n=0; self.max_error=0.; self.errors=[]
    def check(self,ok,label):
        self.n+=1
        if not ok: self.errors.append(label)
    def near(self,a,b,label):
        error=abs(a-b); self.max_error=max(self.max_error,error)
        self.check(math.isfinite(a) and math.isfinite(b) and error<=TOL,label)

def run(root):
    a=Audit(); result=read(root/'evidence/FINAL_RESULT.json'); lock=read(root/'evidence/IMPLEMENTATION_PRETRAIN_LOCK.json')
    plan=read(root/'PLAN_R2.json'); manifest=read(root/'BUNDLE_SHA256SUMS.json')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    a.check(actual==set(manifest)|{'BUNDLE_SHA256SUMS.json'},'bundle exact member set')
    for name,digest in manifest.items(): a.check(sha(root/name)==digest,'bundle sha '+name)
    inner=read(root/'evidence/SHA256SUMS.json')
    for name,digest in inner.items(): a.check(sha(root/'evidence'/name)==digest,'execution sha '+name)
    bindings=read(root/'RUNTIME_SOURCE_BINDINGS.json'); locked_values=set(lock['source_inputs'].values())
    for name,rec in bindings.items():
        a.check(sha(root/name)==rec['sha256'],'source bytes '+name)
        a.check(rec['sha256'] in locked_values,'source prefit binding '+name)
    a.check(sha(root/'PLAN_R2.json')==lock['plan_sha256']=='f77e2dd7e66697e428806c514cabdc4a780ab3b18aac85867b66606eead00804','plan identity')
    a.check(sha(root/'USER_AUTHORIZATION.md')==lock['user_authorization_sha256'],'authorization identity')
    a.check(len(lock['feature_order'])==325 and len(set(lock['feature_order']))==325,'325 unique features')
    a.check([x[0] for x in lock['ordered_dtypes']]==lock['feature_order'],'dtype order')
    for key,val in [('feature_order_sha256',lock['feature_order']),('feature_dtype_sha256',lock['ordered_dtypes'])]:
        digest=hashlib.sha256(json.dumps(val,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        a.check(lock['panel_identity'][key]==digest,'panel '+key)
    a.check(lock['history_dtype']=='UNKNOWN' and result['historical_dtype']=='UNKNOWN','historical dtype remains UNKNOWN')
    a.check(lock['parallelism']==dict(active_models=1,n_jobs=-1,BLAS_OpenMP=1),'parallelism record')
    a.check(lock['model_parameters']['n_estimators']==400 and lock['model_parameters']['min_samples_leaf']==6 and lock['model_parameters']['max_features']==.75 and lock['model_parameters']['random_state']==20260916,'model parameters')
    a.check(len(lock['environment']['versions'])==21,'21 dependency versions recorded')
    events=[read(p) for p in sorted((root/'evidence/events').glob('*.json'))]
    a.check(len(events)==175,'175 events')
    a.check([p.name for p in sorted((root/'evidence/events').glob('*.json'))]==[f'{i:04d}.json' for i in range(1,176)],'event contiguous numbering')
    prev=datetime.fromisoformat(lock['time']); entered=completed=0; stages=Counter(); seen=set(); active=None; fold_counts={}; fold_scores={}
    for e in events:
        t=datetime.fromisoformat(e['time']); a.check(t>=prev,'event monotonic'); prev=t
        stage,seed,fold=e['stage'],e['seed'],e['fold']; key=(stage,seed,fold)
        if stage=='five_later_splits': a.check(stages['fixed_replay']==10,'later preceded by fixed completion')
        if stage=='conditional_confirmation': a.check(stages['fixed_replay']==10 and stages['five_later_splits']==50,'confirmation preceded by research completion')
        if e['event']=='model_entered':
            item=(*key,e['arm']); a.check(active is None and item not in seen,'single new model identity')
            active=item; entered+=1; a.check(e['train_rows']==12*e['train_wells'],'train twelve rows per well')
            n=81-e['train_wells']; a.check(n in (16,17),'validation fold well count')
            if key in fold_counts: a.check(fold_counts[key]==n,'paired arms train same well count')
            fold_counts[key]=n
        elif e['event']=='fit_completed':
            item=(*key,e['arm']); a.check(active==item,'entry completion pairing'); seen.add(item); active=None
            completed+=1; stages[stage]+=1
        elif e['event']=='fold_completed':
            a.check(active is None and all((*key,arm) in seen for arm in ('B0','C1')),'fold follows both arms')
            a.check(e['well_intersection']==0,'recorded well isolation'); fold_scores[key]=e['scores']
        else: a.check(False,'unexpected failure or other event')
        expected=dict(attempts=entered,retries=0,prep_entered=entered,prep_completed=entered,model_entered=entered,model_completed=completed)
        for k,v in expected.items(): a.check(e['budget'][k]==v,'event counter '+k)
        for s in ('fixed_replay','five_later_splits','conditional_confirmation','conditional_private_full_fit'):
            a.check(e['budget']['stage_successes'][s]==stages[s],'event stage '+s)
    a.check(prev<=datetime.fromisoformat(result['finished']),'events before finish')
    a.check(active is None and len(seen)==70 and entered==completed==70,'70 distinct completed entries')
    a.check(stages==Counter(fixed_replay=10,five_later_splits=50,conditional_confirmation=10),'stage exact totals')
    a.check(events[-1]['budget']==result['budget'],'final budget matches final event')
    caps=plan['budgets']
    for key,cap in [('model_completed','total_model_successes_max'),('model_entered','total_model_entries_max'),('attempts','pipeline_attempts_max'),('prep_entered','preprocessor_entries_max'),('prep_completed','preprocessor_completions_max'),('retries','failure_retries_max')]:
        a.check(result['budget'][key]<=caps[cap],'budget cap '+key)
    families=[*result['research'],result['confirmation']]; computed=[]
    expected_seeds=[None,20261012,20261013,20261014,20261015,20261016,20271012]
    a.check([r['seed'] for r in families]==expected_seeds,'seven locked seeds')
    for idx,r in enumerate(families):
        prefix='FIXED_REPLAY.json' if r['seed'] is None else f"SPLIT_{r['seed']}.json"
        a.check(read(root/'evidence'/prefix)==r,'standalone family identical')
        a.check(lock['families'][idx]['seed']==r['seed'] and lock['families'][idx]['split_sha256']==r['split_sha256'],'split lock binding')
        sizes=[fold_counts[(r['stage'],r['seed'],fold)] for fold in range(1,6)]
        a.check(sum(sizes)==81,'81 validation wells'); arms={}
        for name,s in r['arms'].items():
            a.check(s['well_count']==81,'equal well count')
            monthly=[v/2**t for t,v in enumerate(s['monthly_unweighted_relative_error'],1)]
            a.check(len(monthly)==12,'12 monthly errors')
            for j,(x,y) in enumerate(zip(monthly,s['monthly_official_weighted_loss'],strict=True)): a.near(x,y,f'{idx} {name} month {j}')
            prefixes={str(n):math.fsum(monthly[:n]) for n in (1,2,4,12)}
            for n,v in prefixes.items(): a.near(v,s['official_weighted_prefix_loss'][n],'prefix '+n)
            score=100*(1-prefixes['12']); a.near(score,s['official_score'],'total from month errors')
            folds=[fold_scores[(r['stage'],r['seed'],f)][name] for f in range(1,6)]
            for x,y in zip(folds,s['fold_scores'],strict=True): a.near(x,y,'journal fold score')
            weighted=math.fsum(n*v for n,v in zip(sizes,folds,strict=True))/81
            a.near(weighted,score,'unequal folds well weighted total')
            std=math.sqrt(mean([(x-mean(folds))**2 for x in folds])); a.near(std,s['fold_std_ddof0'],'ddof0'); a.near(min(folds),s['worst_fold'],'minimum fold')
            groups=s['diagnostics']['prediction_state_groups']; base_groups=r['arms']['B0']['diagnostics']['prediction_state_groups']
            a.check(sum(g['group_wells'] for g in groups.values())==81,'disjoint state counts')
            a.near(math.fsum(g['group_wells']*g['full_mean_weighted_loss'] for g in groups.values())/81,prefixes['12'],'state loss recombination')
            a.near(math.fsum(g['group_wells']*g['early_mean_weighted_loss'] for g in groups.values())/81,prefixes['2'],'state first2 recombination')
            for key,g in groups.items():
                bg=base_groups[key]; count=g['group_wells']; a.check(count==bg['group_wells'],'paired state sizes')
                a.check(count+g['complement_wells']==81,'state complements')
                delta=100*(bg['full_mean_weighted_loss']-g['full_mean_weighted_loss'])
                a.near(delta,g['score_delta_vs_B0_in_group'],'group internal delta')
                a.near(-delta*count/8100,g['net_loss_change_contribution_all_wells'],'net contribution sign and population')
                a.near((g['early_mean_weighted_loss']-bg['early_mean_weighted_loss'])*count/81,g['early_net_loss_change_contribution_all_wells'],'early net contribution')
                if name=='R1' and key!='raw_scale_fallback': a.near(delta,0.,'positive group unchanged aggregate')
            for j,v in enumerate(s['diagnostics']['monthly_net_weighted_loss_change_vs_B0']):
                a.near(v,monthly[j]-r['arms']['B0']['monthly_official_weighted_loss'][j],'monthly delta identity')
            arms[name]=dict(score=score,monthly_weighted_loss=monthly,prefix_loss=prefixes,fold_scores=folds,fold_std_ddof0=std,min_fold=min(folds),well_weighted_fold_score=weighted,unweighted_fold_mean=mean(folds),unweighted_fold_mean_error=mean(folds)-score)
        b0,rr=arms['B0'],arms['R1']; delta=rr['score']-b0['score']; early=100*(b0['prefix_loss']['2']-rr['prefix_loss']['2'])
        minima=min(rr['fold_scores'])-min(b0['fold_scores']); paired=[x-y for x,y in zip(rr['fold_scores'],b0['fold_scores'],strict=True)]
        a.near(delta,r['delta_vs_B0'],'total delta'); a.near(early,r['first2_score_delta'],'first2 delta')
        a.near(minima,r['fold_risk']['difference_of_minima'],'difference of minima'); a.near(min(paired),r['fold_risk']['minimum_paired_fold_delta'],'minimum paired delta')
        for x,y in zip(paired,r['paired_fold_deltas'],strict=True): a.near(x,y,'paired fold delta')
        cid=r['contribution_identity']; fb=r['arms']['R1']['diagnostics']['prediction_state_groups']['raw_scale_fallback']
        a.check(fb['group_wells']==cid['fallback_well_count']==14,'14 fallback wells')
        a.near(delta,fb['score_delta_vs_B0_in_group']*14/81,'fallback contribution annual')
        a.near(early,-100*fb['early_net_loss_change_contribution_all_wells'],'fallback contribution first2')
        for j,v in enumerate(cid['monthly_score_delta']): a.near(v,100*(b0['monthly_weighted_loss'][j]-rr['monthly_weighted_loss'][j]),'monthly contribution vector')
        a.near(delta,math.fsum(cid['monthly_score_delta']),'annual from monthly delta'); a.near(delta,cid['annual_score_delta'],'annual contribution record')
        c1fb=r['arms']['C1']['diagnostics']['prediction_state_groups']['raw_scale_fallback']
        for k in ('full_mean_weighted_loss','early_mean_weighted_loss','score_delta_vs_B0_in_group'): a.near(fb[k],c1fb[k],'routed fallback C1 aggregate '+k)
        computed.append(dict(seed=r['seed'],stage=r['stage'],validation_well_counts=sizes,arms=arms,delta=delta,first2_delta=early,difference_of_minima=minima,minimum_paired_delta=min(paired),paired_fold_deltas=paired,fallback_group_delta=fb['score_delta_vs_B0_in_group'],fallback_net_score_contribution=fb['score_delta_vs_B0_in_group']*14/81))
    f,c=computed[0],computed[-1]; later=computed[1:6]
    fixed_checks=dict(structure=families[0]['structure_passed'],total=f['delta']>=plan['stages'][0]['score_delta_min'],first2=f['first2_delta']>=plan['stages'][0]['first2_score_delta_min'],difference_of_minima=f['difference_of_minima']>=-1)
    conf_checks=dict(structure=families[-1]['structure_passed'],total=c['delta']>=.2,first2=c['first2_delta']>=0,difference_of_minima=c['difference_of_minima']>=-1,minimum_paired_fold_delta=c['minimum_paired_delta']>=-1)
    summary=dict(mean_delta=mean([r['delta'] for r in later]),strict_positive_count=sum(r['delta']>0 for r in later),min_group_delta=min(r['delta'] for r in later),mean_first2_delta=mean([r['first2_delta'] for r in later]),nonnegative_first2_count=sum(r['first2_delta']>=0 for r in later))
    later_checks=dict(structure=all(r['structure_passed'] for r in families[1:6]),mean_delta=summary['mean_delta']>=.2,strict_positive_count=summary['strict_positive_count']>=4,min_group_delta=summary['min_group_delta']>=-.2,mean_first2_delta=summary['mean_first2_delta']>=0,nonnegative_first2_count=summary['nonnegative_first2_count']>=4)
    for name,checks in [('fixed_gate',fixed_checks),('later_gate',later_checks),('confirmation_gate',conf_checks)]:
        a.check(checks==result[name]['checks'],'gate components '+name); a.check(all(checks.values())==result[name]['passed'],'gate outcome '+name)
    for k,v in summary.items(): a.near(v,result['later_gate'][k],'later summary '+k)
    a.check(result['model_registry']=={} and result['deployment_approved'] is False and result['status']=='COMPLETED_STOPPED_AT_REGISTERED_GATE','stopped no retention result')
    registry=read(root/'MODEL_REGISTRY.json'); a.check(registry['full_real_model_fits']==registry['real_artifacts_saved']==0 and registry['status']=='NOT_RETAINED_CONFIRMATION_FAILED','registry agrees stop')
    return dict(signature=SIGNATURE,scope='Independent aggregate arithmetic and B-journal consistency; not row-level score reconstruction or training witness',checks=a.n,failures=a.errors,passed=not a.errors,max_numeric_error=a.max_error,tolerance=TOL,manifest_members=len(manifest),execution_manifest_members=len(inner),source_bindings=len(bindings),locked_source_count=len(lock['source_inputs']),source_lock_uncovered_count=len(lock['source_inputs'])-len(bindings),events=Counter(e['event'] for e in events),budget=result['budget'],families=computed,later_summary=summary,gates=dict(fixed=fixed_checks,later=later_checks,confirmation=conf_checks),decision='STOP_NO_RETAIN_NO_UPGRADE',actual_A_model_fits=0,actual_A_preprocessor_fits=0,private_data_read=False,historical_dtype='UNKNOWN')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    result=run(args.bundle);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ('checks','failures','passed','max_numeric_error','events','later_summary','decision')}))
    raise SystemExit(not result['passed'])
