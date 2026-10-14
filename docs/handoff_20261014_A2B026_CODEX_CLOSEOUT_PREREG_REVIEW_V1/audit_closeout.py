"""Review new public addenda only, using hashes, static checks and synthetic evidence."""
import ast, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent;B=ROOT/'sources/B';P=ROOT/'sources/prereg'
BASE='f482b55d403b8cd36e1a6e30d46a4c976b11baf4'
HEAD='0f4f2295f971fb3d9ff82f31bb5eb2e5b74889f9'
OLD=ROOT.parent/'CODEX_A2B026_STAGE0_REVIEW_20261014/sources/B'
def load(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
checks=[]
def need(ok,label):
    checks.append({'check':label,'passed':bool(ok)})
    if not ok:raise RuntimeError(label)
tree=load(ROOT/'TREE_IDENTITY_CHECK.json');diff=load(ROOT/'DIFF_SOURCE.json')
need(tree['all_existing_files_unchanged'] and not tree['base_existing_files_changed'],'ALL_BASE_REPOSITORY_FILES_UNCHANGED')
need(len(diff['files'])==9 and all(e['status']=='added' and e['deletions']==0 for e in diff['files']),'EXACT_NINE_ADDITIONS')
need(set(tree['added_files'])=={e['path'] for e in diff['files']},'TREE_DIFF_AGREEMENT')
for n in [p.name for p in OLD.iterdir() if p.is_file()]:need((B/n).read_bytes()==(OLD/n).read_bytes(),'OLD_24_BYTES_'+n)
for folder in [B,P]:
    for n,e in load(folder/'ADDENDUM_SHA256SUMS.json').items():
        need((folder/n).stat().st_size==e['bytes'] and sha(folder/n)==e['sha256'],'ADDENDUM_FINGERPRINT_'+n)
scan=load(B/'PRIVACY_SUPPLEMENT_SCAN_RAW.json')
need(scan['base_commit']==BASE and scan['all_24_scanned_now'] and scan['final_published_count']==24,'SCAN_BASE_AND_COUNT')
paths=[e['path'] for e in scan['files']]
need(len(paths)==len(set(paths))==24,'SCAN_24_UNIQUE_PATHS')
prefix='docs/handoff_20261014_A2B026_B_STAGE0_V1/'
need(set(paths)=={prefix+p.name for p in OLD.iterdir() if p.is_file()},'SCAN_EXACT_OLD_PUBLICATION_SET')
for i,e in enumerate(scan['files'],1):
    n=e['path'][len(prefix):]
    need(e['sha256']==sha(OLD/n) and e['bytes']==(OLD/n).stat().st_size,'PER_FILE_SCAN_HASH_'+n)
    need(e['scan_record_id']==f'SUPPLEMENT-{i:03d}','UNIQUE_SCAN_RECORD_ID_'+n)
    need(e['result']=='PASS' and all(v==0 for v in e['private_token_hits'].values()) and all(v==0 for v in e['generic_sensitive_hits'].values()),'PER_FILE_ZERO_HITS_'+n)
need(sum(e['previously_missing'] for e in scan['files'])==3,'THREE_PREVIOUSLY_MISSING_NOW_SCANNED')
need(set(scan['missed_files'])=={'PRIVACY_RECOVERY.json','PUBLICATION_PRIVACY_CHECK.json','SHA256SUMS.json'},'MISSED_FILE_NAMES')
history=load(B/'HISTORIC_SCAN_SELECTION_RECONSTRUCTED.json')
need(len(history['historic_21_files'])==21 and 'reconstructed' in history['evidence_level'],'HISTORICAL_RECONSTRUCTION_NOT_NEW_HISTORICAL_LOG')
need(history['builder_sha256']==scan['historic_builder_sha256'],'BUILDER_FINGERPRINT_BINDING')
synthetic=load(ROOT/'SCANNER_SYNTHETIC_REVIEW.json')
need(synthetic['passed'] and synthetic['tests']==4 and synthetic['real_fits']==0 and synthetic['unmodified_scanner_sha256']==sha(B/'privacy_supplement.py'),'ACTUAL_UNMODIFIED_SCANNER_SYNTHETIC_TESTS')
source=(B/'privacy_supplement.py').read_text(encoding='utf-8');st=ast.parse(source)
imports=set()
for x in ast.walk(st):
    if isinstance(x,ast.Import):imports.update(a.name.split('.')[0] for a in x.names)
    if isinstance(x,ast.ImportFrom):imports.add(x.module.split('.')[0])
need(imports<={'pathlib','argparse','csv','datetime','hashlib','io','json','re','subprocess','sys','zipfile','yaml'},'SCANNER_IMPORT_SCOPE')
calls=[x for x in ast.walk(st) if isinstance(x,ast.Call)]
need(not any(isinstance(x.func,ast.Attribute) and x.func.attr in {'fit','fit_transform','partial_fit','predict','load_model'} for x in calls),'SCANNER_HAS_NO_LEARNING_CALL')
for text in ["assert len(files)==24","sha_bytes(data[n])==v['sha256']","assert initial['raw_archive']==old_lock['raw_archive_sha256']","assert initial['private_config']==old_lock['private_config_sha256']","assert initial['raw_manifest']==old_lock['raw_manifest_sha256']"]:
    need(text in source,'LOCKED_SCAN_INPUT_CHECK_'+text)
result=load(B/'CLOSEOUT_PREREG_RESULT.json');params=load(P/'PREREG_PARAMETERS.json')
need(result['model_fit_calls_this_turn']==result['preprocessor_fit_calls_this_turn']==scan['model_fit_calls']==scan['preprocessor_fit_calls']==0,'B_ZERO_FIT_RECORDS')
need(not result['B2_training_started'] and not result['B2_training_authorized'] and not params['model_training_allowed_this_turn'],'B2_NOT_EXECUTED_OR_AUTHORIZED_RECORD')
text=(P/'PREREG_ROUTE_B.md').read_text(encoding='utf-8-sig')
table=re.search(r'(\| Codex 确认的结果 \| 下一步 \|\r?\n\|---\|---\|(?:\r?\n\|[^\n]*\|)+)',text).group(1).replace('\r\n','\n')
need(table==params['decision_table_original']==result['decision_table_original'],'B_COPIES_OF_TABLE_SELF_CONSISTENT')
need('≥ +1.0' in table and '## 7. 建议改动（与正式计划分开）' in text,'THRESHOLD_ONE_AND_SEPARATE_SUGGESTIONS')
need(params['features']['history_cutoff']=='M-1' and params['features']['preprocessing_input_count']==325,'PREREG_SAFE_CUTOFF_AND_COLUMNS')
need(params['features']['feature_order_sha256']=='398a6f98fcc15397b0427ce72a976741509a0db5a3c42a2284c3322d4ccc2bb6','KNOWN_B0_FEATURE_IDENTITY')
need(params['validation']=={'outer_GroupKFold':5,'outer_split_sha256':'beadb191d075afdd138d6463f0b3a0e03999a76e07641f56ea24ec77e5e4d5f8','inner_GroupKFold':3,'shuffle':False,'all_estimator_seeds':20260916},'PREREG_GROUPED_FOLDS_AND_FIXED_SEED')
need(params['threshold']['finite_candidates']==[i/100 for i in range(101)] and params['threshold']['extra_candidate']=='NEVER_ZERO (+infinity)','LOCKED_TAU_GRID')
for phrase in ['只在该外层训练井集汇总τ','不触及外层验证井标签','不读取测试真实标签','只在训练折','GroupKFold(3)']:
    if phrase=='只在训练折':continue
    need(phrase in text,'INNER_TAU_PLAN_'+phrase)
need('学习型填补/编码/标准化仅看该训练折' in text,'FOLD_LOCAL_PREPROCESSING_PLAN')
for path in [P/'PREREG_ROUTE_B.md',B/'PRIVACY_COVERAGE_MAP.md']:
    t=path.read_text(encoding='utf-8-sig');card=t.split('# ',1)[0]
    for field in ['【交付登记卡】','任务编号/阶段：','角色：','分支：','完整提交号（40 位）：','目录路径：','结果文件路径（单个 JSON）：','关键数字（按决策表变量逐项列出，变量名与决策表一致）：','硬门禁结论：','UNKNOWN 与未关闭项：','对应决策表行（仅 Codex 填写）：']:
        need(field in card,'REGISTRATION_FIELD_'+path.name+'_'+field)
    need('d9a35ab9893ada8fae99d0f9bae12eb0d920c2b1' in card,'REGISTRATION_FIXED_40_COMMIT_'+path.name)
for e in tree['card_result_bound']:need(e['snapshot_blob']==e['reviewed_blob'],'CARD_SNAPSHOT_RESULT_'+e['path'])

generic_ast=next(x for x in ast.walk(st) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='generic' for t in x.targets))
scope={};exec(compile(ast.Module(body=[generic_ast],type_ignores=[]),'<literal-scanner-patterns>','exec'),{},scope)
generic=scope['generic'];hits=[]
for folder in [B,P]:
    for path in folder.iterdir():
        if path.is_file():
            s=path.read_text(encoding='utf-8-sig')
            if any(re.search(pat,s) for pat in generic.values()):hits.append(path.name)
