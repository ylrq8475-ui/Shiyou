"""Independent loss-budget analysis from audited anonymous summaries; no training."""
import hashlib,json,math,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'A2_A24_DEPLOYMENT_R1_20261013/sources/research/FINAL_RESULT.json'
final=json.loads(SOURCE.read_bytes())
goal=95.;target_loss=1-goal/100;reported=86.2003;reported_loss=1-reported/100
families=final['research']+[final['confirmation']];records=[]
for f in families:
    b=f['arms']['B0'];loss=sum(b['monthly_official_weighted_loss']);early=sum(b['monthly_official_weighted_loss'][:2]);front4=sum(b['monthly_official_weighted_loss'][:4])
    g=b['diagnostics']['prediction_state_groups']['raw_scale_fallback'];fallback=g['group_wells']/b['well_count']*g['full_mean_weighted_loss']
    tail2=loss-early;tail4=loss-front4;top_share=b['diagnostics']['loss_concentration']['own_loss_share_top_wells']
    ceiling=lambda removed:100*(1-loss+removed)
    records.append({'stage':f['stage'],'seed':f['seed'],'B0_score':b['official_score'],'B0_loss':loss,
        'loss_reduction_fraction_needed_for_CV95':(loss-target_loss)/loss,
        'perfect_fallback_only_score':ceiling(fallback),
        'perfect_first2_only_score':ceiling(early),
        'perfect_first4_only_score':ceiling(front4),
        'perfect_top10percent_wells_only_score':ceiling(top_share*loss),
        'first4_error_reduction_needed_if_months5_12_unchanged':(loss-target_loss)/front4,
        'months3_12_minimum_reduction_if_first2_perfect':max(0.,(tail2-target_loss)/tail2),
        'diagnostic_oracle_not_achievable_model_score':True})
out={'signature':'账户A（新接手）独立审核与交付','goal':goal,'source_SHA256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
     'source_commit':'65115714d49d17122989195910b119264bd93880',
     'platform_budget_conditional_on_user_report':{'reported_score':reported,'target_score':goal,'score_gap':goal-reported,
          'current_loss':reported_loss,'target_loss':target_loss,'fraction_current_loss_to_remove':(reported_loss-target_loss)/reported_loss,
          'platform_score_independently_verified':False,'test_error_breakdown_not_available':True},
     'CV_oracle_diagnostics':records,
     'frozen_R1_current_test_contribution_of_C1':0,
     'frozen_R1_current_test_oracle_C1_cannot_change_any_output':True,
     'model_family_or_feature_information_ceiling_established':False,
     'probability_of_future_platform95_estimable_from_current_evidence':False,
     'CV95_not_required_to_claim_platform95':True,
     'new_model_fits':0,'new_data_or_private_model_access':False}
assert math.isclose(out['platform_budget_conditional_on_user_report']['score_gap'],8.7997,abs_tol=1e-12)
for r in records:
    assert r['perfect_fallback_only_score']<95 and r['perfect_first2_only_score']<95
    assert r['perfect_first4_only_score']>95 and 0<r['first4_error_reduction_needed_if_months5_12_unchanged']<1
with (HERE/'LOSS_BUDGET_95_A2.json').open('x',encoding='utf-8') as stream:json.dump(out,stream,ensure_ascii=False,indent=2)
print(json.dumps({'platform':out['platform_budget_conditional_on_user_report'],'fixed_CV':records[0]},ensure_ascii=True))
