"""R13 internal daily search orchestrator around unchanged reviewed core."""
import sys,time,traceback,platform,importlib.metadata as im,itertools,copy,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'source'))
from cv035 import *
from ledger035 import Ledger

def save(p,o):Path(p).write_bytes(encode(o))
def runtime_probe():
    value={'python_version':platform.python_version(),'python_build':list(platform.python_build()),'python_compiler':platform.python_compiler(),'executable_sha256':file_sha(sys.executable),'dependencies':dict(sorted({d.metadata['Name']:d.version for d in im.distributions()}.items(),key=lambda x:x[0].lower())),'logical_CPU':os.cpu_count(),'n_jobs':-1,'BLAS_OpenMP_threads':1,'folds_parallel':1,'prediction_reduction':'sequential'}
    locked=json.loads((HERE/'ENVIRONMENT_LOCK.json').read_bytes());require(value['python_version']==locked['python_version'] and value['python_build']==locked['python_build'] and value['python_compiler']==locked['python_compiler'] and value['dependencies']==locked['dependencies'],'LIVE_ENVIRONMENT_CHANGED');return value
def scope_check(c):
    validate_config(c);require_release(c);approval=json.loads((HERE/'PIPELINE_APPROVAL.json').read_bytes());s=approval['allowed_scope'];require(not s['external_models_released'] and not s['geology_released'],'RELEASE_SCOPE_EXPECTATION')
    def member(m):
        require(m['features'] in s['features'] and m['learner']['name'] in ('ExtraTrees','MultiOutputExtraTrees') and m['target']['scale'] in s['target_scales'],'OUTSIDE_ACTUAL_CODEX_SCOPE')
    if c['learner']['name']=='Ensemble':
        require(c['fusion']['method'] in s['fusion_methods'],'FUSION_NOT_RELEASED')
        for m in c['fusion']['members']:member(m)
    else:member(c)
def semantic(c):
    z=copy.deepcopy(c);z.pop('variant');z.pop('purpose');return fingerprint(z)
def representation(c):return fingerprint({k:c[k] for k in ('cutoff','target','features')})
def describe(panel,pred,folds,c):
    rows=[]
    for n,(tr,va) in enumerate(folds,1):
        v=summary(panel.iloc[va],pred[va]);rows.append({'fold':n,'score':v['official_score'],'weighted_losses':v['weighted_losses'],'train_wells':int(panel.iloc[tr].WELL_ID.nunique()),'validation_wells':int(panel.iloc[va].WELL_ID.nunique()),'well_overlap':0,'row_split_sha256':fold_hash(tr,va)})
    v=summary(panel,pred);ss=[f['score'] for f in rows];return {'score':v['official_score'],'fold_scores':ss,'worst_fold':min(ss),'fold_std_population':float(np.std(ss)),'weighted_losses':v['weighted_losses'],'official_formula_difference':v['official_cross_check_difference'],'folds':rows,'validation_coverage_each_row_once':True,'models_and_preprocessors_fitted_only_on_training_rows':True,'prediction_reuse':c}

