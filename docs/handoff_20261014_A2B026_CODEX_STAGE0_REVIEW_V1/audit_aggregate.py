"""Independent public-byte, event, arithmetic and static review. No real entry."""
import ast, hashlib, json, math, re
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
B=ROOT/'sources/B';REF=ROOT/'sources/reference';ROLES=ROOT/'sources/roles'
def load(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
checks=[]
def need(ok,label):
    checks.append({'check':label,'passed':bool(ok)})
    if not ok:raise RuntimeError(label)
def close(a,b,label,tol=1e-11):need(math.isclose(a,b,rel_tol=0,abs_tol=tol),label)

manifest=load(B/'SHA256SUMS.json')
for name,entry in manifest.items():
    need((B/name).stat().st_size==entry['bytes'] and sha(B/name)==entry['sha256'],'B_MANIFEST_'+name)
need(set(p.name for p in B.iterdir() if p.is_file())==set(manifest)|{'SHA256SUMS.json'},'B_EXACT_FILE_SET')
for label,folder in [('roles',ROLES),('proposal',REF)]:
    entries=load(B/'SOURCE_RECEIPT.json')[label]['files']
    for p in folder.rglob('*'):
        if p.is_file():
            n=p.relative_to(folder).as_posix()
            need(n in entries and sha(p)==entries[n]['sha256'] and p.stat().st_size==entries[n]['bytes'],label+'_SOURCE_'+n)
for name in ['diagnostics_reference.py','test_diagnostics_reference.py']:
    need((B/name).read_bytes()==(REF/'reference'/name).read_bytes(),'REFERENCE_BYTES_'+name)
need((B/'PROMPT_CODEX_ORIGINAL.md').read_bytes()==(ROLES/'PROMPT_CODEX.md').read_bytes(),'CODEX_PROMPT_BYTES')
source_manifest=load(REF/'SHA256SUMS.json')
for n in ['PRIMARY_EXPERIMENT_DRAFT.md','reference/diagnostics_reference.py','reference/test_diagnostics_reference.py']:
    need(sha(REF/n)==source_manifest[n]['sha256'],'LOCKED_PROPOSAL_'+n)

r=load(B/'RESULT_STAGE0.json');lock=load(B/'PRE_DIAGNOSTIC_LOCK.json');events=load(B/'EVENTS.json')
for key,name in [('execution_source_sha256','run_stage0.py'),('reference_sha256','diagnostics_reference.py'),
                 ('source_receipt_sha256','SOURCE_RECEIPT.json'),('synthetic_sha256','SYNTHETIC_RESULTS.json'),
                 ('role_and_authorization_sha256','ROLE_AND_AUTHORIZATION.md')]:
    need(lock[key]==sha(B/name),'ACTUAL_PRE_DIAGNOSTIC_BINDING_'+key)
need([e['sequence'] for e in events]==list(range(1,11)),'EVENT_SEQUENCE')
times=[datetime.fromisoformat(e['time']) for e in events]
need(times==sorted(times),'EVENT_TIME_ORDER')
need(events[1]['event']=='synthetic_tests_passed' and events[2]['event']=='competition_data_read_started_after_synthetic_gate','SYNTHETIC_BEFORE_DATA_RECORD')
need(times[2] < datetime.fromisoformat(lock['time']) < times[4],'LOCK_BEFORE_DIAGNOSTIC_SCORES')
for i,e in enumerate(events):need(all(v==0 for v in e['fit_counts'].values()),f'ZERO_FIT_EVENT_{i+1}')
need(all(v==0 for v in r['fit_counts'].values()),'ZERO_FIT_FINAL_RECORD')
for n,key in [('D0_STRUCTURE.json','D0'),('D1_ZERO_MASS.json','D1'),('D2_ANCHOR_COMPARISON.json','D2'),('D4_SMOOTH_ORACLE.json','D4')]:
    need(load(B/n)==r[key],'RESULT_BINDING_'+key)
prior=load(ROOT/'sources/prior_B/PREFIT_LOCK.json')['contract']
need(lock['input_panel_identity']==prior['panel_identity'],'BASELINE_PRIOR_PANEL_IDENTITY')
need(len(prior['feature_order'])==325 and len(set(prior['feature_order']))==325,'PRIOR_325_UNIQUE_ORDERED_FEATURES')
for k in ['feature_order_sha256','feature_dtype_sha256','label_key_frame_sha256']:
    need(lock['candidate_panel_identity'][k]==lock['input_panel_identity'][k],'CANDIDATE_UNCHANGED_'+k)
for side,n in [('train',81),('test',10)]:
    v=r['D0'][side]
    need(v['wells_checked']==n and v['feature_values_checked']==n*359,'D0_'+side+'_COUNT')
    need(v['feature_columns']==325 and v['same_name_and_order_as_B0'] and v['target_and_key_metadata_unchanged'],'D0_'+side+'_STRUCTURE')
    need(v['sensitive_feature_count']==0 and v['feature_key_mismatch_wells']==0 and v['passed'],'D0_'+side+'_INVARIANCE_RECORD')

zero=r['D1'];f=zero['zero_month_fraction_by_horizon'];n=zero['wells']
counts=[round(v*n) for v in f]
for i,(v,c) in enumerate(zip(f,counts)):close(v,c/n,f'ZERO_HORIZON_INTEGER_{i+1}')
close(zero['zero_month_fraction'],sum(counts)/(n*12),'ZERO_FRACTION')
budget=100*sum(c*2**(-(t+1)) for t,c in enumerate(counts))/n
close(budget,zero['max_recoverable_points_if_perfect_zero_detection'],'ZERO_WEIGHT_BUDGET')
need(n==81 and sum(counts)==12 and 1<=zero['wells_with_any_zero_month']<=sum(counts),'ZERO_AGGREGATE_COUNTS')
a=r['D2'];close(a['delta_score_M_minus_M1'],a['anchor_M']['score']-a['anchor_M_minus_1']['score'],'D2_SCORE_DELTA')
close(a['delta_first2_loss_M_minus_M1'],a['anchor_M']['first2_weighted_loss']-a['anchor_M_minus_1']['first2_weighted_loss'],'D2_EARLY_LOSS_DELTA')
need(a['wells_compared']==a['anchor_M']['wells']==a['anchor_M_minus_1']['wells']==64,'D2_COHORT_COUNTS')
oracle=r['D4'];gain=oracle['smooth_plus_zero_oracle_score']-oracle['smooth_oracle_score']
need(0<=gain<=budget+1e-9 and oracle['wells']==81,'D4_ZERO_GAIN_WITHIN_BUDGET')

tree=ast.parse((REF/'reference/diagnostics_reference.py').read_text(encoding='utf-8'))
decision=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DECISION' for t in x.targets))
need(decision==lock['DECISION'],'DECISION_DICTIONARY_UNMODIFIED')
expected={'G_ZERO':'ACTIVATE_ROUTE_B_DESIGN' if budget>=decision['G_ZERO']['activate_route_B_if_points_ge'] else 'ELIMINATE_ROUTE_B' if budget<decision['G_ZERO']['eliminate_route_B_if_points_lt'] else 'KEEP_ROUTE_B_RESERVE',
          'G_INFO':'STAGE1_ELIGIBLE_PENDING_APPROVAL_AND_CODEX_REVIEW' if a['delta_score_M_minus_M1']>=decision['G_INFO']['run_route_A_stage1_if_delta_score_ge'] and a['delta_first2_loss_M_minus_M1']<0 else 'ELIMINATE_ROUTE_A' if a['delta_score_M_minus_M1']<=decision['G_INFO']['eliminate_route_A_if_delta_score_le'] else 'WEAK_OR_UNMET_FIRST2_SIGNAL_NO_AUTOMATIC_EXECUTION',
          'G_CEIL':'95_NOT_CREDIBLE_UNDER_REGISTERED_DIAGNOSTIC_POLICY' if oracle['smooth_plus_zero_oracle_score']<decision['G_CEIL']['declare_95_not_credible_if_smooth_plus_zero_oracle_lt'] else 'SMOOTH_ZERO_GRID_NOT_REJECTED_AT_90'}
for k,v in expected.items():need(r['decisions'][k]==v,'MECHANICAL_'+k)
need(r['decisions']['phase1_executed'] is False and r['phase1_training'] is False and r['models_loaded_or_saved'] is False,'STOP_AT_STAGE0_RECORD')

runner_tree=ast.parse((B/'run_stage0.py').read_text(encoding='utf-8'))
calls=[x for x in ast.walk(runner_tree) if isinstance(x,ast.Call)]
for fn,args in [('zero_month_mass',['targets']),('compare_anchors',['targets','am','am1']),('smooth_oracle_scores',['targets'])]:
    matches=[x for x in calls if isinstance(x.func,ast.Attribute) and isinstance(x.func.value,ast.Name) and x.func.value.id=='d' and x.func.attr==fn]
    need(len(matches)==1 and [ast.unparse(y) for y in matches[0].args]==args,'EXACT_REFERENCE_CALL_'+fn)
need(not any(isinstance(x.func,ast.Attribute) and x.func.attr in {'fit','fit_transform','partial_fit','predict','dump'} for x in calls),'NO_FIT_OR_PREDICT_CALL_IN_REAL_WRAPPER')
names={x.func.id for x in calls if isinstance(x.func,ast.Name)}
need('exec' not in names and 'eval' not in names,'NO_DYNAMIC_EXECUTION')
runner=(B/'run_stage0.py').read_text(encoding='utf-8')
for snippet in ['period <= m','month+1,config','features != prior_lock','cf==features','candidate[meta_cols].equals(original[meta_cols])','periods==m+delta','DUPLICATE_RAW_ANCHOR_MONTH','TARGET_HORIZON_ALIGNMENT','TRAIN_TEST_WELL_OVERLAP']:
    need(snippet in runner,'STATIC_CONTRACT_'+snippet)
source_py_files=[B/'diagnostics_reference.py',B/'test_diagnostics_reference.py']
for p in source_py_files:
    imports=[x for x in ast.walk(ast.parse(p.read_text(encoding='utf-8'))) if isinstance(x,(ast.Import,ast.ImportFrom))]
    imported={a.name for x in imports if isinstance(x,ast.Import) for a in x.names}|{x.module for x in imports if isinstance(x,ast.ImportFrom)}
    need(imported<={'math','numpy','unittest','diagnostics_reference'},'SYNTHETIC_REFERENCE_IMPORT_SCOPE_'+p.name)

privacy=load(B/'PUBLICATION_PRIVACY_CHECK.json');recovery=load(B/'PRIVACY_RECOVERY.json');initial=load(B/'PRIVACY_SCAN.json');stopped=load(B/'STOPPED.json')
need(not initial['passed'] and initial['exact_private_token_hits']==0 and initial['generic_credential_or_user_path_hits']==1,'INITIAL_PRIVACY_FAILURE_PRESERVED')
need(stopped['error_code']=='PRIVACY_GATE_FAILED','INITIAL_STOP_RECORD_PRESERVED')
need(privacy['passed'] and privacy['private_identifier_calendar_candidate_hits']==0 and privacy['credential_and_user_path_hits']==0,'B_RECOVERY_SCAN_RECORD')
need(recovery['actual_execution_source_unchanged'] and recovery['D0_D1_D2_D4_successful_results_recomputed'] is False,'RECOVERY_NO_DIAGNOSTIC_RERUN_RECORD')
secret=re.compile(r'(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|wxid_[A-Za-z0-9]{4,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
hits=[]
for p in B.iterdir():
    if p.is_file() and secret.search(p.read_text(encoding='utf-8-sig')):hits.append(p.name)
need(not hits,'CODEX_INDEPENDENT_PUBLIC_CREDENTIAL_PATTERN_SCAN')
need('github_pat_|wxid_' in runner,'INITIAL_SELF_PREFIX_FALSE_POSITIVE_REPRODUCIBLE')
reference_tests=load(ROOT/'SYNTHETIC_REVIEW_CODEX.json')
need(reference_tests['passed'] and reference_tests['tests_run']==12 and reference_tests['fit_attempts']==0,'CODEX_ACTUAL_12_REFERENCE_TESTS')

summary={'account':'Codex（账户A2）独立审核与交付','task':'A2B-026阶段0',
 'B_fixed_commit':'f482b55d403b8cd36e1a6e30d46a4c976b11baf4','reference_commit':'3256382fb56efecf37f54b4ce3bd4287ffe1f71c',
 'checks':len(checks),'all_passed':True,'B_manifest_files_verified':len(manifest),'B_public_files_retrieved':len(manifest)+1,
 'reference_synthetic_tests':12,'Codex_real_data_read':False,'Codex_real_fits':0,'Codex_B_real_entry_executed':False,
 'real_cohort_counts_and_scores':'B execution evidence; not independently recomputed from raw data',
 'D0_checks_train':r['D0']['train']['feature_values_checked'],'D0_checks_test':r['D0']['test']['feature_values_checked'],
 'D0_sensitive_train':0,'D0_sensitive_test':0,'D1_zero_rows_recomputed_from_aggregates':sum(counts),
 'D1_weight_budget_recomputed':budget,'D2_score_delta_recomputed':a['delta_score_M_minus_M1'],
 'D2_first2_loss_delta_recomputed':a['delta_first2_loss_M_minus_M1'],
 'D2_later_month_score_delta_derived':a['delta_score_M_minus_M1']+100*a['delta_first2_loss_M_minus_M1'],
 'D4_finite_grid_scores':oracle,'D4_ZERO_budget_minus_observed_gain':budget-gain,'mechanical_decisions_recomputed':expected,
 'privacy_exact_marker_scan':'B record 98 identifiers and 78 month tokens; Codex does not have private token inventory',
 'privacy_public_file_count_gap':{'B_record_files':privacy['allowlisted_files_scanned'],'published_files':len(manifest)+1,'per_file_scan_receipt_available':False},
 'B_3261_frozen_file_comparison':'aggregate B claim only; per-file before/after manifest absent in this handoff',
 'B_runtime_dependency_identity':'previous public sources available; current per-module import identity not included',
 'B_publication_return_receipt':'not included; Codex independently retrieved and verified all B published bytes',
 'check_results':checks}
with (ROOT/'AGGREGATE_REVIEW_CODEX.json').open('x',encoding='utf-8') as out:json.dump(summary,out,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in summary.items() if k not in {'check_results','D4_finite_grid_scores'}},ensure_ascii=False))
