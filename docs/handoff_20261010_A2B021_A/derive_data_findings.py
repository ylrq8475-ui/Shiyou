"""Post-score, aggregate-only interpretation; no training or new candidate."""
from pathlib import Path
import hashlib,json,math,statistics
HERE=Path(__file__).resolve().parent
ROOT=HERE/'bundle/payload/execution'
SEEDS=[20260917,20261031,20261219,20270107,20270303]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def avg(values):return statistics.mean(values)

def main():
    families=[load(ROOT/f'REPEAT_{s}.json') for s in SEEDS]
    comparisons=load(HERE/'received/MODEL_COMPARISON.json')['comparisons']
    baseline=[r['arms']['B0'] for r in families]
    weights=[avg(r['monthly_official_weighted_loss'][t] for r in baseline) for t in range(12)]
    raw=[avg(r['monthly_unweighted_relative_error'][t] for r in baseline) for t in range(12)]
    total=math.fsum(weights)
    groups={}
    for name in baseline[0]['diagnostics']['prediction_state_groups']:
        rows=[r['diagnostics']['prediction_state_groups'][name] for r in baseline]
        if any(r['status']!='RELEASED' for r in rows):groups[name]={'status':'SUPPRESSED'};continue
        contribution=avg(r['full_mean_weighted_loss']*r['group_wells']/81 for r in rows)
        groups[name]={'status':'RELEASED','group_well_count_range':[min(r['group_wells'] for r in rows),max(r['group_wells'] for r in rows)],
                      'repeat_mean_group_weighted_loss':avg(r['full_mean_weighted_loss'] for r in rows),
                      'repeat_mean_global_loss_contribution':contribution,
                      'share_of_repeat_mean_total_loss':contribution/total,
                      'definition':'fallback and training-fold q25; mutually exclusive groups, not label routing'}
    assert math.isclose(sum(v['repeat_mean_global_loss_contribution'] for v in groups.values()),total,abs_tol=1e-14)
    directions={}
    for side in ['over','under']:
        vals=[r['diagnostics']['early_directional_losses']['first2'][side] for r in baseline]
        assert all(v['status']=='RELEASED' for v in vals)
        directions[side]=avg(v['official_weighted_loss_contribution_all_wells'] for v in vals)
    assert math.isclose(sum(directions.values()),sum(weights[:2]),abs_tol=1e-14)
    leaf={}
    for arm in ['B0','C1']:
        values=[v['early_validation_row_tree_visits'] for r in [load(ROOT/'FIXED_FIVE_FOLD.json'),*families] for v in r['leaf_support'][arm]]
        leaf[arm]={'mean_independent_training_well_support':sum(v['mean_distinct_train_wells']*v['leaf_observations'] for v in values)/sum(v['leaf_observations'] for v in values),
                   'fraction_support_below_5':sum(v['fraction_support_lt5']*v['leaf_observations'] for v in values)/sum(v['leaf_observations'] for v in values)}
    for v in comparisons:
        r=[r['arms'][v['model_id']] for r in families]
        assert math.isclose(v['repeat_mean_score'],avg(x['official_score'] for x in r),abs_tol=1e-10)
        assert math.isclose(v['repeat_mean_first2_weighted_loss'],avg(x['official_weighted_prefix_loss']['2'] for x in r),abs_tol=1e-14)
    c32=[r['arms']['C3']['official_score']-r['arms']['C2']['official_score'] for r in families]
    data={'scope':'independent post-score arithmetic; no causal identification or training',
          'first2_actual_weighted_loss_share':sum(weights[:2])/total,
          'first2_mean_unweighted_relative_error':avg(raw[:2]),'month3_4_mean_unweighted_relative_error':avg(raw[2:4]),
          'prediction_known_state_groups':groups,'first2_directional_global_loss':directions,
          'leaf_support_all_six_families':leaf,'C3_minus_C2_repeat_mean':avg(c32),'C3_minus_C2_positive_repeats':sum(d>0 for d in c32),
          'B0_top10percent_repeat_mean_loss_share':avg(r['diagnostics']['loss_concentration']['own_loss_share_top_wells'] for r in baseline),
          'largest_repairable_causal_mechanism':'NOT_IDENTIFIED','label_based_routing':False,
          'no_additional_training_authorized':True,'input_files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/f'REPEAT_{s}.json' for s in SEEDS]}}
    with (HERE/'A_DATA_FINDINGS.json').open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
    print(json.dumps({k:v for k,v in data.items() if k!='input_files_sha256'},indent=2))
if __name__=='__main__':main()
