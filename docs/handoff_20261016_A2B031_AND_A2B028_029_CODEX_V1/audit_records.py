"""Read-only aggregate/source audit of R5 plus evidence inventory for R7."""
import ast,collections,hashlib,importlib.util,json,math,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;B=ROOT/'sources'/'B028029';C=ROOT/'sources'/'B030'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(name,ok):checks.append({'check':name,'passed':bool(ok)})
def close(a,b):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
r=read(B/'RESULT_A2B028_029.json');plan=read(B/'PLAN_R5.json');lock=read(B/'IMPLEMENTATION_PREFIT_LOCK.json');structure=read(B/'STRUCTURE_GATES.json');events=read(B/'EVENTS.json');counts=read(B/'FIT_COUNTS.json');prereg=read(B/'PREREG_A2B029.json');manifest=read(B/'SHA256SUMS.json');privacy=read(B/'PRIVACY_SCAN_RAW.json')
names={x.name for x in B.iterdir() if x.is_file()}
check('exact_B_file_count',len(names)==38)
check('manifest_coverage',{Path(x['path']).name for x in manifest['files']}==names-{'SHA256SUMS.json'})
for row in manifest['files']:
    p=B/Path(row['path']).name;check('original_manifest_bytes_'+p.name,sha(p)==row['sha256'] and p.stat().st_size==row['bytes'])
check('privacy_coverage',len(privacy['records'])==38 and {Path(x['path']).name for x in privacy['records']}==names)
for row in privacy['records']:
    name=Path(row['path']).name;check('private_and_credential_zero_'+name,row['result']=='PASS' and not any(row['private_marker_hits'].values()) and row['credential_or_private_path_hits']==0)
    if row['sha256'] is not None:check('scan_identity_'+name,sha(B/name)==row['sha256'] and (B/name).stat().st_size==row['bytes'])
    else:check('final_serialized_metadata_'+name,name in ['PRIVACY_SCAN_RAW.json','SHA256SUMS.json'] and 'serialized bytes' in row['scan_method'])
check('scan_no_exemption',privacy['exemptions']==0 and privacy['all_pass'])
for name,hashvalue in lock['sources'].items():
    if (B/name).is_file():check('actual_locked_source_'+name,sha(B/name)==hashvalue)
check('environment_lock_identity',sha(B/'ENVIRONMENT_LOCK.json')==lock['environment_sha256'])
check('FM_environment_identity',sha(B/'FM_ENVIRONMENT_LOCK.json')==prereg['environment_lock_sha256'])
check('FM_prereg_identity',sha(B/'PREREG_A2B029.json')==lock['FM_prereg_sha256'])
check('R5_instruction_identity',sha(B/'CLAUDE_INSTRUCTION_ORIGINAL_R5.md')==sha(ROOT/'sources'/'instructions'/'R5.md'))
ref=read(B/'REFERENCE_PANEL_CONTRACT.json')['contract']
check('base_panel_identity',lock['base_identity']==ref['panel_identity'])
check('325_base_and335_F0_columns',len(lock['ordered_feature_dtypes'])==335 and structure['baseline_features']==325 and structure['F0_extra_features']==10)
check('972_eval_rows_and81_wells',structure['baseline_rows']==972 and structure['baseline_cohort_wells']==81)
check('target_and_history_boundary',structure['history_cutoff']=='M-1' and structure['targets']=='M+1..M+12')
check('split_identity',structure['split_sha256']=='beadb191d075afdd138d6463f0b3a0e03999a76e07641f56ea24ec77e5e4d5f8')
check('feature_order_identity',lock['base_identity']['feature_order_sha256']==read(B/'PREREG_PARAMETERS.json')['features']['feature_order_sha256'])
check('F0_label_keys_unchanged',lock['base_identity']['label_key_frame_sha256']==lock['F0_identity']['label_key_frame_sha256'])
check('aux_label_keys_unchanged',lock['aux_identity']['label_key_frame_sha256']==lock['aux_F0_identity']['label_key_frame_sha256'])
check('cohort_augmentation',structure['auxiliary']['historical_events']==26 and structure['auxiliary']['incomplete_events']==6 and structure['auxiliary']['events']==32 and structure['auxiliary']['historical_rows']==312 and structure['auxiliary']['incomplete_rows']==31 and structure['auxiliary']['rows']==343)
check('all_valid_well_events_isolated',len(structure['folds'])==5 and all(x['validation_well_intersection_all_events']==0 for x in structure['folds']))
sizes=[x['validation_wells'] for x in structure['folds']]
check('fold_sizes',sizes==[17,16,16,16,16])
check('B0_exact_reference',r['B0_reproduced']==73.71410733861434 and abs(r['B0_difference'])<=1e-9 and r['B0_reproduction_passed'])
check('B0_reproduction_file',read(B/'BASELINE_REPRODUCTION.json')['score']==r['B0_reproduced'])
check('fit_totals',counts==r['fit_counts'] and counts['model_entered']==counts['model_completed']==counts['preprocessor_entered']==counts['preprocessor_completed']==20)
check('no_failed_or_retried_fit',counts['model_failed']==counts['preprocessor_failed']==counts['retries']==counts['FM_model_fits']==0)
check('event_sequence',list(range(1,len(events)+1))==[x['sequence'] for x in events])
state=collections.Counter();byconfig=collections.Counter()
for e in events:
    if e['event'] in ['model_fit_entered','model_fit_completed','preprocessor_fit_entered','preprocessor_fit_completed']:
        kind,status=e['event'].split('_fit_');key=kind+'_'+status;state[key]+=1;byconfig[(kind,status,e['config'])]+=1
    check('event_fit_counter_'+str(e['sequence']),all(e['fit_counts'][k]==state[k] for k in ['model_entered','model_completed','preprocessor_entered','preprocessor_completed']))
