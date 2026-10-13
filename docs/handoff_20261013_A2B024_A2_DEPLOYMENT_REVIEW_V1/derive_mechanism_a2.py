"""Infer only aggregate loss-mass bounds and method applicability from audited evidence."""
import json,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
v=json.loads((HERE/'INDEPENDENT_AGGREGATE_A2.json').read_bytes())
families=v['loss_budget_observations'];observations=[]
for x in families:
    observations.append({'stage':x['stage'],'seed':x['seed'],
       'positive_state_loss_share':x['positive_state_full_loss_share'],
       'first2_loss_share':x['B0_first2_loss_share'],
       'positive_state_first2_loss_share_lower_bound':max(0.,x['positive_state_full_loss_share']+x['B0_first2_loss_share']-1),
       'positive_state_first2_loss_share_upper_bound':min(x['positive_state_full_loss_share'],x['B0_first2_loss_share']),
       'bound_not_measured_intersection':True})
screen=observations[1:6]
out={'signature':'账户A（新接手）独立审核与交付','observations':observations,
     'five_screen_lower_bound_range':[min(x['positive_state_first2_loss_share_lower_bound'] for x in screen),max(x['positive_state_first2_loss_share_lower_bound'] for x in screen)],
     'derivation':'Nonnegative loss mass: share(A intersection B) >= share(A)+share(B)-1; <= min(share(A),share(B))',
     'test_C1_branch_coverage_B_record':0,'test_prediction_changes_A_observed':0,
     'priority':'Test a mechanism that can change B0 predictions for positive-state wells, concentrating diagnosis on first two months',
     'single_future_hypothesis':'Same scaled-log target, full 12-month pooled ExtraTrees; replace squared_error split/leaf criterion with absolute_error only, after checking candidate ledger',
     'hypothesis_not_proven':True,'state_by_direction_intersection_missing':True,
     'must_not_infer_uniform_overprediction':True,'current_test_labels_not_known':True,
     'cannot_identify_largest_repairable_true_test_error':True,'new_training_authorized_or_started':False,
     'software_method_reference':'https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html',
     'external_datasets_or_fitted_state_used':False}
with (HERE/'ERROR_MECHANISM_A2.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps({'five_screen_lower_bound_range':out['five_screen_lower_bound_range'],'no_new_training':True}))
