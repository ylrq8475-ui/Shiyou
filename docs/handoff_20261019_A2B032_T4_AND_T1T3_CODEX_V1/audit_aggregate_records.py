"""Audit public frozen records and aggregate arithmetic, no real-data execution."""
import ast, hashlib, json, math
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent;B=ROOT/'sources/B032'
checks=[]
def check(name,condition):
    checks.append({'name':name,'pass':bool(condition)})
    assert condition,name
def get(name):return json.loads((B/name).read_bytes())
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=get('SHA256SUMS.json')['files'];names={p.name for p in B.iterdir() if p.is_file()}
check('B_file_count',len(names)==22)
check('manifest_coverage',len(manifest)==21 and {Path(x['path']).name for x in manifest}==names-{'SHA256SUMS.json'})
for r in manifest:
    name=Path(r['path']).name;b=(B/name).read_bytes()
    check('B_manifest/'+name,len(b)==r['bytes'] and sha(b)==r['sha256'])
privacy=get('PRIVACY_SCAN_RAW.json');records=privacy['records']
check('privacy_all_files_covered',len(records)==privacy['published_files']==privacy['scan_records']==22 and {Path(r['path']).name for r in records}==names)
check('privacy_no_exemptions',privacy['exemptions']==0 and privacy['all_pass'])
for r in records:
    name=Path(r['path']).name
    check('privacy_record/'+name,r['result']=='PASS' and sum(r['private_marker_hits'].values())==0 and r['credential_or_private_path_hits']==0)
    if r['sha256'] is not None:
        check('privacy_digest/'+name,sha((B/name).read_bytes())==r['sha256'] and len((B/name).read_bytes())==r['bytes'])
    else:check('privacy_metadata_self_binding/'+name,name in {'SHA256SUMS.json','PRIVACY_SCAN_RAW.json'} and bool(r['identity_binding']))
lock=get('IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json');result=get('RESULT_A2B032.json');source=get('SOURCE_RECEIPT.json')
for name,digest in lock['source_hashes'].items():check('implementation_lock/'+name,sha((B/name).read_bytes())==digest)
check('R9_copy_bytes',(B/'CLAUDE_INSTRUCTION_ORIGINAL_R9.md').read_bytes()==(ROOT/'sources/r9').read_bytes())
check('R9_hash',source['R9_sha256']=='50d8517264c1f225b3984b3f19a45cf3228613bdd8e98851e95831951c500fc6')
check('input_identity_records',lock['input_hashes']==source['input_hashes']==result['integrity']['input_hashes_before']==result['integrity']['input_hashes_after'])
check('read_boundary_receipt',get('READ_BOUNDARY_AND_INTEGRITY.json')['read_boundary']==result['read_boundary'])
check('zero_counts',get('ZERO_FIT_COUNTS.json')==result['fit_counts'] and all(v==0 for v in result['fit_counts'].values()))
for group,n in [('T1',10),('T2',81)]:
    for key in ('k_start','k_end'):check(group+'/'+key+'/denominator',sum(result[group][key].values())==n)
def unique_mode(d):
    m=max(d.values());r=[int(k) for k,v in d.items() if v==m];return r
for group in ['T1','T2']:
    for key in ['k_start','k_end']:check(group+'/'+key+'/unique_mode',unique_mode(result[group][key])==[1])
check('k_end_all_one',result['T1']['k_end']=={'1':10} and result['T2']['k_end']=={'1':81})
check('ALIGN_recomputed',result['ALIGN_MATCH'] is False and result['test_joint_modal_wells']==6 and result['T1']['k_start']['1']<8)
check('template_pre_month',result['T1']['last_pretemplate_row_equals_T0_minus_1_wells']==10)
check('no_gap',result['T1']['gap_wells']==0 and not result['T1']['gap_month_count_distribution'])
check('finite_exact_months',result['T1']['T0_minus_1_RCYL_finite_wells']==result['T1']['M_RCYL_finite_wells']==10)
for key in ('P1','P2'):
    r=result['T3'][key];s=r['all_well_score'];loss=s['monthly_weighted_loss']
    check(key+'/cohort',r['valid_wells']==r['well_denominator']==81 and r['status']=='COMPLETE')
    check(key+'/score_identity',math.isclose(s['official_score'],100*(1-loss['m1_to_12']),rel_tol=0,abs_tol=1e-12))
    check(key+'/prefix_monotone',0<=loss['m1_to_1']<=loss['m1_to_2']<=loss['m1_to_4']<=loss['m1_to_12']<=1)
    check(key+'/topline',s['official_score']==result[key])
