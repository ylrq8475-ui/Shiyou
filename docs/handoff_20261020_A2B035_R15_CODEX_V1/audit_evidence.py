import json,hashlib,ast,math,statistics,collections
from pathlib import Path
R=Path(__file__).resolve().parent;checks=[];limits=[]
def rd(p):return json.loads((R/p).read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ck(n,v):checks.append({'check':n,'pass':bool(v)})
def eq(a,b):return math.isclose(a,b,rel_tol=0,abs_tol=1e-9)
for key in ['first','close']:
 for m in rd(key+'/sources/SHA256SUMS.json')['files']:ck(key+':published:'+Path(m['path']).name,sha(R/key/'sources'/Path(m['path']).name)==m['sha256'])
 manifest=rd(key+'/sources/'+('SOURCE_BUNDLE_MANIFEST.json' if key=='first' else 'RETEST_SOURCE_MANIFEST.json'));members=manifest.get('files',manifest.get('members'));print(key,'manifest',list(manifest))
 if isinstance(members,dict):members=[{'path':k,'sha256':v} for k,v in members.items()]
 for m in members:ck(key+':member:'+m['path'],sha(R/key/'bundle'/m['path'])==m['sha256'])
 scan=rd(key+'/sources/PRIVACY_SCAN_RAW.json')
 for m in scan['records']:
  ck(key+':scan:'+m['path'],m['result']=='PASS')
  if m.get('sha256'):ck(key+':scan_sha:'+m['path'],sha(R/key/'sources'/Path(m['path']).name)==m['sha256'])
  for x in m.get('source_ZIP_members',[]):ck(key+':scan_member:'+x['path'],sha(R/key/'bundle'/x['path'])==x['sha256'] and x['result']=='PASS')
 for p in (R/key/'bundle').rglob('*.py'):ast.parse(p.read_bytes());ck(key+':parse:'+str(p.relative_to(R/key/'bundle')),True)
lock=rd('first/sources/RESEARCH_LOCK.json');redactions=rd('first/sources/RESULT_R15_W.json')['source_runner_private_path_parameterization']
for name,h in lock['files'].items():
 p=R/'first/bundle'/name
 if name=='source/run15.py':
  receipt=redactions[0];ck('runner_executed_hash',receipt['original_sha256']==h);ck('runner_public_hash',receipt['public_sha256']==sha(p));ck('runner_declared_AST_equal',receipt['all_other_AST_equal']);limits.append('Original private runner not held by A; only declared DATA-path redaction and bound public/executed identities checked')
 else:ck('research_lock:'+name,sha(p)==h)
ck('research_lock_sha',sha(R/'first/sources/RESEARCH_LOCK.json')=='aafffd62ebc0974ce8fdc446484d554372bbcd2ed762598b85e548c75b174dac')
prior=R.parent/'CODEX_A2B035_R14_REVIEW_20261020/bundle/source/base'
for p in (R/'first/bundle/source/base').rglob('*'):
 if p.is_file():ck('prior_core:'+p.relative_to(R/'first/bundle/source/base').as_posix(),p.read_bytes()==(prior/p.relative_to(R/'first/bundle/source/base')).read_bytes())
allr=rd('close/sources/ALL_RESEARCH_RESULTS.json');records={x['config']['variant']:x for x in allr['records']};base=records['B0_U'];foldids={}
for name,x in records.items():
 results=x['results'];c=x['config']
 for sn in ['fixed']+['repeat_'+str(i) for i in range(1,6)]:
  s=results[sn];fs=s['folds'];budget=x['error_budget'][sn];n=sum(f['validation_wells'] for f in fs)
  ck(name+sn+':wells',n==81 and all(f['well_overlap']==0 and f['train_wells']+f['validation_wells']==81 for f in fs))
  ck(name+sn+':weighted_score',eq(s['score'],sum(f['validation_wells']*f['score'] for f in fs)/n))
  ck(name+sn+':official',eq(s['score'],100*(1-s['weighted_losses']['m1_to_12'])))
  ck(name+sn+':std',eq(s['fold_std_population'],statistics.pstdev(s['fold_scores'])))
  ck(name+sn+':cutpoints',all(v['outer_validation_used_for_cutpoints']==0 for v in budget['cutpoint_evidence']))
  ck(name+sn+':budget_identity',eq(budget['total_weighted_loss'],1-s['score']/100))
  ck(name+sn+':buckets',eq(sum(v['weighted_loss'] for v in budget['horizon_buckets'].values()),budget['total_weighted_loss']))
  ck(name+sn+':directions',eq(sum(budget['direction_contributions']['full'].values()),budget['total_weighted_loss']))
  for group,values in budget['groups'].items():
   if isinstance(values,dict):ck(name+sn+group+':suppressed',values.get('status')=='ENTIRE_DIMENSION_SUPPRESSED' and not any(k in values for k in ['wells','group_mean_weighted_loss']))
   else:ck(name+sn+group+':minimum',all(v['wells']>=5 for v in values));ck(name+sn+group+':group_total',sum(v['wells'] for v in values)==81 and eq(sum(v['contribution_to_total_loss'] for v in values),budget['total_weighted_loss']))
  ids=[f['split_sha256'] for f in fs]
  if name=='B0_U':foldids[sn]=ids
  else:ck(name+sn+':same_split',ids==foldids[sn])
  ck(name+sn+':fit_rows',all(f['effective_train_month_rows']==f['train_wells']*(2 if c['T'] else 12) for f in fs))
  ck(name+sn+':W_label',all((f['training_sample_weight']=='2^-horizon unnormalized')==c['W'] for f in fs))
  if c['T']:ck(name+sn+':late_identical',all(f['T_late_horizons_unchanged'] is True for f in fs))
  for prefix in ['m1_to_1','m1_to_2','m1_to_4','m1_to_12']:ck(name+sn+prefix,eq(s['weighted_losses'][prefix],sum(f['validation_wells']*f['weighted_losses'][prefix] for f in fs)/81))
 scores=[results['repeat_'+str(i)]['score'] for i in range(1,6)];ck(name+':repeat',eq(statistics.mean(scores),results['repeated_summary']['mean']));ck(name+':SE',eq(statistics.stdev(scores)/math.sqrt(5),results['repeated_summary']['standard_error']))
ck('baseline_exact',base['results']['fixed']['score']==73.71410733861434)
events=rd('close/sources/RESEARCH_FIT_EVENTS.json');print('events_type',type(events).__name__,list(events)[:8] if isinstance(events,dict) else len(events))
if isinstance(events,dict):events=events['events']
groups=collections.defaultdict(list)
for i,e in enumerate(events,1):ck('fit_sequence'+str(i),e['sequence']==i);groups[e['stage']].append(e['event'])
for name,ev in groups.items():ck('fit_lifecycle:'+name,ev==['preprocessor_entered','preprocessor_completed','model_entered','model_completed'])
ck('research540',len(groups)==540)
counts=rd('close/sources/FIT_ACCOUNTING_FINAL.json');ck('fit548',sum(counts[k] for k in ['research_models','B0_rebuild_models_including_lost_artifact','W_private_full_and_independent_models','LGB_Cat_synthetic_models','TabPFN_synthetic_context_fit_calls'])==counts['models_completed_total']==548)
ck('postfit_retry_honest',counts['postfit_artifact_failure']==counts['necessary_artifact_fit_retry']==1)
for x in rd('close/sources/CONFIG_INTERFACE_ZERO_FIT.json')['versions']:
 for m in x['members']:
  p=R/'close/bundle/package_interfaces'/x['version']/m['path'];p2=R/'first/bundle'/m['path']
  if p.is_file():ck('package_interface:'+x['version']+m['path'],sha(p)==m['sha256'])
  elif p2.is_file():ck('package_core:'+x['version']+m['path'],sha(p2)==m['sha256'])
 ck('config_zero_fits',x['model_fits']==x['preprocessor_fits']==0)
metadata=rd('OFFICIAL_METADATA_CHECK.json');tab=rd('close/sources/TABPFN_ACTUAL_ADMISSION.json');chr=rd('close/sources/CHRONOS_ACTUAL_ADMISSION.json')
for item in metadata['tab_tree']['lfs_files']:
 if item['path']==tab['weight']['filename']:ck('official_tab_lfs',item['lfs']['oid']==tab['weight']['actual_sha256'])
for item in metadata['chronos_tree']['lfs_files']:
 if item['path']=='model.safetensors':ck('official_chronos_lfs',item['lfs']['oid']==next(f['actual_sha256'] for f in chr['resource']['files'] if f['path']=='model.safetensors'))
ck('official_tab_license',metadata['tab_license']['sha256']==sha(R/'close/sources/TABPFN_MODEL_LICENSE.txt'));ck('official_chronos_license',metadata['chronos_license']['sha256']==sha(R/'close/sources/CHRONOS_APACHE_LICENSE.txt'))
for x in [tab,chr]:ck('foundation_zero_network',x.get('network_attempts',x.get('network_connect_blocks'))==0);ck('foundation_no_raw',x.get('competition_data_read',x.get('real_competition_data_read')) is False)
def pair(a,b):
 x=records[a];y=records[b];ds=[x['results']['repeat_'+str(i)]['score']-y['results']['repeat_'+str(i)]['score'] for i in range(1,6)]
 return {'variant':a,'reference':b,'fixed_delta':x['results']['fixed']['score']-y['results']['fixed']['score'],'repeat_delta':statistics.mean(ds),'seed_deltas':ds,'positive_seeds':sum(v>0 for v in ds),'early_score_gain':statistics.mean([100*(y['error_budget']['repeat_'+str(i)]['horizon_buckets']['month1']['weighted_loss']+y['error_budget']['repeat_'+str(i)]['horizon_buckets']['month2']['weighted_loss']-x['error_budget']['repeat_'+str(i)]['horizon_buckets']['month1']['weighted_loss']-x['error_budget']['repeat_'+str(i)]['horizon_buckets']['month2']['weighted_loss']) for i in range(1,6)])}
diagnosis={}
for name in ['B0_U','B0_W','B0PRIME_T_BASE',allr['best_H'],allr['best_T'],'B0_HX']:
 x=records[name];bs=[x['error_budget']['repeat_'+str(i)] for i in range(1,6)];diag={'repeated_mean':x['results']['repeated_summary']['mean'],'mean_total_loss':statistics.mean(b['total_weighted_loss'] for b in bs),'mean_top10pct_loss_fraction':statistics.mean(b['top10pct_loss_fraction'] for b in bs),'buckets':{k:statistics.mean(b['horizon_buckets'][k]['weighted_loss'] for b in bs) for k in bs[0]['horizon_buckets']},'direction_full':{k:statistics.mean(b['direction_contributions']['full'][k] for b in bs) for k in ['over_prediction','under_prediction']},'groups':{}}
 for field in ['production_tertile','scale_fallback','M_anomaly','M_operating_fraction']:
  if all(isinstance(b['groups'][field],list) for b in bs):
   names=set(v['group'] for b in bs for v in b['groups'][field]);diag['groups'][field]={n:{'mean_loss':statistics.mean(next(v['group_mean_weighted_loss'] for v in b['groups'][field] if v['group']==n) for b in bs),'mean_total_contribution':statistics.mean(next(v['contribution_to_total_loss'] for v in b['groups'][field] if v['group']==n) for b in bs)} for n in names if all(any(v['group']==n for v in b['groups'][field]) for b in bs)}
  else:diag['groups'][field]='SUPPRESSED in at least one split'
 diagnosis[name]=diag
geo=rd('close/sources/GEOLOGY_SCREEN.json');ck('geo_no_model',geo['model_fits']==geo['preprocessor_fits']==0 and geo['G_model_enabled'] is False);hits=[x for x in geo['results'] if x.get('worth_criterion_met')];ck('geo_rule',geo['decision']==('值得争取放行' if hits else '不再投入'))
out={'reviews_commit':'42a5c66406f56af86520c3d65eb71d1fbb616fea','also_reviews_commit':'51055b6458f17fc19f46c4b7a03da2f9a7a557e6','checks_total':len(checks),'failed':[c for c in checks if not c['pass']],'all_checks_pass':all(c['pass'] for c in checks),'limitations':limits,'pairs':[pair('B0_W','B0_U'),pair(allr['best_H'],'B0_U'),pair('T_B0PRIME_T_BASE','B0PRIME_T_BASE'),pair('T_H_base325_original_W',allr['best_H']),pair('B0_HX','B0_U')],'diagnosis':diagnosis,'fit_counts':counts,'A_model_fits':0,'A_preprocessor_fits':0,'A_competition_raw_reads':0}
(R/'EVIDENCE_AND_ARITHMETIC.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['diagnosis','fit_counts']},ensure_ascii=False,indent=2))
