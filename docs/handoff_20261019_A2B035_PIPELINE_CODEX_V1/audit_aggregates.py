"""Independent stdlib-only identity, fit ledger and equal-well arithmetic."""
import hashlib,json,math,statistics,zipfile
from pathlib import Path
R=Path(__file__).resolve().parent;B=R/'sources/B';S=R/'source_runtime';checks=[]
def load(n,base=B):return json.loads((base/n).read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(n,v):checks.append({'check':n,'pass':bool(v)})
def same(a,b,tol=1e-11):return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol
files={p.name:p for p in B.iterdir() if p.is_file()};manifest=load('SHA256SUMS.json')
check('35 published files',len(files)==35)
rows=manifest['files'];check('checksum coverage34',len(rows)==34 and {Path(x['path']).name for x in rows}==set(files)-{'SHA256SUMS.json'})
for row in rows:
    p=files[Path(row['path']).name];check('manifest '+p.name,sha(p)==row['sha256'] and p.stat().st_size==row['bytes'])
bundle=load('SOURCE_BUNDLE_MANIFEST.json');privacy=load('PRIVACY_SCAN_RAW.json');record=next(x for x in privacy['records'] if x['path'].endswith('.zip'));inner={x['path']:x for x in record['source_ZIP_members']}
check('source archive original bytes',bundle['source_zip_sha256']==sha(B/'PIPELINE_SOURCE_ANONYMOUS.zip') and bundle['source_zip_bytes']==(B/'PIPELINE_SOURCE_ANONYMOUS.zip').stat().st_size)
with zipfile.ZipFile(B/'PIPELINE_SOURCE_ANONYMOUS.zip') as z:
    check('source archive CRC and 29 members',z.testzip() is None and len(z.infolist())==29 and set(z.namelist())=={x['path'] for x in bundle['members']}==set(inner))
    for row in bundle['members']:
        b=z.read(row['path']);rel=row['path'].removeprefix('source/');check('archive/public identity '+rel,hashlib.sha256(b).hexdigest()==row['sha256']==inner[row['path']]['sha256'] and len(b)==row['bytes'] and (S/rel).read_bytes()==b and inner[row['path']]['result']=='PASS')
        if rel in files:check('loose/archive identity '+rel,files[rel].read_bytes()==b)
check('35 unique privacy records',len(privacy['records'])==35 and {Path(x['path']).name for x in privacy['records']}==set(files) and len({x['record_id'] for x in privacy['records']})==35)
for row in privacy['records']:
    name=Path(row['path']).name;check('B scan result '+name,row['result']=='PASS' and sum(row['private_marker_hits'].values())==row['credential_or_private_path_hits']==0)
    if row['sha256'] is None:check('metadata no circular digest '+name,name in {'PRIVACY_SCAN_RAW.json','SHA256SUMS.json'})
    else:check('B scan bytes '+name,sha(files[name])==row['sha256'] and files[name].stat().st_size==row['bytes'])
lock=load('PIPELINE_LOCK.json');contract=load('DATA_CONTRACT.json');start=load('STARTED.json');preflight=load('PREFLIGHT.json');plan=load('PLAN_STAGE0.json');result=load('RESULT_PIPELINE.json');baseline=load('BASELINE_CONFIGS.json')
check('pipeline identity binding',sha(B/'PIPELINE_LOCK.json')==start['pipeline_lock_sha256']==preflight['pipeline_lock_sha256']==result['pipeline_lock_sha256']=='ce1ab047d126f2586993dc8d2b05aef5f1b9871c59b626d6927d8803904713d1')
for name,h in lock['files'].items():check('immutable source '+name,sha(S/name)==h)
check('prescore record identities',start['plan_sha256']==sha(B/'PLAN_STAGE0.json') and start['preflight_sha256']==sha(B/'PREFLIGHT.json') and sha(B/'ENVIRONMENT_LOCK.json')==lock['environment_sha256'])
check('R13 original bytes hash',sha(R/'sources/r13')==plan['R13_sha256']=='ec3fe583f40e10da7cdc9fede01ce3c5079f85968f7acb6fb1209eeef7a1bee5')
for name,c in baseline.items():
    check('baseline config original '+name,c==load('configs/'+name+'.json',S) and c['split_fingerprints']==contract['split_fingerprints'])
check('six split sets fixed prescore',set(contract['split_fingerprints'])=={'fixed',*[f'repeat_{i}' for i in range(1,6)]} and all(len(v)==5 for v in contract['split_fingerprints'].values()))
for arm in ['B0','B0_prime']:
    values=result['results'][arm];check('baseline identity '+arm,preflight['row_target_feature_identity'][arm]['identity']==contract[arm+'_identity'])
    for name in ['fixed',*[f'repeat_{i}' for i in range(1,6)]]:
        value=values[name];folds=value['folds'];check(arm+' '+name+' full fold scope',len(folds)==5 and sum(f['validation_wells'] for f in folds)==81 and all(f['train_wells']+f['validation_wells']==81 and f['well_overlap']==0 for f in folds) and value['validation_coverage_each_row_once'])
        score=sum(f['score']*f['validation_wells'] for f in folds)/81;check(arm+' '+name+' independent equal-well aggregate',same(score,value['score']))
        check(arm+' '+name+' locked split identity',[f['row_split_sha256'] for f in folds]==contract['split_fingerprints'][name])
        scores=[f['score'] for f in folds];check(arm+' '+name+' fold summaries',scores==value['fold_scores'] and min(scores)==value['worst_fold'] and same(statistics.pstdev(scores),value['fold_std_population']))
        check(arm+' '+name+' total score from loss',same(100*(1-value['weighted_losses']['m1_to_12']),value['score']))
        for horizon in [1,2,4,12]:
            k=f'm1_to_{horizon}';check(arm+' '+name+' horizon '+str(horizon),same(sum(f['weighted_losses'][k]*f['validation_wells'] for f in folds)/81,value['weighted_losses'][k]))
        for i,f in enumerate(folds):
            check(arm+' '+name+' fold loss score '+str(i+1),same(100*(1-f['weighted_losses']['m1_to_12']),f['score']) and [f['weighted_losses'][f'm1_to_{h}'] for h in (1,2,4,12)]==sorted(f['weighted_losses'].values()))
    repeated=[values[f'repeat_{i}']['score'] for i in range(1,6)];summary=values['repeated_summary'];check(arm+' repeated summary mean/std/SE',summary['repeat_scores']==repeated and same(statistics.mean(repeated),summary['mean']) and same(statistics.stdev(repeated),summary['sample_std']) and same(statistics.stdev(repeated)/math.sqrt(5),summary['standard_error']))
    for k,v in summary['weighted_loss_means'].items():check(arm+' repeated loss '+k,same(statistics.mean(values[f'repeat_{i}']['weighted_losses'][k] for i in range(1,6)),v))
check('fixed B0 exact historical score',abs(result['results']['B0']['fixed']['score']-73.71410733861434)<=1e-6)
check('fixed B0prime exact historical score',abs(result['results']['B0_prime']['fixed']['score']-76.33261832127738)<=1e-6)
deltas=[result['results']['B0_prime'][f'repeat_{i}']['score']-result['results']['B0'][f'repeat_{i}']['score'] for i in range(1,6)];paired=result['repeated_paired_delta'];check('five paired mean/count',all(same(a,b) for a,b in zip(deltas,paired['values'])) and same(statistics.mean(deltas),paired['mean']) and sum(x>0 for x in deltas)==paired['positive_groups']==5)
ledger=load('FIT_COUNTS.json');events=ledger['events'];check('61 entered/completed fits each',all(ledger[k]==61 for k in ['models_entered','models_completed','preprocessors_entered','preprocessors_completed']) and ledger['failures']==ledger['retries']==0)
check('244 unique chronological events',len(events)==244 and [e['sequence'] for e in events]==list(range(1,245)) and [e['time'] for e in events]==sorted(e['time'] for e in events))
stages=set(e['stage'] for e in events);expected={'synthetic-real-estimator'}|{f'{arm}-{name}-fold{i}' for arm in ['B0','B0_prime'] for name in ['fixed',*[f'repeat_{j}' for j in range(1,6)]] for i in range(1,6)};check('60 actual CV plus1 synthetic stage',stages==expected)
for stage in sorted(stages):check('fit stage '+stage,[e['event'] for e in events if e['stage']==stage]==['preprocessor_entered','preprocessor_completed','model_entered','model_completed'])
check('both fixed baselines precede all repeat stages',max(e['sequence'] for e in events if '-fixed-' in e['stage'])<min(e['sequence'] for e in events if '-repeat_' in e['stage']))
check('lock start before first fit',start['start_time']<events[0]['time'])
check('fit counts and result no hidden totals',result['fit_counts']=={k:v for k,v in ledger.items() if k!='events'} and result['competition_data_CV_model_fits']==result['competition_data_CV_preprocessor_fits']==60 and result['synthetic_model_fits']==result['synthetic_preprocessor_fits']==1)
check('no OOF/model/test prediction persistence',result['row_oof_persisted'] is False and result['fold_models_persisted'] is False and result['real_test_predictions_generated'] is False and result['candidate_packages_generated']==0 and result['search_started'] is False)
check('all external adapters disabled',all(x['enabled'] is False and x['license_checked'] is False for x in load('RESOURCE_RELEASES.json').values()))
ledger_public=load('PLATFORM_LEDGER_PUBLIC.json');check('ledger not deriving S_v from missing scores',ledger_public['daily_complete_version_limit']==3 and all(x['S_v']=='UNKNOWN' for x in ledger_public['entries']))
check('ledger excludes row values',not any(k in json.dumps(ledger_public).casefold() for k in ['well_id','predictions','truth','labels']))
check('protected old artifacts declaration',load('PRESERVATION_CHECK.json')['files_checked']==129 and load('PRESERVATION_CHECK.json')['all_original_bytes_unchanged'])
out={'source_and_receipt_checks':len(checks),'passed':sum(x['pass'] for x in checks),'failed':sum(not x['pass'] for x in checks),'checks':checks,'A_actual_model_fits':0,'A_actual_preprocessor_fits':0,'competition_data_read':False,'scope':'Public source, bound execution receipts and independently recomputed aggregate arithmetic; no A real CV rerun','B0_repeated':result['results']['B0']['repeated_summary']['mean'],'B0_prime_repeated':result['results']['B0_prime']['repeated_summary']['mean'],'paired_mean':statistics.mean(deltas),'known_ledger_provenance_caveat':'Two hashes appear as uploaded_* with USER_REPLY source although A supplied audited-package reference hashes only. Request exact source wording or classify as reviewed_artifact reference; S_v remains UNKNOWN.'}
with (R/'AGGREGATE_REVIEW_CODEX.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='checks'}));assert out['failed']==0
