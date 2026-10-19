"""Source/receipt checks only; never reads competition inputs or fits models."""
import hashlib,json,re,difflib
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent;B=ROOT/'sources/B033s2';S=ROOT/'sources/step1'
def load(n,base=B):return json.loads((base/n).read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(name,condition):checks.append({'check':name,'pass':bool(condition)})
files={p.name:p for p in B.iterdir() if p.is_file()}
check('44 published files',len(files)==44)
manifest=load('SHA256SUMS.json')
check('manifest covers all other 43 files',{Path(x['path']).name for x in manifest['files']}==set(files)-{'SHA256SUMS.json'})
for x in manifest['files']:
    p=files[Path(x['path']).name];check('manifest bytes '+p.name,p.stat().st_size==x['bytes'] and sha(p)==x['sha256'])
privacy=load('PRIVACY_SCAN_RAW.json')
check('44 unique privacy records',len(privacy['records'])==44 and {Path(x['path']).name for x in privacy['records']}==set(files) and len({x['record_id'] for x in privacy['records']})==44)
for row in privacy['records']:
    name=Path(row['path']).name;p=files[name]
    check('B privacy declaration '+name,row['result']=='PASS' and sum(row['private_marker_hits'].values())==0 and row['credential_or_private_path_hits']==0)
    if row['sha256'] is not None:check('privacy exact file identity '+name,sha(p)==row['sha256'] and p.stat().st_size==row['bytes'])
    else:check('metadata no circular hash '+name,name in {'PRIVACY_SCAN_RAW.json','SHA256SUMS.json'})
inner=privacy['decoded_source_container_entries'];frozen=load('FROZEN_SOURCES.json')['files']
check('ten decoded source scan records',len(inner)==len(frozen)==10)
for row in frozen:
    p=B/row['path'];scan=next(x for x in inner if x['path']==row['path'])
    check('frozen decoded bytes '+row['path'],p.read_bytes()==row['text'].encode() and sha(p)==row['sha256']==scan['sha256'] and scan['result']=='PASS')
for name in ['core.py','csv_projection.py','predict.py','FROZEN_SOURCES.json']:
    check('step1 unchanged '+name,(B/name).read_bytes()==(S/name).read_bytes())
for name in ['train.py','fit_ledger.py','test_033.py','requirements.txt']:
    diff=''.join(difflib.unified_diff((S/name).read_text(encoding='utf-8').splitlines(True),(B/name).read_text(encoding='utf-8').splitlines(True),fromfile='step1/'+name,tofile='step2/'+name))
    dp=ROOT/(name.replace('.','_')+'_STEP1_DIFF.txt')
    if dp.exists():assert dp.read_text(encoding='utf-8')==diff
    else:
        with dp.open('x',encoding='utf-8') as f:f.write(diff)
req=lambda p:dict(line.split('==',1) for line in p.read_text().splitlines() if line.strip())
first=load('ENVIRONMENT_FIRST.json');clean=load('ENVIRONMENT_CLEAN.json');requirements=req(B/'requirements.txt');oldreq=req(S/'requirements.txt')
check('21 dependency versions same',len(requirements)==21 and requirements==first['dependencies']==clean['dependencies'])
check('prior requirement versions unchanged',all(requirements[k]==v for k,v in oldreq.items()))
check('runtime fingerprints identical',first==clean and first['python']=='3.13.7')
envcmp=load('ENVIRONMENT_COMPARISON.json');check('B isolated environment declaration',envcmp['new_venv_system_site_packages'] is False and envcmp['prefit_model_fits']==envcmp['prefit_preprocessor_fits']==0)
lock=load('PREFIT_LOCK.json');old=load('IMPLEMENTATION_PREFIT_LOCK.json',S);params=load('MODEL_PARAMETERS.json')
check('all actual model parameters locked',params==lock['model_params']==old['model_params'])
check('candidate panel identity same step1',lock['candidate_identity']==old['candidate_identity'])
check('raw identity same step1',lock['raw_identity']=={('original_config' if k=='config' else k):v for k,v in old['raw_input_hashes'].items()})
for n,v in lock['source_sha256'].items():
    rel=n.removeprefix('package/');p=B/rel
    if p.exists():check('prefit source identity '+rel,sha(p)==v)
check('R11 original exact',sha(B/'INSTRUCTION_ORIGINAL_R11.md')=='407d536923bbbb6c6b03a2da6f686cf7e0321db6143ec63ffbc1cb64c332d414')
auth=load('STEP2_AUTHORIZATION.json');r=load('RESULT_A2B033_STEP2.json')
check('explicit override and original failed gate preserved',auth['step2_explicitly_authorized'] and auth['step1_gate_passed'] is False and auth['positive_folds']==3 and r['original_step1_retain_gate_passed'] is False and r['user_override_recorded'])
ledger=load('FIT_LEDGER_STEP2.json');events=ledger['events']
check('exactly two fits each',all(ledger[k]==2 for k in ['max_models','max_preprocessors','models_entered','models_completed','preprocessors_entered','preprocessors_completed']))
check('zero failed/retried fits',ledger['failures']==ledger['retries']==0)
check('eight chronological actual events',len(events)==8 and [x['sequence'] for x in events]==list(range(1,9)) and [x['time'] for x in events]==sorted(x['time'] for x in events))
for i,stage in enumerate(['full-first','full-clean-reproduction']):
    e=events[i*4:(i+1)*4]
    check('event sequence '+stage,[x['event'] for x in e]==['preprocessor_entered','preprocessor_completed','model_entered','model_completed'] and {x['stage'] for x in e}=={stage})
check('no OOF refits/test fits/platform uploads',r['OOF_refits']==r['test_fits']==r['platform_uploads']==0)
check('cumulative accounting inherited five plus two',r['cumulative_A2B033_models']==r['cumulative_A2B033_preprocessor_pipeline_fits']==7)
for name in ['FULL_FIRST_CLI.json','FULL_CLEAN_CLI.json','PREDICT_FIRST_CLI.json','PREDICT_CLEAN_CLI.json']:
    x=load(name);check('actual CLI exit '+name,x['exit_code']==0 and x['stderr_lines']==0)
    if name.startswith('FULL_'):check('actual CLI fit counts '+name,x['stdout_aggregate']['model_fits']==x['stdout_aggregate']['preprocessor_fits']==1)
    else:check('inference CLI fit counts '+name,x['stdout_aggregate']['model_fits']==x['stdout_aggregate']['preprocessor_fits']==0)
package=load('PRIVATE_CODE_PACKAGE_MANIFEST.json');mapping=load('PUBLIC_CODE_TO_PRIVATE_PACKAGE.json')
check('declared package size crc identity',package['CRC']=='PASS' and package['members']==len(package['members_sha256'])==25 and package['bytes']<5_000_000_000 and package['sha256']==r['submission_code_zip']['sha256'])
for x in mapping['files']:
    check('public/package member '+x['public_file'],x['same_original_bytes'] and sha(B/x['public_file'])==x['sha256']==package['members_sha256'][x['private_package_member']])
for x in frozen:check('original module package binding '+x['path'],x['sha256']==package['members_sha256'][x['path']])
check('private runtime policy binding',package['members_sha256']['runtime_policy.json']==lock['private_policy_sha256'])
repro=load('CLEAN_REPRODUCTION.json');lint=load('LINTER_RESULTS.json')
check('reported actual clean training and exact 120 comparison',repro['train_from_official_raw'] and repro['from_final_code_ZIP'] and repro['rows_compared']==120 and repro['keyed_predictions_exact_equal'] and repro['maximum_absolute_difference']==0)
check('two result ZIP and model hashes identical',repro['first_result_zip_sha256']==repro['clean_result_zip_sha256']==r['result_zip']['sha256'] and repro['first_model_sha256']==repro['clean_model_sha256']==r['model_first']['sha256']==r['model_clean']['sha256']==package['members_sha256']['models/B0_prime.joblib'])
check('ten CSV hashes identical',repro['first_csv_SHA256_anonymous_archive_order']==repro['clean_csv_SHA256_anonymous_archive_order']==lint['first']['CSV_hashes_anonymous_archive_order']==lint['clean']['CSV_hashes_anonymous_archive_order'] and len(repro['first_csv_SHA256_anonymous_archive_order'])==10)
for stage in ['first','clean']:
    x=lint[stage];check('linter '+stage,x['status']=='PASS' and x['files']==10 and x['rows']==120 and x['columns']==['WELL_ID','NY','RCYL'] and x['CRC_passed'] and x['flat_ZIP'] and x['exact_template_keys_dates_order'] and x['duplicate_keys']==x['extra_columns']==x['NaN_Inf_negative']==0)
boundary=load('STRUCTURE_AND_BOUNDARY.json');check('reported actual cutoff identities',boundary['candidate_identity_matches_step1'] and boundary['all_model_parameters_match_step1'] and boundary['training']['raw_last_RCYL_checks']==81 and boundary['test']['test_window_RCYL_parsed']==boundary['test']['test_window_dynamic_values_decoded']==0)
integrity=load('INTEGRITY_AFTER.json');check('B unchanged old/raw statement',integrity['old_files_checked']==178 and integrity['all_old_files_unchanged'] and integrity['raw_members_verified']==100 and integrity['raw_archive_unchanged'] and integrity['raw_copied_or_extracted'] is False)
compare=load('DEPLOYED_B0_AGGREGATE_COMPARISON.json')
check('aggregate comparison counts and monotonic quantiles',sum(compare[k] for k in ['rows_increased','rows_decreased','rows_equal'])==compare['rows']==120 and compare['signed_relative_difference_quantiles']==sorted(compare['signed_relative_difference_quantiles']))
check('platform score only user evidence',compare['platform_score']==86.2003 and compare['platform_score_evidence']=='USER_REPORTED' and compare['used_to_adjust_predictions'] is False)
diff=load('B_COMMIT_DIFF_CODEX.json',ROOT);check('final B commit adds no other paths',diff['head']=='47077ee354a784bdf99444dd19adb7a8dac36d80' and len(diff['files'])==43 and all(x['status']=='added' and x['path'].startswith('docs/handoff_20261019_A2B033_STEP2_B_V1/') for x in diff['files']))
out={'scope':'Public original-byte source and B-receipt cross-checks, not A retraining or direct private ZIP inspection','reviewed_B_commit':'47077ee354a784bdf99444dd19adb7a8dac36d80','checks':checks,'passed':sum(x['pass'] for x in checks),'failed':sum(not x['pass'] for x in checks),'A_model_fits':0,'A_preprocessor_fits':0,'raw_data_read':False,'private_packages_downloaded':False,'README_defect_separate':'CODEX-033-S2-01 P1; these identity checks do not assess interpreter routing'}
with (ROOT/'AGGREGATE_REVIEW_CODEX.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='checks'}));assert out['failed']==0
