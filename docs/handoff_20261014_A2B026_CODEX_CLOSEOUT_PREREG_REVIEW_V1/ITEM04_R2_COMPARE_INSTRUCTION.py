"""Compare fixed instruction archive to actual user-forwarded B R2. No data or fits."""
import difflib,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
R=ROOT/'sources/R2';I=ROOT/'sources/instruction'
OLD=ROOT.parent/'CODEX_A2B026_CLOSEOUT_PREREG_REVIEW_20261014/sources'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def need(ok,label):
    checks.append({'check':label,'passed':bool(ok)})
    if not ok:raise RuntimeError(label)
need(sha(I/'INSTRUCTION_ORIGINAL.md')==load(I/'SHA256SUMS.json')['INSTRUCTION_ORIGINAL.md'],'CLAUDE_ORIGINAL_ACTUAL_BYTE_SHA256')
need(load(ROOT/'TREE_SCOPE_PROOF.json')['all_prior_files_unchanged'],'OLD_B_FILES_REMAIN_UNCHANGED')
relation=load(ROOT/'COMMIT_RELATION.json')
need(relation['status']=='ahead' and relation['total_commits']==3,'B213_DESCENDS_FROM_0F4_BY_THREE_COMMITS')
need(len(relation['files'])==12 and all(e['status']=='added' and e['deletions']==0 for e in relation['files']),'TWELVE_NEW_R2_FILES_NO_REPLACEMENT')
for e in load(R/'SHA256SUMS.json')['files']:
    n=Path(e['path']).name
    need(sha(R/n)==e['sha256'] and (R/n).stat().st_size==e['bytes'],'R2_SHA256_'+n)

original=(I/'INSTRUCTION_ORIGINAL.md').read_text(encoding='utf-8-sig')
current=(R/'PREREG_ROUTE_B.md').read_text(encoding='utf-8-sig')
previous=(OLD/'prereg/PREREG_ROUTE_B.md').read_text(encoding='utf-8-sig')
def table(text):
    lines=text.splitlines();start=next(i for i,l in enumerate(lines) if l.lstrip().startswith('| Codex 确认的结果 | 下一步 |'))
    out=[];indent=len(lines[start])-len(lines[start].lstrip(' '))
    for line in lines[start:]:
        if not line.lstrip().startswith('|'):break
        out.append(line[indent:])
    return '\n'.join(out),indent
t_original,indent=table(original);t_current,_=table(current);t_previous,_=table(previous)
need(t_original==t_current,'R2_TABLE_TEXT_EXACT_AFTER_CODE_BLOCK_EMBEDDING_INDENT_REMOVAL')
params=load(R/'PREREG_PARAMETERS.json');result=load(R/'RESULT_B.json')
need(params['decision_table_original']==result['decision_table_original']==t_current,'R2_TABLE_MD_JSON_BINDING')
need('OOF 分数差 ≥ +1.0' in t_original and 'OOF 分数差 ≥ +1.0' in t_current,'ONE_POINT_THRESHOLD_EXACT')
startup_original=next(line.strip() for line in original.splitlines() if line.strip().startswith('启动条件：'))
startup_exact=startup_original in current
quoted_sentence=startup_original.split('：',1)[1]
sentence_exact=quoted_sentence in current
alternatives=[line for line in current.splitlines() if '第11项' in line and any(s in line for s in ['启动','授权','另行批准'])]
need(bool(alternatives),'STARTUP_EQUIVALENT_CONSTRAINTS_PRESENT')
need('阶段B-2需要另行批准，且启动前必须由Codex明确关闭第11项' in current,'STARTUP_AND_LOGIC_PRESENT')
need('建议改动（与正式计划分开）' in current,'SUGGESTIONS_SEPARATE')
need(params['threshold']['grid_search'] is False and params['threshold']['pooled_OOF_selection'] is False and params['threshold']['outer_OOF_selection'] is False,'R2_GRID_REMOVED_NO_OUTER_SELECTION')
need(params['threshold']['formula']=='tau=(1-l_plus)/(2-l_plus)','R2_FORMULA_LOCKED')
need(params['threshold']['zero_route']=='q_zero > tau; equality retains B0','R2_STRICT_GREATER_ROUTING')
need(params['budget_proposed_for_separate_B2_approval']['successful_model_fits_max']==25 and params['budget_proposed_for_separate_B2_approval']['successful_preprocessor_fits_max']==20,'R2_PROPOSED_BUDGET')
fit=load(R/'FIT_COUNTS.json')
for k,v in fit.items():
    if k.endswith(('_entries','_fits','_retries','_loaded','_saved','_submissions','_reruns')):need(v==0,'R2_ZERO_EXECUTION_'+k)
need(result['counts']==fit and result['B2_start_allowed'] is False,'R2_RESULT_COUNT_BINDING')
for n in ['privacy_supplement.py','PRIVACY_SUPPLEMENT_SCAN_RAW.json','HISTORIC_SCAN_SELECTION_RECONSTRUCTED.json']:
    need((R/n).read_bytes()==(OLD/'B'/n).read_bytes(),'R2_IDENTICAL_PREVIOUSLY_REVIEWED_'+n)
