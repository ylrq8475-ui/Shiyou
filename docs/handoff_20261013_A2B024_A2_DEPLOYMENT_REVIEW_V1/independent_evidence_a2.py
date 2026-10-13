"""A2 independently recomputes anonymous summaries; never imports B metric or fits."""
from pathlib import Path
import hashlib,json,math,statistics
HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[];max_error=0.
def check(name,ok):
    checks.append({'check':name,'passed':bool(ok)})
    if not ok:raise AssertionError(name)
def equal(name,a,b):
    global max_error
    error=abs(float(a)-float(b));max_error=max(max_error,error);check(name,error<1e-10)
manifest_counts={}
for group,manifest_name in [('sources/deploy','UPLOAD_SHA256SUMS.json'),('deploy_bundle','SHA256SUMS.json'),('sources/research','UPLOAD_SHA256SUMS.json'),('research_bundle','BUNDLE_SHA256SUMS.json')]:
    root=HERE/group;obj=load(root/manifest_name);records=obj.get('files',obj)
    if isinstance(records,list):records={v['path']:v for v in records}
    verified=0
    for n,v in records.items():
        p=root/n;check(group+'_exists_'+n,p.is_file())
        expected=v if isinstance(v,str) else v['sha256'];check(group+'_sha_'+n,sha(p)==expected)
        if isinstance(v,dict) and 'bytes' in v:check(group+'_bytes_'+n,p.stat().st_size==v['bytes'])
        verified+=1
    manifest_counts[group]=verified
    if group.endswith('_bundle'):
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        check(group+'_coverage',actual==set(records)|{manifest_name})
source_lock=load(HERE/'deploy_bundle/SOURCE_LOCK.json')
for n,v in source_lock['public_source_hashes'].items():check('source_lock_'+n,sha(HERE/'deploy_bundle/source'/n)==v)
for n in source_lock['public_source_hashes']:
    check('source_original_outer_binding_'+n,(HERE/'deploy_bundle/source'/n).is_file())
final=load(HERE/'sources/research/FINAL_RESULT.json');families=final['research']+[final['confirmation']]
check('seven_families',len(families)==7)
events=[load(p) for p in sorted((HERE/'research_bundle/evidence/events').glob('*.json'))]
entries=[e for e in events if e['event']=='model_entered'];completed=[e for e in events if e['event']=='fit_completed'];fold_done=[e for e in events if e['event']=='fold_completed']
check('model_event_counts',len(entries)==len(completed)==70 and len(fold_done)==35)
tag=lambda e:(e['stage'],e['seed'],e['fold'],e['arm'])
check('unique_entered_and_completed_identities',len({tag(e) for e in entries})==70 and {tag(e) for e in entries}=={tag(e) for e in completed})
family_summaries=[];error_sources=[]
for i,family in enumerate(families):
    prefix='family_'+str(i)+'_';arm_scores={};stage=family['stage'];seed=family['seed']
    rows=[e for e in entries if e['stage']==stage and e['seed']==seed and e['arm']=='B0']
    rows.sort(key=lambda e:e['fold']);counts=[81-e['train_wells'] for e in rows]
    check(prefix+'validation_well_counts',len(counts)==5 and sum(counts)==81)
    for arm in ['B0','C1','R1']:
        summary=family['arms'][arm]
        raw=summary['monthly_unweighted_relative_error'];weighted=[2.**(-t)*v for t,v in enumerate(raw,1)]
        check(prefix+arm+'_twelve_months',len(raw)==12)
        for t,(x,y) in enumerate(zip(weighted,summary['monthly_official_weighted_loss'])):equal(prefix+arm+'_weight_'+str(t),x,y)
        score=100*(1-sum(weighted));arm_scores[arm]=score;equal(prefix+arm+'_official_score',score,summary['official_score'])
        for end in [1,2,4,12]:equal(prefix+arm+'_prefix_'+str(end),sum(weighted[:end]),summary['official_weighted_prefix_loss'][str(end)])
        fs=summary['fold_scores'];equal(prefix+arm+'_worst_fold',min(fs),summary['worst_fold']);equal(prefix+arm+'_ddof0',statistics.pstdev(fs),summary['fold_std_ddof0'])
        equal(prefix+arm+'_well_weighted_fold_total',sum(n*s for n,s in zip(counts,fs))/81,score)
        g=summary['diagnostics']['prediction_state_groups'];check(prefix+arm+'_group_partition',sum(v['group_wells'] for v in g.values())==81)
        equal(prefix+arm+'_group_loss_identity',sum(v['group_wells']*v['full_mean_weighted_loss'] for v in g.values())/81,sum(weighted))
        equal(prefix+arm+'_group_early_identity',sum(v['group_wells']*v['early_mean_weighted_loss'] for v in g.values())/81,sum(weighted[:2]))
        if arm=='R1':
            for name in ['positive_scale_training_q25_low','other_positive_scale']:
                equal(prefix+name+'_zero_route_contribution',g[name]['net_loss_change_contribution_all_wells'],0.)
            equal(prefix+'fallback_total_gain',-100*g['raw_scale_fallback']['net_loss_change_contribution_all_wells'],arm_scores['R1']-arm_scores['B0'])
            equal(prefix+'fallback_group_to_total',g['raw_scale_fallback']['score_delta_vs_B0_in_group']*14/81,arm_scores['R1']-arm_scores['B0'])
    b0,r1=family['arms']['B0'],family['arms']['R1'];delta=arm_scores['R1']-arm_scores['B0'];early=100*(sum(b0['monthly_official_weighted_loss'][:2])-sum(r1['monthly_official_weighted_loss'][:2]))
    equal(prefix+'delta',delta,family['delta_vs_B0']);equal(prefix+'early_delta',early,family['first2_score_delta'])
    paired=[r-b for b,r in zip(b0['fold_scores'],r1['fold_scores'])]
    equal(prefix+'min_pair',min(paired),family['fold_risk']['minimum_paired_fold_delta'])
    equal(prefix+'minima_difference',min(r1['fold_scores'])-min(b0['fold_scores']),family['fold_risk']['difference_of_minima'])
    ci=family['contribution_identity'];equal(prefix+'monthly_route_net_total',sum(ci['monthly_score_delta']),delta)
    bdiag=b0['diagnostics'];bg=bdiag['prediction_state_groups'];full=sum(b0['monthly_official_weighted_loss']);early_loss=sum(b0['monthly_official_weighted_loss'][:2])
    positive_loss=sum(v['group_wells']*v['full_mean_weighted_loss']/81 for k,v in bg.items() if k!='raw_scale_fallback')
    directions=bdiag['early_directional_losses'];over=directions['first2']['over']['official_weighted_loss_contribution_all_wells'];under=directions['first2']['under']['official_weighted_loss_contribution_all_wells']
    equal(prefix+'direction_loss_identity',over+under,early_loss)
    error_sources.append({'stage':stage,'seed':seed,'B0_first2_loss_share':early_loss/full,'positive_state_full_loss_share':positive_loss/full,
                         'first2_overprediction_loss_share':over/early_loss,'first2_underprediction_loss_share':under/early_loss,
                         'no_state_by_direction_intersection_supplied':True})
    family_summaries.append({'stage':stage,'seed':seed,'B0_score':arm_scores['B0'],'C1_score':arm_scores['C1'],'R1_score':arm_scores['R1'],'R1_delta':delta,
                             'first2_delta':early,'minimum_paired_fold_delta':min(paired),'difference_of_minima':min(r1['fold_scores'])-min(b0['fold_scores'])})
