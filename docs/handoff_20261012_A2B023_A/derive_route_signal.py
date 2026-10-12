"""Read-only post-hoc algebra; not a trained or independently validated candidate."""
from pathlib import Path
import ast, hashlib, json, math, statistics, types
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE/'bundle'
read=lambda p:json.loads(p.read_bytes())
final=read(ROOT/'execution/FINAL_RESULT.json')
observations=[]
for r in final['research']:
    b,c=r['arms']['B0'],r['arms']['C1']
    g=c['diagnostics']['prediction_state_groups']['raw_scale_fallback']
    assert g['status']=='RELEASED' and g['group_wells']==14
    net=-100*g['net_loss_change_contribution_all_wells']
    early=-100*g['early_net_loss_change_contribution_all_wells']
    observations.append({'seed':r['seed'],'baseline_score':b['official_score'],
        'posthoc_fallback_only_delta':net,'posthoc_fallback_only_score':b['official_score']+net,
        'posthoc_first2_score_delta':early,'posthoc_months3_12_score_delta':net-early,
        'group_score_delta':g['score_delta_vs_B0_in_group'],'group_wells':g['group_wells']})
repeat=observations[1:]
# Execute only pure target/inverse definitions on invented numbers.
module=types.ModuleType('synthetic_target_check')
def require(ok,message):
    if not ok:raise ValueError(message)
module.__dict__.update(np=np,require=require,MODEL_NAMES={'B0':'ratio','C1':'absolute'})
tree=ast.parse((ROOT/'runtime/a2b023_core.py').read_text(encoding='utf-8'))
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'scales','target','inverse'}]
assert len(nodes)==3
exec(compile(ast.Module(body=nodes,type_ignores=[]),'bound_B_target_definitions','exec'),module.__dict__)
raw=np.array([0.,-2.,np.nan,np.inf,1.,4.]);y=np.array([2.,5.,8.,3.,7.,12.])
scale,fallback=module.scales(raw)
t0=module.target(y,raw,'B0');t1=module.target(y,raw,'C1')
assert np.array_equal(t0[fallback],t1[fallback])
z=np.array([.2,.3,.4,.5,.6,.7])
assert np.array_equal(module.inverse(z,raw,'B0')[fallback],module.inverse(z,raw,'C1')[fallback])
assert not fallback[4] and scale[4]==1
assert t0[-1]!=t1[-1]
result={'status':'POSTHOC_RESEARCH_SIGNAL_ONLY','source_commit':'4ea326798ca1da0736cde4bc41f33b7ff8b58cf9',
 'new_fit_or_candidate_execution':False,'posthoc_derivation_not_preregistered_validation':True,
 'derivation':'Whole-well route uses C1 only when raw last RCYL is nonfinite or <=0, otherwise B0; equal-well loss makes aggregate score change equal existing fallback-group contribution. No row predictions reconstructed.',
 'selection_bias':'Hypothesis selected after observing these outcomes. Same 81 wells and reused splits; scores cannot be called fresh confirmation or significance.',
 'family_observations':observations,
 'repeat_mean_posthoc_score':statistics.mean(r['posthoc_fallback_only_score'] for r in repeat),
 'repeat_mean_posthoc_delta':statistics.mean(r['posthoc_fallback_only_delta'] for r in repeat),
 'repeat_min_posthoc_delta':min(r['posthoc_fallback_only_delta'] for r in repeat),
 'repeat_positive_deltas':sum(r['posthoc_fallback_only_delta']>0 for r in repeat),
 'repeat_mean_early_delta':statistics.mean(r['posthoc_first2_score_delta'] for r in repeat),
 'synthetic_fallback_target_equality':True,'synthetic_fallback_inverse_equality_given_same_z':True,
 'interpretation':'Fallback rows have identical numeric targets and inverse mapping in both arms. Prediction changes arise from the globally different training target geometry and fitted trees, not from changing fallback1 itself.',
 'ordinary_rows_unchanged_is_design_requirement_not_executed_router_evidence':True,
 'not_authorization_for_training_or_deployment':True}
with (HERE/'A_ROUTE_SIGNAL.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False,indent=2))