old_params=load(OLD/'prereg/PREREG_PARAMETERS.json')
for k in ['regressor','classifier','features','validation','label']:need(old_params[k]==params[k],'UNCHANGED_R1_R2_'+k)
source_receipt=load(R/'SOURCE_RECEIPT_R2.json')
scan=load(R/'PRIVACY_SUPPLEMENT_SCAN_RAW.json')
by_path={e['path']:e for e in scan['files']}
for e in source_receipt['original_24_bindings']:
    need(e['path'] in by_path and e['sha256']==by_path[e['path']]['sha256'] and e['bytes']==by_path[e['path']]['bytes'],'R2_EXISTING_SCAN_BINDING_'+Path(e['path']).name)
static=load(R/'PREREG_STATIC_CHECKS.json')
for e in static['source_formula_checks']:need(abs(e['tau']-(1-e['l_plus_synthetic'])/(2-e['l_plus_synthetic']))<1e-14,'FORMULA_SYNTHETIC_ARITHMETIC_'+str(e['l_plus_synthetic']))

delta=[{'id':'TEXT-1','level':'P3','expected':startup_original,'actual':alternatives,
        'exact_sentence_in_preregistration':sentence_exact,'exact_whole_startup_line_in_preregistration':startup_exact,
        'meaning_changed':False,'description':'startup constraint has equivalent wording, but the required original sentence is not copied verbatim'}] if not startup_exact else []
changes={'decision_table':list(difflib.unified_diff(t_previous.splitlines(),t_current.splitlines(),fromfile='0f4f_R1',tofile='213b_R2',lineterm='')),
 'threshold_method':{'old':'102-item inner OOF score maximization','new':'tau=(1-l_plus)/(2-l_plus), inner-fold positive B0 loss only'},
 'routing_operator':{'old':'>=','new':'>'},'successful_model_fit_budget':{'old':40,'new':25},
 'inner_classifier_fit_budget':{'old':15,'new':0},'preprocessor_budget':{'old':20,'new':20},
 'old_data_model_target_features_folds_unchanged':True}
summary={'task':'CODEX-026B-04','role':'Codex（账户A2）独立补充审核','review_scope':'this item and unreviewed B R2 delta only',
 'reviewed_B_commit':'213b1b465c61d799371e2b4326ebc71922c4f7ee','previous_reviewed_B_commit':'0f4f2295f971fb3d9ff82f31bb5eb2e5b74889f9',
 'instruction_commit':'0536eafab45b71ffd5f8f0160ee7957f1edd661d','instruction_sha256':sha(I/'INSTRUCTION_ORIGINAL.md'),
 'previous_review_covered_B213':False,'current_supplement_covers_B213':True,
 'instruction_original_received_and_verified':True,'previous_P1_missing_source_resolved':True,
 'table_exact_text_match':True,'threshold_one_point_match':True,'source_table_embedding_indent_spaces_ignored':indent,
 'comparison_policy':'remove code-block table embedding indent and LF/CRLF formatting only; retain wording, numbers, symbols and punctuation',
 'startup_exact_match':startup_exact,'startup_meaning_matches':True,
 'item_status':'通过' if startup_exact else '失败','issue_level':None if startup_exact else 'P3',
 'CODEX_026B_04_closed':startup_exact,'UNKNOWN_items':[],
 'item_11_closed':True,'separate_B2_user_approval_in_archive':False,'B2_start_conditions_satisfied':False,
 'B2_approval_scope':'archive explicitly approves no-training closeout/preregistration and still requires separate B2 approval',
 'hard_gates_current_scope':{'泄漏':'通过','错位':'通过','井级隔离':'通过','指标':'通过'},
 'hard_gate_scope':'document-only supplement; previous limited scope inherited, future B2 implementation not verified',
 'differences_against_instruction':delta,'differences_R1_R2':changes,
 'B_commit_relation':{'ancestor':'0f4f2295f971fb3d9ff82f31bb5eb2e5b74889f9','descendant':'213b1b465c61d799371e2b4326ebc71922c4f7ee','intervening_commits':3,'added_files':12,'old_files_changed':0},
 'R2_files_reviewed':[e['path'] for e in relation['files']],
 'checks_passed':len(checks),'check_results':checks,'data_read':False,'model_fits':0,'preprocessor_fits':0,
 'minimal_text_correction':'copy the archived original startup sentence into PREREG_ROUTE_B.md; no method, threshold, budget or training change'}
with (ROOT/'ITEM04_R2_RESULT_CODEX.json').open('x',encoding='utf-8') as out:json.dump(summary,out,ensure_ascii=False,indent=2)
print(json.dumps({k:summary[k] for k in ['checks_passed','instruction_original_received_and_verified','table_exact_text_match','startup_exact_match','startup_meaning_matches','item_status','issue_level','CODEX_026B_04_closed','B2_start_conditions_satisfied']},ensure_ascii=True))