def main(a):
    require(not (ROOT/'execution/STARTED.json').exists(),'DAILY_RUN_ALREADY_STARTED');verify_source_lock();initial=runtime_probe();save(ROOT/'execution/STARTED.json',{'time':__import__('datetime').datetime.now().isoformat(),'runner_sha256':file_sha(__file__),'plan_sha256':file_sha(ROOT/'PLAN_DAILY_SEARCH.json'),'actual_runtime':initial,'pipeline_lock_sha256':file_sha(HERE/'PIPELINE_LOCK.json'),'actual_approval_sha256':file_sha(HERE/'PIPELINE_APPROVAL.json')});tick=time.perf_counter();ledger=Ledger(ROOT/'execution/FIT_COUNTS.json');contract=json.loads((HERE/'DATA_CONTRACT.json').read_bytes());require(file_sha(a.data_dir)==contract['raw_archive_sha256'],'DATA_ARCHIVE_CHANGED');policy,legacy=load_locked_policy(a.policy);store=Inputs(a.data_dir)
    try:history=load_train(store,legacy)
    finally:store.close()
    provider=Panels(history,policy,legacy);template=load_variant(HERE/'configs/B0_prime.json');base_panel=provider.get(template)[0];splits=split_sets(base_panel);require(split_fingerprints(splits)==contract['split_fingerprints'],'ROW_SPLITS_CHANGED');panels={representation(template):provider.get(template)};records=[];done={};oofs={};completed={}
    stage0=json.loads((ROOT/'received/RESULT_STAGE0.json').read_bytes());prior=stage0['results']['B0_prime'];require(identity(base_panel,policy['feature_order'])==contract['B0_prime_identity'],'BASELINE_INPUT_CHANGED')
    require(initial['dependencies']==json.loads((HERE/'ENVIRONMENT_LOCK.json').read_bytes())['dependencies'],'REUSE_RUNTIME_IDENTITY');reference={'variant':'B0_prime','config':template,'results':prior,'reuse':'exact same algorithm, features, dtype, rows, target, model parameters, splits, source bytes and live dependencies; variant/purpose metadata only differ','OOF_available_in_this_process':False};records.append(reference);done[semantic(template)]=reference
    def cached(c):
        key=representation(c)
        if key in panels:provider.cache[fingerprint(c)]=panels[key]
        else:panels[key]=provider.get(c)
        return provider.get(c)
    def checkpoint():
        rank=sorted(records,key=lambda r:(-r['results']['repeated_summary']['mean'],r['results']['repeated_summary']['standard_error'],-r['results']['fixed']['score'],r['variant']));save(ROOT/'execution/PROGRESS.json',{'completed_configs':len(records),'top10':[{'variant':r['variant'],'repeat_mean':r['results']['repeated_summary']['mean'],'SE':r['results']['repeated_summary']['standard_error'],'fixed':r['results']['fixed']['score']} for r in rank[:10]],'fit_counts':{k:v for k,v in ledger.value.items() if k!='events'},'seconds':time.perf_counter()-tick});return rank
    def admit(c):
        scope_check(c);verify_source_lock();env=runtime_probe();require(env==initial,'RUNTIME_CHANGED_DURING_DAILY_BATCH');path=ROOT/'configs'/(c['variant']+'.json');require(not path.exists(),'CONFIG_ALREADY_LOCKED');save(path,c);p,f,audit=cached(c);stamp={'config_sha256':file_sha(path),'config_fingerprint':fingerprint(c),'semantic_identity':semantic(c),'runtime':env,'runtime_fingerprint':fingerprint(env),'pipeline_lock_sha256':file_sha(HERE/'PIPELINE_LOCK.json'),'private_policy_sha256':file_sha(a.policy),'raw_archive_sha256':contract['raw_archive_sha256'],'row_feature_identity':identity(p,f),'split_fingerprints':split_fingerprints(splits),'before_new_variant_fits_and_scores':True};save(ROOT/'configs'/(c['variant']+'.PRESCORE.json'),stamp);return p,f
    def evaluate(c):
        key=semantic(c)
        if key in done:return done[key]
        p,f=admit(c);name=c['variant'];folder=ROOT/'execution'/name;folder.mkdir();values={};predictions={};print('BEGIN '+name,flush=True)
        for sn,folds in splits.items():
            verify_source_lock();values[sn],predictions[sn]=evaluate_split(c,provider,folds,ledger,name+'-'+sn,folder)
        values['repeated_summary']=repeated_summary([values['repeat_'+str(i)] for i in range(1,6)]);row={'variant':name,'config':c,'results':values,'reuse':False,'OOF_available_in_this_process':True};records.append(row);done[key]=row;oofs[name]=predictions;completed[name]=row;save(folder/'RESULT.json',row);checkpoint();print('DONE '+name+' repeat='+str(values['repeated_summary']['mean']),flush=True);return row
    def make(scale,feat,trees=400,leaf=6,mf=.75,learner='ExtraTrees'):
        c=copy.deepcopy(template);c.update(variant=('ET' if learner=='ExtraTrees' else 'MO')+'_'+scale+'_'+('R' if feat.endswith('_R') else 'B')+f'_t{trees}_l{leaf}_f{int(mf*100)}',purpose='search',features=feat,target={'transform':'log1p' if scale=='none' else 'log_ratio','scale':scale});c['learner'].update(name=learner,n_estimators=trees,min_samples_leaf=leaf,max_features=mf);return c
    def fusion(c1,c2,method,name):
        c=copy.deepcopy(template);c.update(variant=name,purpose='search',learner={'name':'Ensemble'},fusion={'method':method,'members':[c1,c2]});return c
    def fuse_existing(members,method,name):
        c=fusion(members[0]['config'],members[1]['config'],method,name);admit(c);values={};predictions={};folder=ROOT/'execution'/name;folder.mkdir();first=cached(members[0]['config'])[0];print('BEGIN '+name,flush=True)
        for sn,folds in splits.items():
            pred=np.full(len(first),np.nan);weightlog=[]
            for k,(tr,va) in enumerate(folds,1):
                weights=[.5,.5];evidence={'source':'fixed equal','outer_validation_rows_used':0}
                if method=='inner_grid_0.1':
                    train=first.iloc[tr];inner=list(GroupKFold(5,shuffle=True,random_state=20260916).split(train,groups=train.WELL_ID));inner_preds=[]
                    for j,row in enumerate(members):
                        m=row['config'];p,f,_=cached(m);ip=np.full(len(tr),np.nan)
                        for z,(itr,iva) in enumerate(inner,1):
                            gtr=tr[itr];gva=tr[iva];require(not set(gtr)&set(va) and not set(gva)&set(va) and not set(p.iloc[gtr].WELL_ID)&set(p.iloc[gva].WELL_ID),'INNER_OUTER_OVERLAP');artifact=fit_single(p.iloc[gtr],f,m,legacy,ledger,f'{name}-{sn}-fold{k}-member{j}-inner{z}');ip[iva]=predict_single(artifact,p.iloc[gva],m)
                        inner_preds.append(ip)
                    weights,evidence=choose_weights_on_training_only(train,inner_preds,tr,va)
                arrays=[oofs[m['variant']][sn][va] for m in members];pred[va]=np.sum(np.asarray(arrays)*np.asarray(weights)[:,None],axis=0);weightlog.append({'fold':k,'weights':weights,'evidence':evidence,'outer_member_predictions':'exact matching already-fitted member, same environment/data/rows/features/splits, memory only; no repeated outer fit'})
            values[sn]=describe(first,pred,folds,'exact same-run outer member OOF');values[sn]['fusion_weight_log']=weightlog;predictions[sn]=pred
        values['repeated_summary']=repeated_summary([values['repeat_'+str(i)] for i in range(1,6)]);row={'variant':name,'config':c,'results':values,'reuse':'outer predictions only, weights inner fit if configured','OOF_available_in_this_process':True};records.append(row);done[semantic(c)]=row;oofs[name]=predictions;completed[name]=row;save(folder/'RESULT.json',row);checkpoint();print('DONE '+name+' repeat='+str(values['repeated_summary']['mean']),flush=True);return row
    try:
        with offline_only():
            factorial=[]
            for scale,feat in itertools.product(('last_legal','last3_valid_mean','presegment3_mean','none'),('base325','base325_R')):factorial.append(evaluate(make(scale,feat)))
            best=sorted(factorial,key=lambda r:(-r['results']['repeated_summary']['mean'],r['results']['repeated_summary']['standard_error'],-r['results']['fixed']['score'],r['variant']))[0];save(ROOT/'execution/ADAPTIVE_CHOICE_BEFORE_GRID.json',{'basis':'first factorial repeated-CV mean only','selected_representation':{k:best['config'][k] for k in ('target','features')},'source_variant':best['variant'],'chosen_before_grid_variant_fits':True});scale=best['config']['target']['scale'];feat=best['config']['features']
            for learner in ('ExtraTrees','MultiOutputExtraTrees'):
                for trees,leaf,mf in itertools.product((400,800),(2,4,6,10),(.3,.5,.75,1.)):
                    evaluate(make(scale,feat,trees,leaf,mf,learner))
            singles=sorted(completed.values(),key=lambda r:(-r['results']['repeated_summary']['mean'],r['results']['repeated_summary']['standard_error'],-r['results']['fixed']['score'],r['variant']));top=singles[:2];save(ROOT/'execution/FUSION_MEMBERS_BEFORE_SCORES.json',{'members':[r['variant'] for r in top],'basis':'top two complete newly evaluated singles by repeat mean','no_platform_feedback_used':True})
            fuse_existing(top,'equal','FUSION_TOP2_EQUAL');fuse_existing(top,'inner_grid_0.1','FUSION_TOP2_INNER01')
            # Legacy benchmark scalar results do not contain OOF. Evaluate its
            # new fixed-equal composite once through the unchanged core.
            old=load_variant(HERE/'configs/B0.json');old['purpose']='fusion_member';modern=copy.deepcopy(template);modern['purpose']='fusion_member';evaluate(fusion(old,modern,'equal','FUSION_B0_B0PRIME_EQUAL'))
        rank=checkpoint();eligible=[r for r in rank[:10] if r['variant'] in oofs];chosen=[];diversities=[]
        for r in eligible:
            differences=[]
            for q in chosen:
                aa=np.concatenate([oofs[r['variant']]['repeat_'+str(i)] for i in range(1,6)]);bb=np.concatenate([oofs[q['variant']]['repeat_'+str(i)] for i in range(1,6)]);differences.append(float(np.mean(np.abs(aa-bb)/(np.abs(aa)+np.abs(bb)+1e-6))))
            if all(v>=.05 for v in differences):chosen.append(r);diversities.append({'variant':r['variant'],'minimum_symmetric_prediction_difference_from_prior':min(differences) if differences else None})
            if len(chosen)==3:break
        save(ROOT/'execution/CANDIDATE_SELECTION.json',{'selected':[r['variant'] for r in chosen],'diversity_evidence':diversities,'selection_rule':'top10 repeat ranking, greedy >=.05 mean symmetric OOF difference, up to3','no_platform_labels_or_feedback_used':True,'full_versions_only':True})
        require(runtime_probe()==initial,'RUNTIME_CHANGED_AFTER_SEARCH');verify_source_lock();final={'task':'A2B-035/internal daily search first batch','role':'账户B执行与交付','status':'DAILY_SEARCH_COMPLETED_CANDIDATE_BUILD_NEXT','Codex_release_commit':'3001037a7d465117fd8062e5cbc6b2d168575fef','records':records,'ranking':[r['variant'] for r in rank],'selected_for_local_packages':[r['variant'] for r in chosen],'fit_counts':{k:v for k,v in ledger.value.items() if k!='events'},'seconds':time.perf_counter()-tick,'row_OOF_persisted':False,'external_models_or_G_used':False,'formal_platform_uploads':0,'S_v':'UNKNOWN','live_runtime_unchanged':True,'source_lock_unchanged':True,'whole_A2B035_final_designation_completed':False};save(ROOT/'execution/RESULT_DAILY_SEARCH.json',final);print('DAILY_SEARCH_COMPLETE selected='+','.join(final['selected_for_local_packages']),flush=True)
    except Exception as e:
        save(ROOT/'execution/FAILURE.json',{'type':type(e).__name__,'code':str(e) if isinstance(e,RuntimeError) else 'PRIVATE_TRACEBACK','counts':{k:v for k,v in ledger.value.items() if k!='events'}});(ROOT/'private/TRACEBACK.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data_dir',required=True);p.add_argument('--policy',required=True);main(p.parse_args())
