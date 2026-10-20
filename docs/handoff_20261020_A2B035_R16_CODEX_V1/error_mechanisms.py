"""No new experiments; pair existing complete anonymous OOF budgets."""
import json,statistics
from pathlib import Path
R=Path(__file__).resolve().parent
e=json.loads((R/'EVIDENCE_AND_ARITHMETIC.json').read_bytes());d=e['diagnosis'];out={}
for name,base in [('CAT_B0_d6_W','CTRL_NATIVE_B0'),('CAT_B0P_d6_U','CTRL_NATIVE_B0P'),('LGB_B0_n7_m10_t300_W','CTRL_NATIVE_B0'),('LGB_B0P_n7_m10_t300_U','CTRL_NATIVE_B0P')]:
 a,b=d[name],d[base]
 row={'reference':base,'score_contributions':{k:100*(b['buckets'][k]-a['buckets'][k]) for k in a['buckets']},'direction_loss_change_points':{k:100*(a['directions'][k]-b['directions'][k]) for k in a['directions']},'group_loss_change_points':{field:{k:100*(v['group_mean_weighted_loss']-b['groups'][field][k]['group_mean_weighted_loss']) for k,v in a['groups'][field].items()} for field in ['production_tertile','scale_fallback'] if isinstance(a['groups'][field],dict)},'early_direction_loss_change_points':{m:{k:100*(a['early_directions'][m][k]-b['early_directions'][m][k]) for k in a['early_directions'][m]} for m in ['month1','month2']}}
 row['early2_score_gain']=row['score_contributions']['month1']+row['score_contributions']['month2'];out[name]=row
weight={}
for cut in ['B0','B0P']:
 rows=[v for v in e['W_U_pairs'] if '_'+cut+'_' in v['weighted']]
 weight[cut]={'pairs':len(rows),'positive_pairs':sum(v['delta_repeat']>0 for v in rows),'minimum_delta':min(v['delta_repeat'] for v in rows),'maximum_delta':max(v['delta_repeat'] for v in rows),'all_early2_positive':all(v['early2_score_gain']>0 for v in rows)}
extra={'paired_diagnoses':out,'W_U_summary':weight,'tree_increase_pairs':len(e['tree_count_pairs']),'tree_increase_positive_pairs':sum(v['delta_repeat']>0 for v in e['tree_count_pairs']),'evidence_boundary':'association from already published grouped OOF budgets; not causal attribution, no new tuning or fits'}
(R/'ERROR_MECHANISMS.json').write_text(json.dumps(extra,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(extra,indent=2))