for c in ['B0','B0_F0','B0_AUG','B0_F0_AUG']:
    for k in ['model','preprocessor']:
        for s in ['entered','completed']:check('five_calls_'+c+'_'+k+'_'+s,byconfig[(k,s,c)]==5)
baseline=next(e for e in events if e['event']=='baseline_reproduced');locked=next(e for e in events if e['event']=='all_structures_and_prereg_locked')
check('B0_gate_after_exactly5_fits',baseline['fit_counts']['model_completed']==baseline['fit_counts']['preprocessor_completed']==5)
check('locks_before_fits',locked['fit_counts']['model_entered']==locked['fit_counts']['preprocessor_entered']==0 and lock['time']<events[2]['time'])
check('FM_prereg_before_first_score',prereg['created_at']<baseline['time'] and prereg['before_any_real_score'])
check('no_test_no_persistence',r['test_tables_parsed']==r['test_prediction_rows_generated']==r['models_saved']==r['formal_packages_created']==r['platform_submissions']==0 and not r['test_labels_read'] and not r['row_OOF_persisted'])
for c,s in {'B0':r['baseline_summary'],**r['candidates'],'FM':r['FM_zero_shot_summary']}.items():
    folds=s['fold_scores'];score=s['score'];weighted=sum(v*n for v,n in zip(folds,sizes))/81
    check('equal_well_aggregate_'+c,close(score,weighted))
    check('score_loss_identity_'+c,close(score,100*(1-s['weighted_losses']['m1_to_12'])))
    check('worst_fold_'+c,close(s['worst_fold'],min(folds)))
    avg=sum(folds)/5;std=math.sqrt(sum((x-avg)**2 for x in folds)/5);check('population_std_'+c,close(s['fold_std_ddof0'],std))
    check('prefix_losses_order_'+c,0<=s['weighted_losses']['m1_to_1']<=s['weighted_losses']['m1_to_2']<=s['weighted_losses']['m1_to_4']<=s['weighted_losses']['m1_to_12'])
    if c!='B0':
        delta=[a-b for a,b in zip(folds,r['baseline_summary']['fold_scores'])]
        check('paired_delta_'+c,all(close(a,b) for a,b in zip(delta,s['paired_fold_deltas'])))
        check('total_delta_'+c,close(s['delta'],score-r['B0_reproduced']))
        check('positive_folds_'+c,s['positive_folds']==sum(x>0 for x in delta))
        check('retention_'+c,s['meets_retention']==(s['delta']>=1 and s['positive_folds']>=4))