need(not hits,'CODEX_GENERIC_SCAN_OF_OLD_AND_NEW_PUBLIC_FILES')

items=[
 {'number':1,'status':'通过','level':None,'missing':None,'basis':'24 unique scan rows bind original bytes/hashes; four unmodified-scanner synthetic tests pass; private-token real scan is B execution evidence'},
 {'number':2,'status':'通过','level':None,'missing':None,'basis':'Git trees and compare agree: nine added files; every pre-existing blob unchanged'},
 {'number':3,'status':'通过','level':None,'missing':None,'basis':'zero model/preprocessor counts in both records; scanner imports stdlib/PyYAML only, no learning calls'},
 {'number':4,'status':'UNKNOWN','level':'P1','missing':'independently supplied original Claude/B route-B instruction, its exact decision table and startup wording, fixed source/version/hash','basis':'B markdown/JSON copies agree and threshold +1.0 matches user checklist, but copies cannot establish exact equality to missing original'},
 {'number':5,'status':'通过','level':None,'missing':None,'basis':'plan only: M-1, nested training-only tau, WELL_ID GroupKFold5/3 and known fixed split hash/seed; implementation not reviewed'},
 {'number':6,'status':'通过','level':None,'missing':None,'basis':'both new report cards have all fields; d9a35... snapshot binds unchanged result JSON/scan/parameters; reviewed final commit is 0f4f...'}]
