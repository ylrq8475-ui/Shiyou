"""Independent anonymous aggregate arithmetic and immutable-source checks; zero ML fits."""
import json,hashlib,ast,math,statistics,collections,itertools
from pathlib import Path
R=Path(__file__).resolve().parent;checks=[];limits=[]
def rd(p):return json.loads((R/p).read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ck(n,v):checks.append({'check':n,'pass':bool(v)})
def eq(a,b):return math.isclose(a,b,rel_tol=0,abs_tol=1e-9)
def enc(o):return json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
for group in ['first','native']:
 src=R/group/'sources';files={p.name for p in src.iterdir() if p.is_file()};manifest=rd(group+'/sources/SHA256SUMS.json')
 ck(group+':manifest_coverage',{Path(v['path']).name for v in manifest['files']}==files-{'SHA256SUMS.json'})
 for v in manifest['files']:
  p=src/Path(v['path']).name;ck(group+':file:'+p.name,sha(p)==v['sha256'] and p.stat().st_size==v['bytes'])
 scan=rd(group+'/sources/PRIVACY_SCAN_RAW.json');ck(group+':scan_coverage',{Path(v['path']).name for v in scan['records']}==files and scan['published_files']==scan['scan_records']==len(files))
 for v in scan['records']:
  ck(group+':scan:'+Path(v['path']).name,v['result']=='PASS' and v['credential_or_private_path_hits']==0 and all(x==0 for x in v['private_marker_hits'].values()))
  if v.get('sha256'):ck(group+':scan_byte:'+Path(v['path']).name,sha(src/Path(v['path']).name)==v['sha256'])
  for m in v.get('source_ZIP_members',[]):ck(group+':member_scan:'+m['path'],sha(R/group/'bundle'/m['path'])==m['sha256'] and m['result']=='PASS')
 ck(group+':scanner_no_fits',scan['model_fits_by_scanner']==scan['preprocessor_fits_by_scanner']==0)
lock=rd('first/sources/RESEARCH_LOCK16.json');ck('lock_identity',sha(R/'first/sources/RESEARCH_LOCK16.json')=='9842a7c64f9e6d6969c462fd1e3d4a1498aece464b7e43f2d1d3fd912809b9df');unavailable=[]
for n,h in lock['files'].items():
 p=R/'first/bundle'/n
 if not p.exists():p=R/'first/sources'/Path(n).name
 if not p.exists():
  prior=R.parent/'CODEX_A2B035_R15_REVIEW_20261020/delivery_final'/Path(n).name
  if prior.exists():p=prior
 if not p.exists() and n=='received/R16_ORIGINAL.md':p=R/'instruction/sources/INSTRUCTION_ORIGINAL.md'
 if p.exists():ck('lock:'+n,sha(p)==h)
 else:unavailable.append(n)
prior=R.parent/'CODEX_A2B035_R15_REVIEW_20261020/first/bundle/source'
for p in (R/'first/bundle/source').rglob('*.py'):ast.parse(p.read_bytes());ck('syntax:'+p.name,True)
for p in (R/'first/bundle/source/base').rglob('*'):
 if p.is_file():ck('old_core:'+p.relative_to(R/'first/bundle/source').as_posix(),p.read_bytes()==(prior/p.relative_to(R/'first/bundle/source')).read_bytes())
for name in ['error_budget.py','r14.py','routes15.py']:ck('prior_R15:'+name,(R/'first/bundle/source'/name).read_bytes()==(prior/name).read_bytes())
grid=rd('first/sources/GRID16.json');configs={v['config']['variant']:v for v in grid['variants']};ck('46configs',len(configs)==46)
for learner,n in [('LightGBM',32),('CatBoost',8),('TabPFN',2),('ExtraTrees',4)]:ck('grid_count:'+learner,sum(v['config']['learner']==learner for v in configs.values())==n)
native=rd('native/sources/ALL_NATIVE_RESULTS.json');records={x['config']['variant']:x for x in native['records']};comparisons={x['variant']:x for x in rd('native/sources/MODEL_COMPARISON_ALL.json')['rows']};ck('native42',len(records)==42)
ck('native_exact_grid',set(records)=={n for n,v in configs.items() if v['environment']=='NATIVE'})
first=rd('first/sources/RESULT_FIRST16.json');env=rd('first/sources/ENV_NATIVE.json');ck('native_env_unchanged',env==rd('native/sources/ENVIRONMENT_NATIVE.json'))
panels=rd('first/sources/PRE_DATA16.json');ck('same_targets',panels['panels']['M_minus_1']['identity']['label_key_frame_sha256']==panels['panels']['T0_minus_1']['identity']['label_key_frame_sha256']);ck('no_test_panels',panels['test_files_parsed']==0 and panels['before_real_fit'] and panels['data_members_verified']==100)
for cut,x in panels['panels'].items():ck(cut+':input_contract',x['features']==325 and x['boundary']['wells']==81 and x['boundary']['rows']==972 and x['boundary']['future_sensitive_input_count']==0)
names=['fixed']+['repeat_'+str(i) for i in range(1,6)];refs={};diags={}
def diagnosis(record):
 bs=[record['error_budget']['repeat_'+str(i)] for i in range(1,6)]
 out={'buckets':{k:statistics.mean(b['horizon_buckets'][k]['weighted_loss'] for b in bs) for k in bs[0]['horizon_buckets']},'directions':{k:statistics.mean(b['direction_contributions']['full'][k] for b in bs) for k in bs[0]['direction_contributions']['full']},'early_directions':{m:{k:statistics.mean(b['direction_contributions'][m][k] for b in bs) for k in bs[0]['direction_contributions'][m]} for m in ['month1','month2']},'groups':{}}
 for field in bs[0]['groups']:
  if any(isinstance(b['groups'][field],dict) for b in bs):out['groups'][field]='SUPPRESSED';continue
  labels={v['group'] for b in bs for v in b['groups'][field]};out['groups'][field]={}
  for label in sorted(labels):
   rows=[next((v for v in b['groups'][field] if v['group']==label),None) for b in bs]
   if all(rows):out['groups'][field][label]={k:statistics.mean(v[k] for v in rows) for k in ['wells','group_mean_weighted_loss','contribution_to_total_loss']}
 return out
for name,x in records.items():
 c=x['config'];res=x['results'];ck(name+':config',configs[name]=={'environment':x['environment'],'config':c});control=records['CTRL_NATIVE_B0' if c['cutoff']=='M_minus_1' else 'CTRL_NATIVE_B0P']
 for sn in names:
  z=res[sn];fs=z['folds'];bs=x['error_budget'][sn];scores=[f['score'] for f in fs]
  ck(name+sn+':wells',len(fs)==5 and sum(f['validation_wells'] for f in fs)==81 and all(f['validation_wells'] in (16,17) and f['training_wells']+f['validation_wells']==81 and f['well_overlap']==0 for f in fs))
  ck(name+sn+':score',eq(z['score'],sum(f['score']*f['validation_wells'] for f in fs)/81))
  ck(name+sn+':official',eq(z['score'],100*(1-z['weighted_losses']['m1_to_12'])))
  ck(name+sn+':fold_stats',z['fold_scores']==scores and eq(z['worst_fold'],min(scores)) and eq(z['fold_std_population'],statistics.pstdev(scores)))
  ck(name+sn+':same_splits',[f['split_sha256'] for f in fs]==[f['split_sha256'] for f in control['results'][sn]['folds']])
  ck(name+sn+':fit_counts',all(f['model_fits']==f['preprocessor_fits']==1 for f in fs))
  ck(name+sn+':weights',all(f['training_weights']==('2^-horizon unnormalized' if c['W'] else 'none') for f in fs))
  for key in ['m1_to_1','m1_to_2','m1_to_4','m1_to_12']:ck(name+sn+key,eq(z['weighted_losses'][key],sum(f['validation_wells']*f['weighted_losses'][key] for f in fs)/81))
  ck(name+sn+':budget',eq(bs['total_weighted_loss'],1-z['score']/100) and eq(sum(v['weighted_loss'] for v in bs['horizon_buckets'].values()),bs['total_weighted_loss']))
  for label,total in [('month1',bs['horizon_buckets']['month1']['weighted_loss']),('month2',bs['horizon_buckets']['month2']['weighted_loss']),('full',bs['total_weighted_loss'])]:ck(name+sn+':direction:'+label,eq(sum(bs['direction_contributions'][label].values()),total))
  for dim,groups in bs['groups'].items():
   if isinstance(groups,dict):ck(name+sn+dim+':suppression',groups.get('status')=='ENTIRE_DIMENSION_SUPPRESSED' and not any(k in groups for k in ['wells','group_mean_weighted_loss','contribution_to_total_loss']))
   else:
    ck(name+sn+dim+':support',sum(g['wells'] for g in groups)==81 and all(g['wells']>=5 for g in groups))
    ck(name+sn+dim+':partition',eq(sum(g['contribution_to_total_loss'] for g in groups),bs['total_weighted_loss']))
    for g in groups:ck(name+sn+dim+g['group']+':contribution',eq(g['group_mean_weighted_loss']*g['wells']/81,g['contribution_to_total_loss']))
  ck(name+sn+':train_cutpoints',all(v['outer_validation_used_for_cutpoints']==0 for v in bs['cutpoint_evidence']))
 scores=[res['repeat_'+str(i)]['score'] for i in range(1,6)];re=res['repeated_summary'];cmp=comparisons[name];deltas=[a-control['results']['repeat_'+str(i)]['score'] for i,a in enumerate(scores,1)]
 ck(name+':repeat',re['repeat_scores']==scores and eq(re['mean'],statistics.mean(scores)) and eq(re['sample_std'],statistics.stdev(scores)) and eq(re['standard_error'],statistics.stdev(scores)/math.sqrt(5)))
 ck(name+':paired_deltas',all(eq(a,b) for a,b in zip(deltas,cmp['paired_repeat_deltas'])) and eq(cmp['repeated_delta'],statistics.mean(deltas)) and cmp['strictly_positive_repeat_count']==sum(v>0 for v in deltas))
 ck(name+':fixed_delta',eq(cmp['fixed_delta'],res['fixed']['score']-control['results']['fixed']['score']))
 for key in ['m1_to_1','m1_to_2','m1_to_4','m1_to_12']:ck(name+':repeat_loss:'+key,eq(re['weighted_loss_means'][key],statistics.mean(res['repeat_'+str(i)]['weighted_losses'][key] for i in range(1,6))))
for name,fixed,repeat in [('CTRL_NATIVE_B0',73.71410733861434,72.47647400484871),('CTRL_NATIVE_B0P',76.33261832127738,75.39352260217446)]:
 ck(name+':baseline',records[name]['results']['fixed']['score']==fixed and records[name]['results']['repeated_summary']['mean']==repeat)
for learner in ['LightGBM','CatBoost']:
 z=rd('first/sources/INTEGRATION_'+learner+'.json');ck(learner+':integration_identity',z['source_lock_sha256']==sha(R/'first/sources/RESEARCH_LOCK16.json') and z['environment']==env and z['actual_learner']==learner)
 ck(learner+':independence',z['validation_rows_single_batch_reverse_extra_exact'] and z['actual_learner_poison_prediction_exact'] and z['both_cutoffs_covered'] and z['synthetic_window_column_cutoff_cases']==54)
 ck(learner+':offline',z['inference_fit_guard_active'] and z['offline_socket_guard_active'] and z['competition_test_files_parsed']==0)
 ck(learner+':first_fold_reused',z['actual_fold']==records[z['config']['variant']]['results']['fixed']['folds'][0] and z['fit_models_for_integration_extra']==z['fit_preprocessors_for_integration_extra']==0)
ledger=rd('native/sources/NATIVE_FIT_EVENTS.json');stages=collections.defaultdict(list)
for i,e in enumerate(ledger['events'],1):ck('fit_event:'+str(i),e['sequence']==i);stages[e['stage']].append(e['event'])
for stage,ev in stages.items():ck('lifecycle:'+stage,ev==['preprocessor_entered','preprocessor_completed','model_entered','model_completed'])
expected={name+'-'+sn+'-'+str(i) for name in records for sn in names for i in range(1,6)}
ck('exact_1260_stages',set(stages)==expected and len(stages)==1260 and ledger['models_completed']==ledger['preprocessors_completed']==1260 and ledger['failures']==ledger['retries']==0)
receipts={}
priorinterfaces=R.parent/'CODEX_A2B035_R15_REVIEW_20261020/close/sources/CONFIG_INTERFACE_ZERO_FIT.json'
versions={v['version']:v for v in json.loads(priorinterfaces.read_bytes())['versions']}
for version in ['B0','B0_W']:
 p=rd('first/sources/'+version+'_PACKAGE_RECEIPT.json');receipts[version]={k:p[k] for k in ['result_zip_sha256','submission_code_zip_sha256','code_bytes']}
 ck(version+':old_package_unchanged',p['result_zip_sha256']==first['packages'][0 if version=='B0' else 1]['result_zip_sha256'] and p['submission_code_zip_sha256']==versions[version]['submission_code_zip_sha256'])
 ck(version+':receipt',p['main_model_sha256']==p['independent_model_sha256'] and p['existing_independent_raw_retrain_result_bytes_equal'] and p['latest_interface_exact_ZIP_inference_result_equal'] and p['model_fits_for_this_receipt']==p['preprocessor_fits_for_this_receipt']==0)
 for phase in ['main','clean']:
  counts=p['existing_'+phase+'_train_counts'];lint=p['existing_'+phase+'_result_linter']
  ck(version+phase+':existingfit',counts['models_completed']==counts['preprocessors_completed']==1 and counts['failures']==0 and [e['event'] for e in counts['events']]==['preprocessor_entered','preprocessor_completed','model_entered','model_completed'])
  ck(version+phase+':linter',lint['status']=='PASS' and lint['files']==10 and lint['rows']==120 and lint['columns']==['WELL_ID','NY','RCYL'] and lint['exact_template_keys_dates_order'] and lint['duplicate_keys']==lint['extra_columns']==lint['NaN_Inf_negative']==0 and lint['flat_ZIP'] and lint['CRC_passed'] and lint['result_zip_sha256']==p['result_zip_sha256'])
  ck(version+phase+':counts_original_sha',hashlib.sha256((json.dumps(counts,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()==p['source_receipts_original_byte_sha256'][phase+'_counts'])
 ck(version+':same_clean_lint',p['existing_main_result_linter']==p['existing_clean_result_linter'])
 for item in p['syntax_check_latest_ZIP']:
  q=R/'first/bundle'/item['path'];q2=R.parent/'CODEX_A2B035_R15_REVIEW_20261020/close/bundle/package_interfaces'/version/item['path']
  if q.is_file():ck(version+':package_source:'+item['path'],sha(q)==item['sha256'])
  elif q2.is_file():ck(version+':package_source:'+item['path'],sha(q2)==item['sha256'])
  else:
   q3=R.parent/'CODEX_A2B035_R15_REVIEW_20261020/first/bundle'/item['path']
   if q3.is_file():ck(version+':prior_package_source:'+item['path'],sha(q3)==item['sha256'])
   else:limits.append(version+': package Python member original private ZIP not held by A: '+item['path'])
best={cut:min([v for v in comparisons.values() if v['cutoff']==cut and v['learner']!='ExtraTrees'],key=lambda v:-v['repeated_mean']) for cut in ['M_minus_1','T0_minus_1']}
for n in ['CTRL_NATIVE_B0','CTRL_NATIVE_B0P']+[v['variant'] for v in best.values()]+['LGB_B0_n7_m10_t300_W','LGB_B0P_n7_m10_t300_U']:diags[n]=diagnosis(records[n])
# Paired W/U and 300/600 tree increments: diagnosis only, no new fitting.
weight_pairs=[];tree_pairs=[]
for n,x in comparisons.items():
 if x['learner']=='ExtraTrees':continue
 if x['W']:
  other=comparisons[n[:-1]+'U'];weight_pairs.append({'weighted':n,'unweighted':other['variant'],'delta_repeat':x['repeated_mean']-other['repeated_mean'],'early2_score_gain':100*(records[other['variant']]['results']['repeated_summary']['weighted_loss_means']['m1_to_2']-records[n]['results']['repeated_summary']['weighted_loss_means']['m1_to_2'])})
 if '_t600_' in n:
  other=comparisons[n.replace('_t600_','_t300_')];tree_pairs.append({'more_trees':n,'delta_repeat':x['repeated_mean']-other['repeated_mean']})
out={'reviews_commit':'12a197b396f80bb83e3a4ab18c8a45509b128026','also_reviews_commit':'6ab552ef1cb007b13f0bc350957b7b82037f1348','checks_total':len(checks),'failed':[c for c in checks if not c['pass']],'all_checks_pass':all(c['pass'] for c in checks),'source_lock_not_independently_held':unavailable,'limits':limits,'best_new_per_cutoff':best,'diagnosis':diags,'W_U_pairs':weight_pairs,'tree_count_pairs':tree_pairs,'package_identities':receipts,'counts':{'native_model_fits':1260,'native_preprocessors':1260,'snapshot_total_models':1267,'snapshot_total_preprocessors':1264,'retired_execution_each':3,'extra_synthetic_model_contexts':3,'active_Tab_context_each':1},'A_model_fits':0,'A_preprocessor_fits':0,'A_competition_data_reads':0}
(R/'EVIDENCE_AND_ARITHMETIC.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k not in ['diagnosis','W_U_pairs','tree_count_pairs']},ensure_ascii=False,indent=2))