check('exact7_candidates',set(r['candidates'])=={'B0_ALPHA','B0_F0','B0_F0_ALPHA','B0_AUG','B0_AUG_ALPHA','B0_F0_AUG','B0_F0_AUG_ALPHA'})
check('none_retained',r['retained_candidates']==[] and r['selected_candidate_B_self_report'] is None and not any(s['meets_retention'] for s in r['candidates'].values()))
best=max(r['candidates'].items(),key=lambda x:x[1]['delta'])
check('A028_locked_weak_signal',best[0]=='B0_ALPHA' and 0<best[1]['delta']<1 and best[1]['positive_folds']==3 and r['A028_decision_B_self_report']=='最佳候选 0 < 分数差 < +1.0，或达标折数 < 4')
check('A029_stop_under70',r['FM_zero_shot_score']==r['FM_zero_shot_summary']['score']<70 and r['A029_decision_B_self_report']=='零样本得分 < 70')
check('FM_blend_not_executed',r['FM_blend_score'] is None and r['FM_blend_delta'] is None and r['FM_blend_positive_folds'] is None and 'FM_blend_records' not in r)
for name,rows in r['Dalpha_records'].items():
    check('alpha_each5folds_'+name,len(rows)==5)
    for row in rows:check('alpha_residual_scope_'+name+'_'+str(row['outer_fold']),row['same_horizon_only'] and not row['current_fold_residuals_used'] and row['residual_sample_wells']+row['validation_wells']==81)
fm=r['FM_metadata'];lic=read(B/'FM_LICENSE_AND_SIZE_EVIDENCE.json')
check('one_frozen_model',fm['model']==prereg['model']==lic['model']=='amazon/chronos-bolt-tiny' and prereg['models_allowed']==1 and fm['revision']==prereg['revision'])
check('weight_identity_everywhere',fm['weight_sha256']==prereg['weight_sha256']==lic['weight_sha256']==lock['sources']['model.safetensors'])
check('license_and_size',prereg['license']=='Apache-2.0' and lic['model_card_license']=='apache-2.0' and lic['code_and_weight_bytes']<5_000_000_000)
check('FM_scope_and_bridge',fm['model_fits']==0 and not fm['competition_training'] and fm['network_connect_blocked'] and fm['eval_mode'] and fm['inference_mode'] and fm['target_steps']==12 and fm['forecast_request_steps']==13 and fm['discarded_bridge_steps']==1)
check('FM_fixed_context_and_native_missing',fm['context_limit']==prereg['context_length']==512 and fm['native_nan_smoke_passed'])
raw=(B/'PLAN_R5.json').read_bytes();rawtext=(ROOT/'sources'/'instructions'/'R5.md').read_text(encoding='utf-8')
for name,table in plan['decisions_verbatim'].items():check('decision_table_verbatim_'+name,table in rawtext)
check('script_no_hidden_fit_entry',"pipe=training._model_pipeline('extra_trees_log_ratio_last',x,config)" in (B/'run_experiment.py').read_text(encoding='utf-8'))
for name in ['diagnostic_core.py','experiment_core.py','fm_worker.py','privacy_check.py','replay.py','route_b_core.py','run_experiment.py','test_experiment.py','train_reader.py']:
    compile((B/name).read_bytes(),name,'exec');check('compile_'+name,True)
debug=read(B/'PREFIT_DEBUG_RECORD.json');check('startup_failures_not_fit_retries',debug['failed_fit_entries']==debug['model_fit_retries']==0 and all(a['model_entered']==a['preprocessor_entered']==0 for a in debug['attempts'][:2]))
check('protected_record_unchanged',r['integrity']['protected_files_checked']==634 and all(r['integrity'][k] for k in ['protected_unchanged','raw_archive_manifest_unchanged','locked_source_inputs_unchanged']))
fields=read(C/'FIELD_DICTIONARY_N1.json')
check('no_layer_date_field',not any(x['date_field'] for x in fields['layer']))
check('only_completion_date_in_plan',[x['field'] for x in fields['plan'] if x['date_field']]==['完工日期'])
check('Q1_G_fields_have_official_definitions',{'YXHD','SYHD','STL','YCZMC'}<=set(x['field'] for x in fields['layer']))
check('R7_hash_exact',sha(ROOT/'sources'/'instructions'/'R7.md')=='70e0fb5bcc66561941b2337293789767c6e856b1e5784bcca281f3ecb5350b6f')
summary={'B_commit':'a2bc8d4c02eba88bea2cb468a5478a4a5f0b18c9','passed':all(x['passed'] for x in checks),'check_count':len(checks),'checks':checks,'best_candidate':best[0],'best_delta':best[1]['delta'],'best_positive_folds':best[1]['positive_folds'],'A_model_fits':0,'A_preprocessor_fits':0,'A_real_data_read':False,'A_weight_downloaded':False,'B_real_training_or_FM_inference_independently_reexecuted':False}
with (ROOT/'AGGREGATE_AUDIT_CODEX.json').open('x',encoding='utf-8') as stream:json.dump(summary,stream,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in summary.items() if k!='checks'}))
if not summary['passed']:print(json.dumps([x for x in checks if not x['passed']]));sys.exit(1)