later=family_summaries[1:6];confirm=family_summaries[-1]
mean=statistics.mean(x['R1_delta'] for x in later);early_mean=statistics.mean(x['first2_delta'] for x in later)
equal('repeat_mean_delta',mean,final['later_gate']['mean_delta']);equal('repeat_mean_first2',early_mean,final['later_gate']['mean_first2_delta'])
check('screen_gate_passes',mean>=.2 and sum(x['R1_delta']>0 for x in later)>=4 and min(x['R1_delta'] for x in later)>=-.2 and early_mean>=0 and sum(x['first2_delta']>=0 for x in later)>=4)
check('confirmation_still_failed',confirm['R1_delta']<.2 and confirm['first2_delta']<0 and not final['confirmation_gate']['passed'])
check('original_research_no_full_or_registry',final['budget']['stage_successes']['conditional_private_full_fit']==0 and final['model_registry']=={})
accept=load(HERE/'sources/deploy/DEPLOYMENT_ACCEPTANCE_B.json');registry=load(HERE/'sources/deploy/MODEL_REGISTRY.json');selection=load(HERE/'sources/deploy/AUTHORIZATION_SELECTION.json')
check('separate_exploration_authorization_record',selection['full_fit_and_save'] and selection['accept_original_confirmation_failed_for_platform_exploration'] and not selection['platform_upload'])
check('full_deployment_count_and_failed_research_consistent',accept['model_counts']=={'model_entered':2,'model_completed':2,'preprocess_entered':2,'preprocess_completed':2} and accept['research_confirmation']=='FAILED_UNCHANGED')
check('test_route_counts_B_record',accept['fallback_test_wells']==0 and accept['positive_test_wells']==10 and accept['test_R1_exactly_equals_this_full_B0'])
check('model_identity_binding',accept['model_sha256']==registry['model_sha256'])
check('post_fit_not_fit_retry',accept['model_fit_failures']==accept['fit_retries']==0 and accept['post_fit_validation_failures_resolved']==1)
devents=[load(HERE/'deploy_bundle/events'/n) for n in ['B0_MODEL_ENTERED.json','B0_MODEL_COMPLETED.json','C1_MODEL_ENTERED.json','C1_MODEL_COMPLETED.json']]
check('two_full_fit_event_records',len(devents)==4 and devents[-1]['counters']==accept['model_counts'])
lock=load(HERE/'sources/research/IMPLEMENTATION_PRETRAIN_LOCK.json');check('criterion_actual_squared_error',lock['model_parameters']['criterion']=='squared_error')
result={'signature':'账户A（新接手）独立审核与交付','check_count':len(checks),'all_passed':True,'max_arithmetic_difference':max_error,
        'manifest_counts':manifest_counts,'families':family_summaries,'loss_budget_observations':error_sources,
        'new_repeat_mean_delta':mean,'new_repeat_mean_first2_delta':early_mean,'original_confirmation_failed':True,
        'true_labels_predictions_or_real_fits_regenerated':False,'B_execution_records_verified_for_internal_consistency_only':True,
        'real_fit_or_model_loads_by_A2':0,'code_and_result_attachments_bound_separately':True,'checks':checks}
with (HERE/'INDEPENDENT_AGGREGATE_A2.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in {'checks','families','loss_budget_observations'}},ensure_ascii=True))
print(json.dumps({'confirmation':confirm,'fixed_error_budget':error_sources[0],'screen_error_budget':error_sources[1:6]},ensure_ascii=True))