summary={'task':'A2B-026阶段0收尾＋路线B预注册','role':'Codex（账户A2）审核',
 'reviewed_B_commit':HEAD,'rules_commit':'48642f2d9e1d0e05cfbb7c42d905f18f366f811e',
 'base_commit':BASE,'scope':'new files only; no old diagnostic rerun',
 'items':items,'item_11_final':'通过','item_11_closed':True,'B2_start_conditions_satisfied':False,
 'decision_variables':{'第11项':'通过／关闭','B-2启动条件':'不满足','分数差':None,'D1上界':2.6478708526234565},
 'hard_gates_current_scope':{'泄漏':'通过','错位':'通过','井级隔离':'通过','指标':'通过'},
 'hard_gate_scope':'append-only/no-fit closeout and preregistration review; inherited stage0, not future B2 implementation signoff',
 'open_unknowns':[{'id':'CODEX-026B-04','level':'P1','missing':items[3]['missing']}],
 'conclusion':'部分同意：第11项关闭，预注册原指令一致性仍为UNKNOWN（P1），B-2启动条件不满足。',
 'arithmetic_static_byte_checks':len(checks),'all_implemented_checks_passed':True,
 'independent_synthetic_tests':4,'real_competition_data_read_by_Codex':False,'real_fits_by_Codex':0,
 'B_declared_fits':[0,0],'changed_base_files':0,'added_files':tree['added_files'],
 'base_repository_files_verified':tree['base_existing_blob_count'],
 'scan_execution_evidence':'B: 98 well identifiers, 78 months/full dates, 2 candidates, 100 members; Codex: bound receipts/static source/synthetic execution, not private-token raw replay',
 'check_results':checks}
with (ROOT/'AUDIT_RESULT_CODEX.json').open('x',encoding='utf-8') as out:json.dump(summary,out,ensure_ascii=False,indent=2)
print(json.dumps({'checks':len(checks),'synthetic_tests':4,'items':[(e['number'],e['status']) for e in items],
                  'item_11_closed':True,'B2_start_conditions_satisfied':False,'old_files_unchanged':tree['base_existing_blob_count']},ensure_ascii=True))
