import json,hashlib,ast
from pathlib import Path
R=Path(__file__).resolve().parent;checks=[]
def read(p):return json.loads((R/p).read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ck(label,ok):checks.append({'check':label,'pass':bool(ok)})
for f in read('sources/SHA256SUMS.json')['files']:ck('published:'+Path(f['path']).name,sha(R/'sources'/Path(f['path']).name)==f['sha256'])
manifest=read('sources/SOURCE_BUNDLE_MANIFEST.json')
print('manifest_keys',list(manifest))
for m in manifest['files']:ck('bundle:'+m['path'],sha(R/'bundle'/m['path'])==m['sha256'])
lock=read('sources/INCREMENT_LOCK.json');ck('lock_exact_sha',sha(R/'sources/INCREMENT_LOCK.json')=='81d77e8147910352ee29c68d46911a6d00026ff051e325b81624234af6de461a');ck('public_and_runtime_lock', (R/'sources/INCREMENT_LOCK.json').read_bytes()==(R/'bundle/source/INCREMENT_LOCK.json').read_bytes())
for name,h in lock['files'].items():ck('locked:'+name,sha(R/'bundle'/name)==h)
prior=R.parent/'CODEX_A2B035_SEARCH_REVIEW_20261020/bundle/source'
for p in (R/'bundle/source/base').rglob('*'):
 if p.is_file() and (prior/p.relative_to(R/'bundle/source/base')).is_file():ck('inherited:'+p.relative_to(R/'bundle/source/base').as_posix(),p.read_bytes()==(prior/p.relative_to(R/'bundle/source/base')).read_bytes())
scan=read('sources/PRIVACY_SCAN_RAW.json');print('scan_keys',list(scan))
for x in scan['records']:
 ck('scan_pass:'+x['path'],x['result']=='PASS')
 if x.get('sha256'):ck('scan_identity:'+x['path'],sha(R/'sources'/Path(x['path']).name)==x['sha256'])
 for m in x.get('source_ZIP_members',[]):ck('scan_member:'+m['path'],sha(R/'bundle'/m['path'])==m['sha256'] and m['result']=='PASS')
result=read('sources/RESULT_R14_PREPARATION.json');f=read('sources/FIT_ACCOUNTING.json');syn=read('sources/SYNTHETIC_R14.json');ck('B_50_cases',syn['assertion_case_count']==50 and sum(x['cases'] for x in syn['checks'])==50 and all(x['PASS'] for x in syn['checks']));ck('B_zero_fits',all(result['fit_counts'][k]==0 for k in ['competition_model_fits','competition_preprocessor_fits','synthetic_ET_fits','synthetic_external_model_fits','synthetic_external_preprocessor_fits','total_new_model_fits','total_new_preprocessor_fits']));ck('B_no_B0_rebuild',result['B0_standalone_rebuild_uploads']==result['platform_uploads']==result['new_formal_packages']==0)
pre=read('sources/PREFLIGHT_R14.json');ck('six_H_panels',len(pre['H_variants'])==6 and all(x['rows']==972 and x['wells']==81 and x['base325_and_target_keys_identical_to_B0prime'] for x in pre['H_variants']));ck('zero_test_distribution',pre['test_CSVs_parsed']==pre['test_input_distribution_comparisons']==0)
for p in (R/'bundle/source').rglob('*.py'):ast.parse(p.read_bytes());ck('syntax:'+str(p.relative_to(R/'bundle')),True)
e=read('sources/EXTERNAL_ADMISSION_EVIDENCE.json');ck('external_not_executed_not_released',e['actual_external_adapter_fit_or_inference_checks'].startswith('NOT_EXECUTED') and e['external_competition_release'] is False and e['synthetic_model_fits']==0)
out={'reviews_commit':'f252407dba3af7b3800c8242518c8e156ad04a42','checks_total':len(checks),'failed':[x for x in checks if not x['pass']],'all_pass':all(x['pass'] for x in checks),'B_synthetic_case_count':50,'B_preflight_scope':'bound source and aggregate records, not independent raw data replay','A_raw_reads':0,'A_model_fits':0,'A_preprocessor_fits':0,'B0_standalone_execution':'not observed in reviewed entry paths and bound B zero counts; no claim to global B process inventory'}
(R/'EVIDENCE_REVIEW.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
