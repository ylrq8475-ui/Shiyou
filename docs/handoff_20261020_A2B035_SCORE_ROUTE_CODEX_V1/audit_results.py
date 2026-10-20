"""Read anonymous B evidence; arithmetic and identity audit only. No ML imports."""
import json,hashlib,statistics,math,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads((ROOT/p).read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(label,ok):
 checks.append({'check':label,'pass':bool(ok)})
def close(a,b):return math.isclose(a,b,rel_tol=0,abs_tol=1e-9)
for f in read('sources/SHA256SUMS.json')['files']:
 p=ROOT/'sources'/Path(f['path']).name;check('published_sha:'+p.name,sha(p)==f['sha256'])
bundle=read('sources/ANONYMOUS_REPRO_MANIFEST.json')
check('anonymous_zip_sha',sha(ROOT/'sources/SEARCH_REPRO_ANONYMOUS.zip')==bundle['sha256'])
for m in bundle['members']:check('zip_member:'+m['path'],sha(ROOT/'bundle'/m['path'])==m['sha256'])
privacy=read('sources/PRIVACY_SCAN_RAW.json')
for f in privacy['records']:
 p=ROOT/'sources'/Path(f['path']).name
 check('privacy_result:'+p.name,f['result']=='PASS')
 if f.get('sha256'):check('privacy_binding:'+p.name,sha(p)==f['sha256'])
 for m in f.get('source_ZIP_members',[]):
  if isinstance(m,dict) and 'path' in m and (ROOT/'bundle'/m['path']).is_file():check('privacy_zip_binding:'+m['path'],sha(ROOT/'bundle'/m['path'])==m['sha256'] and m['result']=='PASS')
old=ROOT.parent/'CODEX_A2B035_PIPELINE_REVIEW_20261019/source_runtime'
core_matches=[]
for p in (ROOT/'bundle/source').rglob('*'):
 if p.is_file() and (old/p.relative_to(ROOT/'bundle/source')).exists():
  q=old/p.relative_to(ROOT/'bundle/source');ok=p.read_bytes()==q.read_bytes();core_matches.append({'path':p.relative_to(ROOT/'bundle/source').as_posix(),'same':ok});check('prior_source:'+str(p.relative_to(ROOT/'bundle/source')),ok)
search=read('bundle/aggregates/RESULT_DAILY_SEARCH.json');public=read('sources/RESULT_DAILY_DELIVERY.json')
records={x['variant']:x for x in search['records']};base=records['B0_prime'];br=base['results']
for name,r in records.items():
 results=r['results'];c=r['config']
 check(name+':split_identity',c['split_fingerprints']==base['config']['split_fingerprints'])
 for sn in ['fixed']+['repeat_'+str(i) for i in range(1,6)]:
  s=results[sn];folds=s['folds'];count=sum(f['validation_wells'] for f in folds)
  check(name+':'+sn+':coverage',count==81 and all(f['well_overlap']==0 and f['train_wells']+f['validation_wells']==81 for f in folds))
  check(name+':'+sn+':score',close(sum(f['score']*f['validation_wells'] for f in folds)/count,s['score']))
  check(name+':'+sn+':formula',close(100*(1-s['weighted_losses']['m1_to_12']),s['score']))
  check(name+':'+sn+':std',close(statistics.pstdev(s['fold_scores']),s['fold_std_population']))
  for k in ('m1_to_1','m1_to_2','m1_to_4','m1_to_12'):
   check(name+':'+sn+':'+k,close(sum(f['weighted_losses'][k]*f['validation_wells'] for f in folds)/count,s['weighted_losses'][k]))
 scores=[results['repeat_'+str(i)]['score'] for i in range(1,6)]
 check(name+':repeat_mean',close(statistics.mean(scores),results['repeated_summary']['mean']))
 check(name+':repeat_SE',close(statistics.stdev(scores)/math.sqrt(5),results['repeated_summary']['standard_error']))
 pub=next(x for x in public['all_config_results'] if x['variant']==name)
 check(name+':public_mean',close(results['repeated_summary']['mean'],pub['repeated_summary']['mean']))
 if name!='B0_prime':
  stamp=read('bundle/configs/'+name+'.PRESCORE.json')
  check(name+':prescore_config',sha(ROOT/'bundle/configs'/ (name+'.json'))==stamp['config_sha256'])
  check(name+':runtime',stamp['runtime']==read('sources/ACTUAL_RUNTIME_START.json')['actual_runtime'])
rank=sorted(records,key=lambda n:(-records[n]['results']['repeated_summary']['mean'],records[n]['results']['repeated_summary']['standard_error'],-records[n]['results']['fixed']['score'],n))
check('rank_matches_public',rank==public['ranking'])
fit=read('sources/FIT_COUNTS_SEARCH.json');groups=collections.defaultdict(list)
for i,e in enumerate(fit['events'],1):check('fit_sequence:'+str(i),e['sequence']==i);groups[e['stage']].append(e['event'])
for stage,events in groups.items():check('fit_lifecycle:'+stage,events==['preprocessor_entered','preprocessor_completed','model_entered','model_completed'])
check('fit_totals',len(groups)==2460 and fit['models_completed']==2460 and fit['preprocessors_completed']==2460 and fit['failures']==fit['retries']==0)
def paired(n,ref='B0_prime'):
 a=records[n]['results'];b=records[ref]['results'];ds=[a['repeat_'+str(i)]['score']-b['repeat_'+str(i)]['score'] for i in range(1,6)]
 fds=[x-y for x,y in zip(a['fixed']['fold_scores'],b['fixed']['fold_scores'])]
 early={k:statistics.mean([100*(b['repeat_'+str(i)]['weighted_losses'][k]-a['repeat_'+str(i)]['weighted_losses'][k]) for i in range(1,6)]) for k in ('m1_to_1','m1_to_2','m1_to_4','m1_to_12')}
 return {'variant':n,'reference':ref,'repeat_mean':a['repeated_summary']['mean'],'fixed_score':a['fixed']['score'],'repeat_delta':statistics.mean(ds),'seed_deltas':ds,'positive_seeds':sum(d>0 for d in ds),'paired_seed_SE_descriptive':statistics.stdev(ds)/math.sqrt(5),'fixed_delta':a['fixed']['score']-b['fixed']['score'],'fixed_fold_deltas':fds,'positive_fixed_folds':sum(d>0 for d in fds),'prefix_score_gains':early}
best=rank[0];routes=[paired(n) for n in rank if n.startswith('FUSION') or n.startswith('MO') and n==next(v for v in rank if v.startswith('MO')) or n.startswith('ET_') and (n.endswith('_t400_l6_f75') or n==best)]
multi_pairs=[paired(n,('ET'+n[2:]) if ('ET'+n[2:]) in records else 'B0_prime') for n in records if n.startswith('MO')]
et=[r for r in records.values() if r['config']['learner']['name']=='ExtraTrees'];modes=collections.Counter(r['config']['learner']['name'] for r in records.values())
v=paired(best);s_prev=(79.4717+br['repeated_summary']['mean'])/2;s_new=(79.3643+records[best]['results']['repeated_summary']['mean'])/2
res={'reviewed_commit':'6601551152ce4b21d8447fef6ad455e1277023e4','fit_count_A':0,'checks_total':len(checks),'checks_failed':[c for c in checks if not c['pass']],'source_comparison':core_matches,'route_results':routes,'best_pair':v,'counts_by_model':dict(modes),'multioutput_pair_summary':{'pairs':len(multi_pairs),'wins':sum(x['repeat_delta']>0 for x in multi_pairs),'mean_delta':statistics.mean(x['repeat_delta'] for x in multi_pairs),'best_multioutput':next(x for x in routes if x['variant'].startswith('MO'))},'positive_configs_vs_baseline':sum(r['results']['repeated_summary']['mean']>br['repeated_summary']['mean'] for r in records.values()),'screenshot_observations':{'latest':{'time':'2026-10-20 10:21:18','score':79.3643,'status':'评测成功'},'previous':{'time':'2026-10-19 17:08:30','score':79.4717,'status':'评测成功'},'delta':79.3643-79.4717,'actual_uploaded_package_hashes':'UNKNOWN; screenshot lacks package hashes; user associates latest delivery'},'conditional_S_v':{'condition':'only if screenshot rows bind respectively to B0prime and selected current candidate packages','previous':s_prev,'latest':s_new,'delta':s_new-s_prev,'actual_version_binding':'UNKNOWN'},'B_fit_counts':{'search':2460,'package':2,'new_total':2462},'all_checks_pass':all(c['pass'] for c in checks)}
(ROOT/'ARITHMETIC_REVIEW.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in res.items() if k not in ('source_comparison',)},ensure_ascii=False,indent=2))
