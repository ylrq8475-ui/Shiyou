"""R17 fixed anonymous source, package identity and aggregate arithmetic audit; zero fits."""
import ast,json,hashlib,statistics,math,collections
from decimal import Decimal
from pathlib import Path
R=Path(__file__).resolve().parent;checks=[];limits=[]
def rd(p):return json.loads((R/p).read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ck(n,v):checks.append({'check':n,'pass':bool(v)})
def eq(a,b):return math.isclose(a,b,rel_tol=0,abs_tol=1e-9)
for group in ['b0','fusion']:
 src=R/group/'sources';files={p.name for p in src.iterdir() if p.is_file()};manifest=rd(group+'/sources/SHA256SUMS.json')
 ck(group+':coverage',{Path(v['path']).name for v in manifest['files']}==files-{'SHA256SUMS.json'})
 for m in manifest['files']:ck(group+':published:'+Path(m['path']).name,sha(src/Path(m['path']).name)==m['sha256'])
 bundle=rd(group+'/sources/SOURCE_BUNDLE_MANIFEST.json');ck(group+':source_zip',sha(src/bundle['ZIP'])==bundle['ZIP_sha256'])
 for m in bundle['members']:ck(group+':source_member:'+m['path'],sha(R/group/'bundle'/m['path'])==m['sha256'])
 scan=rd(group+'/sources/PRIVACY_SCAN_RAW.json');ck(group+':scan_coverage',len(scan['records'])==len(files)==scan['published_files'] and {Path(m['path']).name for m in scan['records']}==files)
 for m in scan['records']:
  ck(group+':scan:'+Path(m['path']).name,m['result']=='PASS' and all(v==0 for v in m['private_marker_hits'].values()) and m['credential_or_private_path_hits']==0)
  if m.get('sha256'):ck(group+':scan_bytes:'+Path(m['path']).name,sha(src/Path(m['path']).name)==m['sha256'])
  for v in m.get('source_ZIP_members',[]):ck(group+':scan_expanded:'+v['path'],sha(R/group/'bundle'/v['path'])==v['sha256'] and v['result']=='PASS')
 for p in (R/group/'bundle').rglob('*.py'):ast.parse(p.read_bytes());ck(group+':syntax:'+p.as_posix(),True)
 ck(group+':instruction_original',(src/'INSTRUCTION_ORIGINAL_R17.md').read_bytes()==(R/'instruction/sources/INSTRUCTION_ORIGINAL.md').read_bytes())
prior=R.parent/'CODEX_A2B035_R16_REVIEW_20261020/first/bundle/source/base'
for group in ['b0','fusion']:
 for p in (R/group/'bundle/source/base').rglob('*'):
  if p.is_file():ck(group+':prior_core:'+p.relative_to(R/group/'bundle/source/base').as_posix(),p.read_bytes()==(prior/p.relative_to(R/group/'bundle/source/base')).read_bytes())
lock=rd('fusion/sources/SOURCE_LOCK17.json');unheld=[]
for name,h in lock['files'].items():
 p=R/'fusion/bundle'/name
 if not p.exists():p=R/'fusion/sources'/Path(name).name
 if name=='source/run_cv17.py':p=R/'fusion/bundle/review/run_cv17.py'
 if name=='source/synthetic17.py':p=R/'fusion/bundle/review/synthetic17.py'
 if name=='SPEC_F70.json':p=R/'fusion/bundle/variant.json'
 if name=='SPEC_F50.json':p=R/'fusion/bundle/F50/variant.json'
 if p.exists():ck('source_lock:'+name,sha(p)==h)
 else:unheld.append(name)
for m in rd('fusion/sources/FINAL_INTEGRITY17.json')['source_locks']:
 if (R/'fusion/sources'/m['lock']).exists():ck('integrity_lock:'+m['lock'],sha(R/'fusion/sources'/m['lock'])==m['lock_sha256'])
assembl=rd('fusion/sources/ASSEMBLY_IMPLEMENTATION_LOCK17.json');limits.append('package17.py and actual_integration17.py assembly/harness source not included; hashes and bound execution receipts only, not claimed independently source-replayed')
b0=rd('b0/sources/B0_AUDIT_II_RECEIPT.json');b0prior=rd('b0/sources/B0_PRIOR_APPROVED_RECEIPT.json');b0manifest=rd('b0/sources/B0_CODE_MEMBER_MANIFEST.json');env=rd('fusion/sources/ENVIRONMENT17.json');envlock=rd('fusion/bundle/source/base/ENVIRONMENT_LOCK.json')
contract=rd('fusion/bundle/source/base/DATA_CONTRACT.json');b0members={m['path']:m for m in b0manifest['all_members']};b0result=rd('b0/sources/RESULT_B0_AUDITII17.json')
ck('B0_private_policy_bound',b0members['runtime_policy.json']['sha256']==contract['private_policy_sha256'])
ck('B0_packaged_model_bound',b0members['models/model.joblib']['sha256']==b0['new_model_sha256'])
ck('B0_code_size',b0result['package_identity']['code_under_5GB'] and b0result['package_identity']['code_bytes']==2479466<5_000_000_000)
ck('env_exact',all(env[k]==envlock[k] for k in env) and b0['new_runtime']==env and rd('b0/sources/CLEAN_ENVIRONMENT17.json')==rd('fusion/sources/CLEAN_ENVIRONMENT17.json'))
requirements=dict(line.split('==') for line in (R/'b0/bundle/requirements.txt').read_text().splitlines() if line.strip());ck('requirements_21_exact',requirements==env['dependencies'] and len(requirements)==21)
ck('B0_current_upload_SHA',b0['submission_code_zip_sha256']==b0manifest['formal_code_sha256']=='a75ce0e1820001ef2e854a0cee6540a04caa5b1ecadec3d3c433f30ab42e420a' and b0['result_zip_sha256']==b0['reproduced_result_zip_sha256']=='2b4f57169d653d0ca5fc994d2822f6e167e72c5696a1220f83f7c1eaac4a1df1')
ck('B0_from_scratch',b0['status']=='PASS' and b0['new_training_directory'] and not b0['packaged_weights_loaded_in_train'] and b0['result_zip_bytes_identical'])
for m in b0manifest['all_members']:
 if m['public_content_included']:ck('B0_exact_package_member:'+m['path'],sha(R/'b0/bundle'/m['path'])==m['sha256'])
 ck('B0_old_member:'+m['path'],any(x['path']==m['path'] and x['sha256']==m['sha256'] for x in rd('b0/sources/B0_PRIOR_APPROVED_RECEIPT.json')['syntax_check_latest_ZIP']) or not m['path'].endswith('.py'))
ck('B0_model_hash_match',b0['new_model_sha256']==b0prior['main_model_sha256']==b0prior['independent_model_sha256'])
ck('B0_reproduction_stages',all(x['exit_code']==0 for x in b0['stages']) and len(b0['stages'])==2)
ck('B0_synthetic_identity',b0['boundary_mutation_evidence_sha256']==sha(R/'b0/sources/SYNTHETIC17.json'))
def lint(name,z,resultsha):
 ck(name+':linter',z['status']=='PASS' and z['files']==10 and z['rows']==120 and z['columns']==['WELL_ID','NY','RCYL'] and z['exact_template_keys_dates_order'] and z['duplicate_keys']==z['extra_columns']==z['NaN_Inf_negative']==0 and z['flat_ZIP'] and z['CRC_passed'] and z['result_zip_sha256']==resultsha)
 ck(name+':csv_support',len(z['CSV_hashes_anonymous_archive_order'])==10 and sum(x['rows'] for x in z['CSV_hashes_anonymous_archive_order'])==120)
lint('B0',b0['linter'],b0['result_zip_sha256'])
def boundary(name,z):ck(name+':window_boundary',z['template_rows']==120 and z['test_wells']==10 and z['test_window_dynamic_values_decoded']==z['test_window_RCYL_parsed']==0 and z['test_window_rows_skipped']==120 and z['template_key_hash_verified_before_dynamic_access'])
boundary('B0',b0['boundary'])
packages=rd('fusion/sources/PACKAGE_REPRODUCTION_RECEIPTS.json');packageids=[]
for p in packages['versions']:
 name=p['version'];mapping={'F70':('variant.json','README.md'),'F50':('F50/variant.json','F50/README.md')};vpath,rpath=mapping[name]
 ck(name+':configuration',p['configuration']==rd('fusion/bundle/'+vpath));ck(name+':requirements',any(m['path']=='requirements.txt' and m['sha256']==sha(R/'fusion/bundle/requirements.txt') for m in p['members']))
 for m in p['members']:
  local=R/'fusion/bundle'/m['path']
  if m['path']=='variant.json':local=R/'fusion/bundle'/vpath
  if m['path']=='README.md':local=R/'fusion/bundle'/rpath
  if local.exists():ck(name+':actual_code_member:'+m['path'],sha(local)==m['sha256'])
  else:ck(name+':only_private_members_excluded:'+m['path'],m['path'] in ['models/FIT_COUNTS.json','models/MODEL_RECEIPT.json','models/pair.joblib','runtime_policy.json'])
 ck(name+':clean_reproduction',p['code_bytes']<5_000_000_000 and p['code_under_5GB'] and p['exact_ZIP_source_retrain'] and p['result_zip_bytes_identical'] and p['result_zip_sha256']==p['clean_reproduced_result_zip_sha256'] and p['runtime']==env)
 ck(name+':same_pair',p['shared_main_pair_sha256']==p['independent_clean_pair_sha256']==rd('fusion/sources/ACTUAL_FUSION_INTEGRATION17.json')['actual_shared_full_member_pair_sha256'])
 pm={m['path']:m for m in p['members']};ck(name+':policy_member_bound',pm['runtime_policy.json']['sha256']==contract['private_policy_sha256']);ck(name+':weight_member_bound',pm['models/pair.joblib']['sha256']==p['shared_main_pair_sha256'])
 lint(name,p['linter'],p['result_zip_sha256'])
 for i,a in enumerate(p['boundary']):boundary(name+str(i),a)
 ck(name+':clean_stages',all(v['exit_code']==0 for v in p['stages']))
 packageids.append({k:p[k] for k in ['version','configuration','submission_code_zip_sha256','result_zip_sha256','code_bytes']})
ck('shared_pair_across_F70_F50',packages['versions'][0]['shared_main_pair_sha256']==packages['versions'][1]['shared_main_pair_sha256'])
cv=rd('fusion/sources/ALL_CV_RESULTS.json');results=cv['results'];names=['fixed']+['repeat_'+str(i) for i in range(1,6)];comparison={}
for name,res in results.items():
 for sn in names:
  x=res[sn];ref=results['B0'][sn];scores=x['fold_scores'];n=sum(v['validation_wells'] for v in ref['folds'])
  ck(name+sn+':equal_well_score',n==81 and eq(x['score'],sum(a*f['validation_wells'] for a,f in zip(scores,ref['folds']))/81))
  ck(name+sn+':metric',eq(x['score'],100*(1-x['weighted_losses']['m1_to_12'])))
  ck(name+sn+':fold_stats',eq(x['worst_fold'],min(scores)) and eq(x['fold_std_population'],statistics.pstdev(scores)))
  for key in ['m1_to_1','m1_to_2','m1_to_4','m1_to_12']:
   ck(name+sn+':prefix_nonnegative:'+key,0<=x['weighted_losses'][key]<=1)
   if name in ['B0','B0_prime']:ck(name+sn+':prefix_fold:'+key,eq(x['weighted_losses'][key],sum(f['validation_wells']*f['weighted_losses'][key] for f in x['folds'])/81))
  if name in ['B0','B0_prime']:
   ck(name+sn+':well_isolation',all(f['well_overlap']==0 and f['train_wells']+f['validation_wells']==81 for f in x['folds']))
   ck(name+sn+':fold_identity',[f['row_split_sha256'] for f in x['folds']]==[f['row_split_sha256'] for f in ref['folds']])
  else:
   ck(name+sn+':fixed_weight_scope',x['fixed_weights']==rd('fusion/bundle/'+('variant.json' if name=='F70' else 'F50/variant.json')) and x['weight_fits']==0 and x['well_overlap']==0 and x['member_key_alignment'] and x['validation_rows_once'])
   ck(name+sn+':delta',eq(x['delta_to_B0'],x['score']-ref['score']) and eq(x['delta_to_B0_prime'],x['score']-results['B0_prime'][sn]['score']))
 scores=[res['repeat_'+str(i)]['score'] for i in range(1,6)];repeat=res['repeated_summary'];ck(name+':repeat_stats',repeat['repeat_scores']==scores and eq(repeat['mean'],statistics.mean(scores)) and eq(repeat['sample_std'],statistics.stdev(scores)) and eq(repeat['standard_error'],statistics.stdev(scores)/math.sqrt(5)))
 for k in ['m1_to_1','m1_to_2','m1_to_4','m1_to_12']:ck(name+':repeat_prefix:'+k,eq(repeat['weighted_loss_means'][k],statistics.mean(res['repeat_'+str(i)]['weighted_losses'][k] for i in range(1,6))))
 comparison[name]={'fixed':res['fixed']['score'],'repeat_mean':repeat['mean'],'repeat_SE':repeat['standard_error'],'delta_repeat_to_B0':repeat['mean']-results['B0']['repeated_summary']['mean'],'delta_repeat_to_B0_prime':repeat['mean']-results['B0_prime']['repeated_summary']['mean'],'early2_score_gain_to_B0':100*(results['B0']['repeated_summary']['weighted_loss_means']['m1_to_2']-repeat['weighted_loss_means']['m1_to_2']),'positive_seeds_to_B0':sum(scores[i]>results['B0']['repeated_summary']['repeat_scores'][i] for i in range(5))}
ck('baseline_fixed_exact',results['B0']['fixed']['score']==73.71410733861434 and results['B0_prime']['fixed']['score']==76.33261832127738)
accounts=rd('fusion/sources/FIT_EVENTS_ALL17.json');parts={v['scope']:v['counts'] for v in accounts['parts']};stagecounts={}
for name,counts in parts.items():
 stages=collections.defaultdict(list)
 for i,event in enumerate(counts['events'],1):ck(name+':seq'+str(i),event['sequence']==i);stages[event['stage']].append(event['event'])
 for stage,events in stages.items():ck(name+':lifecycle'+stage,events==['preprocessor_entered','preprocessor_completed','model_entered','model_completed'])
 ck(name+':completed_counts',len(stages)==counts['models_completed']==counts['preprocessors_completed'] and counts['failures']==counts['retries']==0);stagecounts[name]=len(stages)
ck('all_67_fits',sum(stagecounts.values())==accounts['models_completed']==accounts['top_level_preprocessors_completed']==67)
ck('CV60',cv['model_fits']==cv['preprocessor_fits']==60 and cv['fit_failures']==0)
ck('B0_new_fit1',b0['fit_counts']['models_completed']==b0['fit_counts']['preprocessors_completed']==1)
ck('full_shared_and_clean6',packages['shared_main_model_fits']==2 and packages['independent_clean_model_fits']==4 and packages['full_models_total']==packages['full_top_level_preprocessors_total']==6 and packages['weight_fit_calls']==0)
integration=rd('fusion/sources/ACTUAL_FUSION_INTEGRATION17.json');ck('actual_artifact_integration',integration['status']=='PASS' and all(x['single_batch_reverse_extra_exact'] and x['invalid_window_all_nonkey_prediction_exact'] and x['dynamic_window_cells_decoded']==0 for x in integration['members']) and integration['model_fits']==integration['preprocessor_fits']==integration['competition_test_files_parsed_in_this_check']==0)
thresholds={n:str(Decimal('86.2003')+Decimal(str(results['B0']['repeated_summary']['mean']))-Decimal(str(results[n]['repeated_summary']['mean']))) for n in ['F70','F50']}
out={'reviews_commits':{'B0':'bc6963756f1feaf16154e9edacc96e648c74e63a','F70_F50':'742e573cac082cc6921f46255e07c566439360e4'},'checks_total':len(checks),'failed':[c for c in checks if not c['pass']],'all_checks_pass':all(c['pass'] for c in checks),'source_lock_unheld':unheld,'limits':limits,'package_identities':packageids,'comparison':comparison,'A_score_strictly_above_to_exceed_B0_S_v':thresholds,'B_fit_stages':stagecounts,'A_model_fits':0,'A_preprocessor_fits':0,'A_raw_data_reads':0,'platform_operations':0}
(R/'EVIDENCE_AND_ARITHMETIC.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
