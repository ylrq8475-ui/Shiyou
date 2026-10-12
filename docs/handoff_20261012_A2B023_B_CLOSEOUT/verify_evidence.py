"""Portable aggregate-only check; no project imports, data loading or fitting."""
import json
import math
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parent
load=lambda n:json.loads((ROOT/n).read_bytes())

def run():
    b=load('B_AGGREGATE_EVIDENCE.json')
    a=load('A_ROUTE_SIGNAL.json')
    summary=load('A_ARITHMETIC_SUMMARY.json')
    checks=[]
    def check(name,ok):
        checks.append({'check':name,'passed':bool(ok)})
        if not ok:raise AssertionError(name)
    def equal(name,x,y):check(name,math.isclose(x,y,rel_tol=0,abs_tol=1e-10))
    check('same_B_commit',b['source_commit']==a['source_commit']==summary['source_commit'])
    check('six_families',len(b['families'])==len(a['family_observations'])==6)
    deltas=[];route=[];early=[]
    for i,(family,signal) in enumerate(zip(b['families'],a['family_observations'])):
        prefix='family_'+str(i)+'_'
        check(prefix+'same_seed',family['seed']==signal['seed'])
        equal(prefix+'baseline',family['B0_score'],signal['baseline_score'])
        delta=family['C1_score']-family['B0_score']
        g=family['fallback_group']
        equal(prefix+'fallback_denominator',g['group_wells']+g['complement_wells'],81)
        equal(prefix+'fallback_count',g['group_wells'],14)
        net=-100*g['net_loss_change_contribution_all_wells']
        first2=-100*g['early_net_loss_change_contribution_all_wells']
        equal(prefix+'route_gain',net,signal['posthoc_fallback_only_delta'])
        equal(prefix+'route_score',family['B0_score']+net,signal['posthoc_fallback_only_score'])
        equal(prefix+'early_route_gain',first2,signal['posthoc_first2_score_delta'])
        equal(prefix+'month_decomposition',first2+signal['posthoc_months3_12_score_delta'],net)
        equal(prefix+'group_to_total',g['score_delta_vs_B0_in_group']*14/81,net)
        for arm in ('B0','C1'):
            loss=family[arm+'_monthly_weighted_loss']
            check(prefix+arm+'_12_months',len(loss)==12)
            equal(prefix+arm+'_official_score',100*(1-sum(loss)),family[arm+'_score'])
        if i:
            deltas.append(delta);route.append(net);early.append(first2)
        else:
            equal('fixed_original_delta',delta,summary['fixed_delta'])
    equal('repeat_original_delta',statistics.mean(deltas),summary['repeat_mean_delta'])
    check('original_repeat_zero_positive',sum(x>0 for x in deltas)==0)
    equal('route_repeat_mean',statistics.mean(route),a['repeat_mean_posthoc_delta'])
    equal('route_repeat_min',min(route),a['repeat_min_posthoc_delta'])
    equal('route_early_mean',statistics.mean(early),a['repeat_mean_early_delta'])
    check('route_positive_5',sum(x>0 for x in route)==a['repeat_positive_deltas']==5)
    check('A_only_readonly',summary['model_fits_by_A']==0 and summary['check_count']==696 and summary['all_passed'])
    check('posthoc_not_validation',a['posthoc_derivation_not_preregistered_validation'] and not a['new_fit_or_candidate_execution'])
    check('historical_dtype_not_filled',b['historical_dtype']=='UNKNOWN')
    result={'checks':checks,'check_count':len(checks),'all_passed':True,
            'new_model_fits':0,'new_preprocessor_fits':0,'private_data_read':False,
            'scope':'B independently compares anonymous A claims to frozen B aggregates; route values remain post-hoc algebra, not new performance'}
    p=ROOT/'AGGREGATE_RECEIPT_CHECKS.json'
    if p.exists():assert load(p.name)==result
    else:p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'}))

if __name__=='__main__':run()
