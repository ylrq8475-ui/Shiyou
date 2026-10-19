"""Public-record identities, exact source binding and aggregate-only arithmetic."""
import ast,base64,hashlib,json,math,statistics
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent;B=ROOT/'sources/B033';checks=[]
OUTPUT=ROOT/'verification_output';OUTPUT.mkdir(exist_ok=True)
def get(n):return json.loads((B/n).read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def check(n,v):checks.append({'check':n,'pass':bool(v)});assert v,n
files={p.name for p in B.iterdir() if p.is_file()};manifest=get('SHA256SUMS.json')['files']
check('published_file_count',len(files)==35)
check('manifest_coverage',len(manifest)==34 and {Path(x['path']).name for x in manifest}==files-{'SHA256SUMS.json'})
for r in manifest:
    n=Path(r['path']).name;b=(B/n).read_bytes();check('manifest/'+n,sha(b)==r['sha256'] and len(b)==r['bytes'])
scan=get('PRIVACY_SCAN_RAW.json');check('privacy_coverage',scan['published_files']==scan['scan_records']==len(scan['records'])==35 and {Path(x['path']).name for x in scan['records']}==files)
check('no_scan_exemptions',scan['exemptions']==0 and scan['all_pass'])
for r in scan['records']:
    n=Path(r['path']).name;check('scan_result/'+n,r['result']=='PASS' and sum(r['private_marker_hits'].values())==0 and r['credential_or_private_path_hits']==0)
    if r['sha256'] is not None:check('scan_identity/'+n,sha((B/n).read_bytes())==r['sha256'] and len((B/n).read_bytes())==r['bytes'])
    else:check('metadata_self_binding/'+n,n in {'SHA256SUMS.json','PRIVACY_SCAN_RAW.json'} and bool(r['identity_binding']))
check('R10_copy',(ROOT/'sources/r10').read_bytes()==(B/'CLAUDE_INSTRUCTION_ORIGINAL_R10.md').read_bytes())
check('T4_copy',(ROOT/'sources/T4_result').read_bytes()==(B/'RECEIVED_CODEX_T4.json').read_bytes())
plan=get('PLAN_R10.json');lock=get('IMPLEMENTATION_PREFIT_LOCK.json');r=get('RESULT_A2B033.json');structure=get('STRUCTURE_GATES.json');receipt=get('SOURCE_RECEIPT.json')
check('instruction_identity',plan['R10_sha256']==receipt['R10_sha256']==sha((ROOT/'sources/r10').read_bytes())=='703ed8265078abac88128c8422ce39f815acb62ac22e66a2812c95cb010107c3')
check('T4_identity',receipt['T4_result_sha256']==sha((ROOT/'sources/T4_result').read_bytes()))
for path,digest in lock['source_sha256'].items():
    rel=path.removeprefix('source/');check('prefit_source/'+path,sha((B/rel).read_bytes())==digest)
check('environment_identity',sha((B/'ENVIRONMENT_LOCK.json').read_bytes())==lock['environment_sha256'])
bundle=get('FROZEN_SOURCES.json');historical=json.loads((ROOT/'BASELINE_SOURCE_IDENTITY_CODEX.json').read_bytes());historical_by_path={x['path']:x for x in historical};source_id=[]
check('public_original_module_count',len(bundle['files'])==10)
for row in bundle['files']:
    b=row['text'].encode();old=historical_by_path[row['path']];original=(ROOT/'sources/baseline'/Path(row['path']).name).read_bytes()
    check('embedded_original/'+row['path'],len(b)==row['bytes'] and sha(b)==row['sha256'] and b==(B/row['path']).read_bytes()==original)
    check('old_git_blob/'+row['path'],hashlib.sha1(b'blob '+str(len(original)).encode()+b'\0'+original).hexdigest()==old['git_blob'])
    source_id.append({'path':row['path'],'commit':old['commit'],'sha256':sha(b),'git_blob':old['git_blob'],'bytes':len(b),'matches_embedded_B_source':True})
inner=scan['decoded_source_container_entries'];check('inner_privacy_count',len(inner)==scan['decoded_source_container_entries_count']==10)
for row in inner:
    b=(B/row['path']).read_bytes();check('inner_privacy/'+row['path'],sha(b)==row['sha256'] and len(b)==row['bytes'] and row['result']=='PASS' and sum(row['private_marker_hits'].values())==0 and row['credential_or_private_path_hits']==0)
params=lock['model_params']
for k,v in {'n_estimators':400,'min_samples_leaf':6,'max_features':.75,'random_state':20260916,'n_jobs':-1}.items():check('model/'+k,params[k]==v)
check('feature_schema_count',len(lock['ordered_feature_dtypes'])==325 and len({x[0] for x in lock['ordered_feature_dtypes']})==325)
check('same_feature_order_hash',lock['baseline_identity']['feature_order_sha256']==lock['candidate_identity']['feature_order_sha256']==structure['candidate_identity']['feature_order_sha256'])
check('same_current_dtype_hash',lock['baseline_identity']['feature_dtype_sha256']==lock['candidate_identity']['feature_dtype_sha256'])
check('target_identity',lock['baseline_identity']['label_key_frame_sha256']==lock['candidate_identity']['label_key_frame_sha256']=='4e7db99d009ade76143f37ceed1a5370f0997e328cd77ee97e1f530aca4fbcda')
check('same_split_identity',lock['split_sha256']==structure['split_sha256']=='beadb191d075afdd138d6463f0b3a0e03999a76e07641f56ea24ec77e5e4d5f8')
check('structural_cutoff_checks',structure['cutoff_feature_checks']==29079 and structure['raw_last_RCYL_checks']==81 and structure['future_sensitive_feature_count']==0)
check('cohort_unchanged',structure['cohort']['included_wells']==81 and structure['cohort']['target_rows']==972 and structure['target_window_unchanged'])
ledger=get('FIT_LEDGER.json');counts=get('FIT_COUNTS.json');check('fit_counts_binding',counts==r['fit_counts']=={k:v for k,v in ledger.items() if k!='events'})
for k in ['models_entered','models_completed','preprocessors_entered','preprocessors_completed']:check('fit_count/'+k,counts[k]==5)
check('budget_no_failure_no_retry',counts['failures']==counts['retries']==0 and counts['max_models']==7 and len(ledger['events'])==20)
for i,event in enumerate(ledger['events']):check('ledger_sequence/'+str(i),event['sequence']==i+1)
for fold in range(1,6):
    events=ledger['events'][(fold-1)*4:fold*4]
    check('ledger_scope/'+str(fold),[e['event'] for e in events]==['preprocessor_entered','preprocessor_completed','model_entered','model_completed'] and all(e['stage']==f'OOF-{fold}' for e in events))
    check('ledger_time/'+str(fold),[datetime.fromisoformat(e['time']) for e in events]==sorted(datetime.fromisoformat(e['time']) for e in events))
folds=[get(f'FOLD_{i}.json') for i in range(1,6)];sizes=[17,16,16,16,16]
check('equal_well_aggregate',math.isclose(sum(f['official_score']*n for f,n in zip(folds,sizes))/81,r['score'],abs_tol=1e-12,rel_tol=0))
check('total_delta',r['score']-r['baseline']==r['delta'])
check('P2_delta',r['score']-r['P2_reference']==r['relative_to_P2'])
check('positive_folds',sum(v>0 for v in r['paired_fold_deltas'])==r['positive_folds']==3)
check('worst_fold',min(r['fold_scores'])==r['worst_fold'])
check('population_std',math.isclose(statistics.pstdev(r['fold_scores']),r['fold_standard_deviation_population'],abs_tol=1e-12,rel_tol=0))
for i,f in enumerate(folds):
    check('fold_score/'+str(i),f['official_score']==r['fold_scores'][i] and f['paired_delta']==f['official_score']-r['baseline_fold_scores'][i]==r['paired_fold_deltas'][i])
    check('fold_size/'+str(i),f['wells']==sizes[i] and structure['folds'][i]['valid_wells']==sizes[i] and structure['folds'][i]['well_overlap']==0)
    check('fold_fit_count/'+str(i),f['fit_counts']['models_completed']==f['fit_counts']['preprocessors_completed']==i+1)
    check('fold_metric_identity/'+str(i),math.isclose(100*(1-f['weighted_losses']['m1_to_12']),f['official_score'],abs_tol=1e-12,rel_tol=0) and f['official_cross_check_difference']==0)
for key,value in r['weighted_losses'].items():check('prefix_equal_well_aggregate/'+key,math.isclose(sum(f['weighted_losses'][key]*n for f,n in zip(folds,sizes))/81,value,abs_tol=1e-12,rel_tol=0))
check('loss_score_identity',math.isclose(100*(1-r['weighted_losses']['m1_to_12']),r['score'],abs_tol=1e-12,rel_tol=0))
check('gate_stops',r['delta']>=1 and r['positive_folds']<4 and not r['step1_passed'] and r['status']=='STOPPED_AT_STEP1_GATE')
check('step2_not_triggered',r['step2']=='NOT_STARTED' and r['step2_outputs']['full_model_fits']==r['step2_outputs']['clean_environment_model_fits']==0)
for key in ['result_zip_sha256','submission_code_zip_sha256','submission_code_zip_bytes','clean_reproduction_predictions_equal','linter']:check('no_package_acceptance/'+key,r['step2_outputs'][key] is None)
check('no_weights_or_predictions',r['models_saved']==r['test_prediction_rows_generated']==r['platform_submissions']==0)
check('no_prohibited_published_file_types',all(Path(x).suffix in {'.json','.md','.py','.txt'} for x in files))
for name in ['core.py','run_oof.py','fit_ledger.py','train.py','predict.py','csv_projection.py','privacy_check.py']:
    compile((B/name).read_text(encoding='utf-8'),name,'exec');check('script_compiles/'+name,True)
source=(B/'core.py').read_text(encoding='utf-8');oof=(B/'run_oof.py').read_text(encoding='utf-8');fit=(B/'fit_ledger.py').read_text(encoding='utf-8')
check('train_cutoff_filter_assert',"(months<t0)" in source and "CUTOFF_FILTER_FAILED" in source)
check('test_skip_before_pandas',source.index('if month>=t0:skipped+=1;continue')<source.index("frame=pd.read_csv(io.BytesIO(head"))
check('trainfold_fit_scope',"fit_once(panel.iloc[tr]" in oof and "prediction=predict(pipe,panel.iloc[va]" in oof)
check('fit_scope_split',"prep.fit_transform(x,z)" in fit and "model.fit(xx,z)" in fit)
check('release_written_only_if_passed',"if passed:(R/'source/RELEASE_GATE.json')" in oof)
card=(B/'REPORT_B.md').read_text(encoding='utf-8').split('# 账户B执行与交付')[0]
for field in ['任务编号/阶段','角色','分支','完整提交号','目录路径','结果文件路径','关键数字','硬门禁结论','UNKNOWN 与未关闭项','对应决策表行','所依据的 Claude 指令存档提交号']:check('registration/'+field,field in card)
index=json.loads((ROOT/'sources/index').read_bytes());latest=[v for v in index['entries'] if v['role']=='B' and v['task'].startswith('A2B-033')][-1]
check('latest_B_identity',latest['commit']=='e846e2094ced5a71e3550294a15432388664cd5a')
out={'checks':checks,'checks_passed':len(checks),'all_pass':True,'B_published_files_verified':35,'B_privacy_records_covered':35,'B_nested_public_source_privacy_records':10,'historical_public_modules_byte_identical':10,'A_competition_data_read':False,'A_real_OOF_retraining':False,'A_model_fits':0,'A_preprocessor_fits':0,'B_fit_counts_from_bound_records':{'models':5,'preprocessor_pipelines':5,'failed':0,'retried':0},'submission_upload_approval_ready':False,'scope':'public source, bound execution records, aggregate arithmetic; no independent private-file/dtype/marker or row-OOF recomputation'}
for n,obj in [('AGGREGATE_REVIEW_CODEX.json',out),('BASELINE_SOURCE_IDENTITY_CODEX.json',source_id)]:
    with (OUTPUT/n).open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='checks'},ensure_ascii=False))
