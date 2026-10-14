"""Independent aggregate, ledger, source-lock, publication and decision checks."""
import ast, hashlib, json, math, re, statistics, subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BROOT=ROOT/'sources/B'
REPO=ROOT.parent/'CODEX026_B2_IMPLEMENTATION_REVIEW_20261014/publication_git'
B='3926e2972da62c61eb318abaa670a5da776d62ec';PARENT='213b1b465c61d799371e2b4326ebc71922c4f7ee'
PREFIX='docs/handoff_20261014_A2B026_ROUTE_B_B2_B_V1/'
checks=[]
def check(label,ok):
    checks.append({'check':label,'passed':bool(ok)})
    if not ok:raise RuntimeError(label)
def close(label,x,y,tol=1e-12):check(label,math.isfinite(x) and math.isfinite(y) and abs(x-y)<=tol)
def load(name):return json.loads((BROOT/name).read_bytes())
def hash_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fp(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def git(*args):
    out=subprocess.run(['git','-C',str(REPO),*args],capture_output=True,timeout=60)
    if out.returncode:raise RuntimeError('PUBLIC_GIT_SCOPE_CHECK_FAILED')
    return out.stdout.decode('utf-8').strip()
def write_new(name,obj):
    with (ROOT/name).open('x',encoding='utf-8') as out:json.dump(obj,out,ensure_ascii=False,indent=2);out.write('\n')

def main():
    files={p.name for p in BROOT.iterdir() if p.is_file()}
    manifest=load('SHA256SUMS.json');bound=set()
    for row in manifest['files']:
        check('manifest_safe_path_'+row['path'],row['path'].startswith(PREFIX))
        name=row['path'][len(PREFIX):];bound.add(name)
        check('manifest_bytes_'+name,len((BROOT/name).read_bytes())==row['bytes'])
        check('manifest_sha_'+name,hash_file(BROOT/name)==row['sha256'])
    check('manifest_exact_public_file_set',bound|{'SHA256SUMS.json'}==files)
    result=load('RESULT_B2.json');params=load('PREREG_PARAMETERS.json');lock=load('IMPLEMENTATION_PREFIT_LOCK.json')
    events=load('EVENTS.json');counts=load('FIT_COUNTS.json');structure=load('STRUCTURE_GATES.json');scan=load('PRIVACY_SCAN_RAW.json')
    check('params_original_bytes', (BROOT/'PREREG_PARAMETERS.json').read_bytes()==(ROOT/'sources/R2/PREREG_PARAMETERS.json').read_bytes())
    instruction=(ROOT/'sources/Claude/INSTRUCTION_ORIGINAL.md').read_bytes()
    check('Claude_R3_archive_manifest',hashlib.sha256(instruction).hexdigest()==json.loads((ROOT/'sources/Claude/SHA256SUMS.json').read_bytes())['INSTRUCTION_ORIGINAL.md'])
    check('Claude_R3_copy_original_bytes',instruction==(BROOT/'CLAUDE_INSTRUCTION_ORIGINAL_R3.md').read_bytes())
    check('authorized_B2_OOF_scope','批准B-2并发布' in instruction.decode() and result['Claude_instruction_commit']=='088a71ae8760a57272f68cc2cb538b0a8eecc288')
    report=(BROOT/'REPORT_B.md').read_text(encoding='utf-8-sig');original=instruction.decode()
    startup='启动条件：第 11 项经 Codex 判为"通过"，且用户另行批准 B-2。'
    first_body=report.split('## 1.',1)[1].split('## 2.',1)[0]
    check('CODEX_026B_04_exact_startup_in_first_body_section',startup in original and startup in first_body and result['startup_original']==startup)
    for field in ['任务编号/阶段：','角色：','分支：','完整提交号（40 位）：','目录路径：','结果文件路径（单个 JSON）：','关键数字','硬门禁结论：','UNKNOWN 与未关闭项：','对应决策表行','所依据的 Claude 指令存档提交号（40 位）：']:
        check('B_registration_'+field,field in report.split('## 1.',1)[0])
    check('B_snapshot_is_ancestor',subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor','09f74e2e980c7d1f7951bad6fe69efd82f64f010',B],capture_output=True).returncode==0)
    check('B_snapshot_result_bytes_unchanged',git('rev-parse','09f74e2e980c7d1f7951bad6fe69efd82f64f010:'+PREFIX+'RESULT_B2.json')==git('rev-parse',B+':'+PREFIX+'RESULT_B2.json'))
    changes=git('diff','--name-status',PARENT,B).splitlines()
    check('only_new_B_directory_added',set(changes)=={'A\t'+PREFIX+name for name in files})
    old={line.split('\t')[1]:line.split('\t')[0].split()[2] for line in git('ls-tree','-r',PARENT).splitlines()}
    new={line.split('\t')[1]:line.split('\t')[0].split()[2] for line in git('ls-tree','-r',B).splitlines()}
    check('all_old_public_blobs_unchanged',all(new.get(p)==blob for p,blob in old.items()))
    for name in ['run_b2.py','route_b_core.py','train_reader.py','test_route_b.py','CLAUDE_INSTRUCTION_ORIGINAL_R3.md','PREREG_PARAMETERS.json','CODEX_ITEM11_AND_ITEM04_RESULT.json','REFERENCE_PANEL_CONTRACT.json']:
        check('prefit_lock_sha_'+name,hash_file(BROOT/name)==lock['source_fingerprints'][name])
    check('environment_lock_binding',hash_file(BROOT/'ENVIRONMENT_LOCK.json')==lock['environment_sha256'])
    check('source_receipt_lock_binding',hash_file(BROOT/'SOURCE_RECEIPT.json')==lock['source_receipt_sha256'])
    check('parameter_lock_binding',hash_file(BROOT/'PREREG_PARAMETERS.json')==lock['params_sha256'])
    check('fault_tests_source_binding',load('FAULT_INJECTION_RESULTS.json')['run_b2_source_sha256']==hash_file(BROOT/'run_b2.py'))
    check('feature_order_original',lock['features']==load('REFERENCE_PANEL_CONTRACT.json')['contract']['feature_order'] and fp(lock['features'])==params['features']['feature_order_sha256'])
    check('locked_new_dtype_hash',fp(lock['ordered_dtypes'])==lock['new_panel_identity']['feature_dtype_sha256'])
    check('panel_identity_bound',lock['new_panel_identity']==load('REFERENCE_PANEL_CONTRACT.json')['contract']['panel_identity'])
    check('structural_lock_same_object',structure==lock['structure'])
    check('locked_budgets_unchanged',lock['budgets']==params['budget_proposed_for_separate_B2_approval'])
    check('outer_original_split_binding',structure['outer_split_sha256']==params['validation']['outer_split_sha256'])
    check('325_Mminus1_target_boundary',structure['features']==325 and structure['history_cutoff']=='M-1' and structure['all_target_windows_M_plus_1_to_12'] and structure['raw_scale_from_legal_cutoff'])
    check('all_fold_intersections_zero',structure['all_outer_inner_well_intersections']==0)
    check('cutoff_invariance_records',structure['cutoff_audit']=={'events_checked':81,'feature_values_checked':29079,'future_sensitive_feature_count':0})
    # Reconstruct every event count without trusting the published final total.
    running={k:0 for k in counts};pending=None;baseline_sequence=None;taus={};first_fit_time=None
    for i,event in enumerate(events,1):
        check('event_sequence_'+str(i),event['sequence']==i)
        if i>1:check('event_time_order_'+str(i),datetime.fromisoformat(event['time'])>=datetime.fromisoformat(events[i-2]['time']))
        name=event['event']
        if name.endswith('_fit_entered'):
            check('one_active_fit_'+str(i),pending is None)
            kind=name.split('_fit_',1)[0];role=event['role'];fold=event['outer_fold']
            if first_fit_time is None:first_fit_time=datetime.fromisoformat(event['time'])
            running[kind+'_entered']+=1
            if kind=='model':running[role]+=1
            if role!='outer_regressor':check('baseline_pass_precedes_inner_or_classifier_'+str(i),baseline_sequence is not None)
            if role=='outer_classifier':check('inner_tau_precedes_classifier_'+str(i),fold in taus)
            pending=(kind,role,fold)
        elif name.endswith('_fit_completed') or name.endswith('_fit_failed'):
            kind=name.split('_fit_',1)[0]
            check('fit_completion_matches_entry_'+str(i),pending==(kind,event['role'],event['outer_fold']))
            running[kind+('_completed' if name.endswith('_completed') else '_failed')]+=1;pending=None
        elif name=='baseline_reproduction_evaluated':
            check('baseline_event_passed',event['passed'] is True and event['absolute_difference']<=1e-9)
            check('baseline_stage_exact_fit_counts',running['outer_regressor']==5 and running['model_completed']==5 and running['preprocessor_completed']==5 and running['inner_regressor']==running['outer_classifier']==0)
            baseline_sequence=i
        elif name=='tau_frozen_from_inner_folds_before_classifier':
            fold=event['outer_fold'];taus[fold]=event
            check('three_more_inner_models_per_tau_'+str(fold),running['inner_regressor']==3*fold)
        elif name=='outer_two_stage_fold_completed':check('candidate_fold_no_route_'+str(event['outer_fold']),event['rows_routed_to_zero']==0)
        check('event_counts_reconstructed_'+str(i),running==event['fit_counts'])
    check('all_fit_entries_completed_no_pending',pending is None)
    check('counts_event_result_files_agree',running==counts==result['fit_counts'])
    check('model25_preprocess20_no_failed_retry_fullfit',counts['model_entered']==counts['model_completed']==25 and counts['preprocessor_entered']==counts['preprocessor_completed']==20 and all(counts[k]==0 for k in ['model_failed','preprocessor_failed','retries','inner_classifier','full_fits']))
    check('prefit_lock_before_actual_first_fit',lock['before_first_real_fit_and_new_score'] is True and datetime.fromisoformat(lock['time'])<first_fit_time)
    folds=result['threshold_selection_records'];val_counts=[]
    for record in folds:
        fold=record['outer_fold'];inner=record['inner_fold_estimates']
        ell=math.fsum(x['positive_conditional_weighted_loss'] for x in inner)/3
        close('lplus_independent_equal_three_fold_'+str(fold),ell,record['l_plus'])
        tau=(1-ell)/(2-ell);close('tau_independent_formula_'+str(fold),tau,record['tau'])
        close('tau_event_binding_'+str(fold),record['tau'],taus[fold]['tau'])
        check('inner_fold_counts_'+str(fold),len(inner)==3 and all(x['well_intersection']==0 for x in inner))
        n=sum(x['validation_wells'] for x in inner);val_counts.append(81-n)
        check('inner_train_partition_'+str(fold),all(x['training_wells']+x['validation_wells']==n for x in inner))
        check('outer_train_all_rows_classes_'+str(fold),record['train_zero_rows']+record['train_positive_rows']==12*n)
        check('inner_positive_coverage_'+str(fold),sum(x['positive_target_rows'] for x in inner)==record['train_positive_rows'])
        check('tau_no_outer_info_or_inner_classifier_'+str(fold),record['outer_OOF_used_for_tau'] is False and record['inner_classifier_fits']==0)
        check('unrouted_B0_identity_'+str(fold),record['unrouted_B0_outputs_identical'] is True and record['validation_rows_routed_to_zero']==0)
    check('outer_validation_wells_total81',sum(val_counts)==81 and val_counts==[17,16,16,16,16])
    for arm,key in [('baseline','baseline_reproduced'),('candidate','two_stage_OOF')]:
        scores=result[arm+'_fold_scores'];summary=result[arm+'_summary']
        aggregate=math.fsum(s*n for s,n in zip(scores,val_counts))/81
        close(arm+'_equal_well_weighted_folds',aggregate,result[key])
        close(arm+'_score_from_official_loss',100*(1-summary['official_weighted_loss']),result[key])
        close(arm+'_worst_fold',min(scores),result[arm+'_worst_fold'])
        close(arm+'_std_ddof0',statistics.pstdev(scores),result[arm+'_fold_std_ddof0'])
        check(arm+'_complete81x12',summary['wells']==81 and summary['rows']==972)
        partial=summary['weighted_loss_by_horizon_prefix'];check(arm+'_monotone_prefix_losses',0<=partial['1']<=partial['2']<=partial['4']<=partial['12'])
        close(arm+'_prefix12_total_loss',partial['12'],summary['official_weighted_loss'])
    close('baseline_reference_reproduction',result['baseline_reproduced'],73.71410733861434,1e-9)
    delta=result['two_stage_OOF']-result['baseline_reproduced'];close('paired_delta',delta,result['OOF 分数差']);close('paired_delta_alias',delta,result['分数差'])
    for i,(b,c,d) in enumerate(zip(result['baseline_fold_scores'],result['candidate_fold_scores'],result['paired_fold_deltas']),1):close('paired_fold_delta_'+str(i),c-b,d)
    close('contribution_net_delta',math.fsum(x['net_official_points'] for x in result['error_contributions']),delta)
    check('route_counts_partition',result['routing_counts']['total_rows_routed']==0 and result['routing_counts']['unrouted_rows']==972 and result['routing_counts']['target_zero_rows']==12)
    check('candidate_predictions_identity_logically',result['baseline_summary']==result['candidate_summary'] and result['baseline_fold_scores']==result['candidate_fold_scores'])
    check('R3_locked_decision_row',result['decision_row_B_self_report']=='| 分数差 ≤ 0 | 路线 B 淘汰 |' and delta<=0)
    for k in ['test_tables_parsed','test_predictions_generated','model_weights_loaded','model_weights_saved','submission_packages_created','platform_submissions']:check('forbidden_action_count_'+k,result[k]==0)
    check('test_labels_not_parsed',result['test_labels_read'] is False and structure['test_tables_parsed']==0)
    check('old_local_freeze_B_record_preserved',all(result['integrity'][k] for k in ['protected_old_files_unchanged','archive_and_manifest_unchanged','private_config_unchanged']))
    check('historical_dtype_unknown_not_fabricated',result['historical_dtype']==lock['historical_dtype']=='UNKNOWN')
    # Verify every privacy record against the exact delivered file inventory.
    records=scan['records'];check('privacy_exact31_coverage',scan['published_files']==scan['scan_records']==len(records)==len(files)==31)
    check('privacy_no_duplicate_record_paths',len({r['path'] for r in records})==len(records) and len({r['record_id'] for r in records})==len(records))
    check('privacy_exact_file_path_set',{r['path'] for r in records}=={PREFIX+n for n in files})
    for row in records:
        name=row['path'][len(PREFIX):]
        check('privacy_zero_hits_'+name,row['result']=='PASS' and row['credential_or_private_path_hits']==0 and all(x==0 for x in row['private_marker_hits'].values()))
        if name in ['PRIVACY_SCAN_RAW.json','SHA256SUMS.json']:check('privacy_self_hash_not_fabricated_'+name,row['sha256'] is None and row['bytes'] is None)
        else:check('privacy_file_hash_binding_'+name,row['sha256']==hash_file(BROOT/name) and row['bytes']==(BROOT/name).stat().st_size)
    check('privacy_no_exemptions',scan['exemptions']==0 and scan['all_pass'] is True and scan['test_CSVs_parsed']==scan['test_label_columns_read']==0)
    coverage=(BROOT/'PRIVACY_COVERAGE_MAP.md').read_text(encoding='utf-8-sig')
    check('privacy_mapping_all_records',all(row['path'] in coverage and row['record_id'] in coverage for row in records))
    # Read-only source assertions: contextual inspection, not a true-data replay.
    runner=(BROOT/'run_b2.py').read_text(encoding='utf-8-sig');tree=ast.parse(runner)
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {'fit','fit_transform'}]
    check('exact_three_actual_fit_call_sites',len(calls)==3)
    check('all_fit_calls_are_budgeted_callbacks',all(any(isinstance(a,ast.Lambda) and n in list(ast.walk(a)) for outer in ast.walk(tree) if isinstance(outer,ast.Call) and isinstance(outer.func,ast.Name) and outer.func.id=='fit_call' for a in outer.args) for n in calls))
    check('no_full_training_save_or_test_calls',not re.search(r'\b(?:train_final|run_training|joblib\.(?:dump|load)|_build_test_panel|load_test|predict_test)\s*\(',runner))
    check('inner_loss_uses_inner_validation', 'positive_inner_loss(train.iloc[iva],ip)' in runner and 'fit_reg(train.iloc[itr],train.iloc[iva]' in runner)
    check('outer_shared_prep_classifier_reuse','clf.fit(xt,label)' in runner and 'pipe.named_steps[\'preprocess\'].transform(valid[features])' in runner)
    check('no_threshold_grid_or_calibration',not re.search(r'\b(?:GridSearchCV|CalibratedClassifierCV|linspace|RandomizedSearchCV)\b',runner))
    requirements=dict(line.strip().split('==') for line in (BROOT/'requirements-b2.txt').read_text().splitlines() if line.strip())
    check('requirements_lock21_versions',requirements==load('ENVIRONMENT_LOCK.json')['versions'] and len(requirements)==21)
    binding={'B_commit':B,'B_snapshot':'09f74e2e980c7d1f7951bad6fe69efd82f64f010','all_old_public_blobs_unchanged':True,'old_public_files':len(old),'B_new_files':len(files),'diff_files':changes}
    write_new('PUBLIC_TREE_DIFF_CODEX.json',binding)
    output={'task':'A2B-026/路线B-B2','role':'Codex / Account A2','reviews_commit':B,'Claude_instruction_archive_commit':'088a71ae8760a57272f68cc2cb538b0a8eecc288','checks_passed':len(checks),'checks':checks,
            'aggregate_recalculation':{'baseline':result['baseline_reproduced'],'candidate':result['two_stage_OOF'],'delta':delta,'outer_validation_wells':val_counts,'fold_std_ddof0':statistics.pstdev(result['baseline_fold_scores']),'tau_range':[min(x['tau'] for x in folds),max(x['tau'] for x in folds)]},
            'fit_ledger_reconstruction':{'events':len(events),'counts':running,'lock_before_first_fit':True,'baseline_before_all_inner_or_classifier_fits':True,'all_tau_before_classifier':True},
            'privacy':{'public_files':31,'all_records_bound':True,'marker_inventory_independently_accessed':False,'B_marker_counts':scan['marker_counts'],'self_metadata_binding_verified':True},
            'historical_dtype':'UNKNOWN','A_actual_model_fits':0,'A_actual_preprocessor_fits':0,'A_raw_data_read':False,'real_OOF_retraining_or_row_level_recalculation':False,
            'evidence_scope':'Independent aggregate/source/ledger checks; actual training and immutable local-file verification are B execution records, not a new A real-data run.'}
    write_new('RECORD_AUDIT_CODEX.json',output)
    print(json.dumps({k:v for k,v in output.items() if k in ['checks_passed','fit_ledger_reconstruction','aggregate_recalculation']}))

if __name__=='__main__':main()