check('P2_minus_P1',result['P2']-result['P1']==result['P2_minus_P1']==result['T3']['P2_minus_P1'])
p3=result['T3']['P3'];s=p3['score']['all_well_score']
check('P3_trigger',not result['ALIGN_MATCH'] and p3['k_start_star']==1)
check('P3_identity',p3['redefined_target_P1_reference']==p3['score'] and p3['P3_minus_redefined_target_P1']==0)
check('P3_full_cohort',p3['complete_redefined_target_wells']==81)
check('P3_score',s['official_score']==result['P3'] and math.isclose(s['official_score'],100*(1-s['monthly_weighted_loss']['m1_to_12']),abs_tol=1e-12))
check('P3_different_target_not_gain',p3['cross_target_difference_is_model_gain'] is False)
for row in result['T3']['frozen_official_scorer_cross_checks']:check('recorded_scorer/'+row['name'],row['well_count']==81 and row['difference_vs_local_formula']==0)
boundary=result['read_boundary'];dec=boundary['test_decoder_aggregate']
check('test_window_decode_zero',boundary['test_window_dynamic_values_decoded']==boundary['test_window_RCYL_parsed']==boundary['test_window_other_fields_used']==0)
check('decoder_cell_accounting',dec['test_window_rows_skipped_before_dynamic_cell_decode']==120 and dec['decoded_cells']['key_date']==493 and dec['decoded_cells']['prewindow_RCYL']==373)
check('no_full_test_parse',boundary['test_history_tables_full_parsed']==0 and boundary['plan_layer_tables_parsed']==0)
for filename in ['run_audit.py','audit_core.py','privacy_check.py']:
    tree=ast.parse((B/filename).read_text(encoding='utf-8'))
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {'fit','fit_transform','partial_fit'}]
    check('no_fit_calls/'+filename,not calls)
    imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]+[a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
    check('no_ML_imports/'+filename,not any(x.startswith(('sklearn','torch','xgboost','lightgbm','catboost')) for x in imports))
    compile((B/filename).read_text(encoding='utf-8'),filename,'exec')
src=(B/'run_audit.py').read_text(encoding='utf-8')
check('template_identity_before_dynamic_access',src.index("require(fingerprint(allkeys)==EXPECTED_KEYS")<src.index('pre,audit=permitted_test_history'))
check('training_testing_disjoint_guard',"not train_ids&test_ids" in src)
core=(B/'audit_core.py').read_text(encoding='utf-8')
check('skip_before_dynamic_decode',core.index('if month>=origin:')<core.index('wid=cell(raw'))
card=(B/'REPORT_B.md').read_text(encoding='utf-8').split('# 账户B执行与交付')[0]
for field in ['任务编号/阶段','角色','分支','完整提交号','目录路径','结果文件路径','关键数字','硬门禁结论','UNKNOWN 与未关闭项','对应决策表行','所依据的 Claude 指令存档提交号']:check('registration/'+field,field in card)
index=json.loads((ROOT/'sources/index').read_bytes());record=[r for r in index['entries'] if r['role']=='B' and r['task'].startswith('A2B-032')][-1]
check('latest_B_identity',record['commit']=='094ebcd2b6b323849fce9c5cb1daf3e6b9228b41')
out={'checks':checks,'checks_passed':len(checks),'all_pass':True,'B_published_files_verified':22,'B_privacy_record_count':22,'B_privacy_hashes_bound':20,'B_privacy_self_metadata_records':2,'A_real_rows_recomputed':False,'A_model_fits':0,'A_preprocessor_fits':0,'B_reported_model_fits':0,'B_reported_preprocessor_fits':0,'scope':'Public records, arithmetic, static source and synthetic verification; no private marker rescan or real per-well recomputation'}
with (ROOT/'AGGREGATE_REVIEW_CODEX.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='checks'},ensure_ascii=False))
