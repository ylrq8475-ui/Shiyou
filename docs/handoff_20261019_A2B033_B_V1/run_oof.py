"""R10 exactly-five-fit OOF, no retries. Threshold gates all later fitting."""
import argparse,contextlib,importlib.metadata,io,json,os,platform,sys,time,unittest,warnings
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'source'));from core import *
from fit_ledger import Ledger,fit_once
from sklearn.model_selection import GroupKFold
BASE=73.71410733861434
FOLDS=[71.45331390948151,77.53642908897099,75.12924056181325,64.62686399621428,79.96598872591244]
def arrhash(value):
    a=np.ascontiguousarray(value,dtype=np.int64);return sha(a.dtype.str.encode()+str(a.shape).encode()+a.tobytes())
def protected_files():
    files=[]
    for p in (R.parent/'Shiyou_B_private_handoff_20261009_v1/payload/project').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:files.append(p)
    for folder in R.parent.glob('A2B*'):
        if folder==R:continue
        files +=[p for p in folder.rglob('*.joblib') if p.is_file()]
    return {p:file_sha(p) for p in files}
def run(a):
    root=R/'execution';require(not root.exists(),'EXECUTION_ALREADY_EXISTS_NO_REFIT');root.mkdir()
    def save(n,x):(root/n).write_bytes(encode(x))
    ledger=Ledger(R/'private/FIT_LEDGER.json');result={'task':'A2B-033','role':'账户B执行与交付','R10_commit':'55adffb975204493cdc75567de8d74fc82dd3a73','T4_commit':'ce76e2ba0c3296f22f18a67bf212c05091b14573','status':'PREPARING','baseline':BASE,'baseline_fold_scores':FOLDS,'P2_reference':71.30071992041721,'score':None,'delta':None,'fold_scores':[],'paired_fold_deltas':[],'positive_folds':None,'worst_fold':None,'relative_to_P2':None,'weighted_losses':None,'step1_passed':False,'step2':'NOT_STARTED','models_saved':0,'test_prediction_rows_generated':0,'row_OOF_persisted':False,'platform_submissions':0,'hard_gates':{k:'UNKNOWN' for k in ('泄漏','错位','井级隔离','指标')},'historical_dtype':'UNKNOWN P1; inherited R5 exception, not repaired','decision_row_Codex':'不适用'}
    protected={};store=None
    try:
        output=io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):tests=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_033'))
        (root/'SYNTHETIC_LOG.txt').write_bytes(output.getvalue().encode());save('SYNTHETIC_RESULTS.json',{'tests':tests.testsRun,'passed':tests.wasSuccessful(),'real_model_fits':0,'real_preprocessor_fits':0,'simulated_ledger_tests_not_real_fits':True,'prefit_debug':'Initial synthetic ledger temp writes were unavailable in default temporary root; moved to this task synthetic_records, no real fit failure or retry.'});require(tests.wasSuccessful(),'SYNTHETIC_FAILED')
        original=Path(a.original_config);manifest=Path(a.manifest);archive=Path(a.archive);raw_ids={'config':file_sha(original),'manifest':file_sha(manifest),'archive':file_sha(archive)};require(raw_ids['config']=='89e60c301b1d553b1c7dab8e2f87d1d9a47b600abe4322f2e9895717201c0c72' and raw_ids['manifest']=='efd81b2fa8226f3a610fefb272f20f6a1adb61a98d02ff6885732b7a1312266f' and raw_ids['archive']=='813f0ebe71f6dddf64e8fbc6f365e15058c9952de16304f2f46392e96eca09c7','RAW_IDENTITY')
        store=Inputs(archive);decl=json.loads(manifest.read_bytes());require(len(store.files)==len(decl['files'])==100,'RAW_COUNT')
        for record in decl['files']:raw=store.raw(record['relative_path']);require(sha(raw)==record['sha256'] and len(raw)==record['bytes'],'RAW_MEMBER_DRIFT')
        policy_path=R/'private/runtime_policy.json';policy,config=load_policy(policy_path)
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):history=load_train(store,config);panel,features,anchors,structure=build_train(history,config,policy)
        policy['candidate_identity']=identity(panel,features);policy_path.write_bytes(encode(policy));plan=json.loads((R/'PLAN_R10.json').read_bytes());plan['private_policy_sha256']=file_sha(policy_path);(R/'PLAN_R10.json').write_bytes(encode(plan))
        splits=list(GroupKFold(5,shuffle=False).split(panel,groups=panel.WELL_ID));splitsha=fingerprint([(arrhash(tr),arrhash(va)) for tr,va in splits]);require(splitsha==policy['split_sha256'],'FOLD_IDENTITY');coverage=np.zeros(len(panel),int);fold_audit=[]
        for index,(tr,va) in enumerate(splits,1):
            require(not set(panel.iloc[tr].WELL_ID)&set(panel.iloc[va].WELL_ID),'WELL_ISOLATION');coverage[va]+=1;fold_audit.append({'fold':index,'train_wells':int(panel.iloc[tr].WELL_ID.nunique()),'valid_wells':int(panel.iloc[va].WELL_ID.nunique()),'train_rows':len(tr),'valid_rows':len(va),'well_overlap':0,'row_split_sha256':fingerprint((arrhash(tr),arrhash(va)))})
        require((coverage==1).all(),'OOF_COVERAGE');structure.update({'folds':fold_audit,'split_sha256':splitsha,'OOF_coverage_exactly_once':True,'test_history_parsed_for_OOF':0,'target_window_unchanged':True,'external_data':False});save('STRUCTURE_GATES.json',structure)
        env={'python':platform.python_version(),'build':platform.python_build(),'compiler':platform.python_compiler(),'executable_sha256':file_sha(sys.executable),'dependencies':dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())),'cpu_count':os.cpu_count(),'parallelism':plan['parallelism']};save('ENVIRONMENT_LOCK.json',env)
        protected=protected_files();save('PROTECTED_IDENTITY_BEFORE.json',{'protected_count':len(protected),'anonymous_hashes':{sha(str(p).encode()):v for p,v in protected.items()}})
        sources=list((R/'source').glob('*.py'))+[R/'source/FROZEN_SOURCES.json',R/'source/requirements.txt',R/'PLAN_R10.json',Path(__file__),policy_path]+list((R/'source/src/oil_uplift').glob('*.py'));locked={p:file_sha(p) for p in sources}
        lock={'before_first_real_fit_and_candidate_score':True,'source_sha256':{p.relative_to(R).as_posix():v for p,v in locked.items() if p!=policy_path},'private_policy_sha256':locked[policy_path],'raw_input_hashes':raw_ids,'environment_sha256':file_sha(root/'ENVIRONMENT_LOCK.json'),'ordered_feature_dtypes':list(zip(features,panel[features].dtypes.astype(str))),'candidate_identity':identity(panel,features),'baseline_identity':policy['baseline_identity'],'split_sha256':splitsha,'model_params':training._model_pipeline(safe.MODEL_NAME,panel[features],config).named_steps['model'].get_params(),'budget':{'models':7,'preprocessors':7,'OOF':5,'full':1,'clean_reproduction':1,'retries':0},'historical_dtype':'UNKNOWN'};save('IMPLEMENTATION_PREFIT_LOCK.json',lock)
        def unchanged():require(all(file_sha(p)==v for p,v in locked.items()) and file_sha(archive)==raw_ids['archive'] and file_sha(original)==raw_ids['config'] and file_sha(manifest)==raw_ids['manifest'],'SOURCE_OR_INPUT_CHANGED')
        pred=np.full(len(panel),np.nan);result['hard_gates'].update(泄漏='通过',错位='通过',井级隔离='通过')
        for fold,(tr,va) in enumerate(splits,1):
            unchanged()
            with warnings.catch_warnings(record=True),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                pipe=fit_once(panel.iloc[tr],features,config,ledger,f'OOF-{fold}');prediction=predict(pipe,panel.iloc[va],features,config)
            pred[va]=prediction;value=summary(panel.iloc[va],prediction);result['fold_scores'].append(value['official_score']);save(f'FOLD_{fold}.json',{'fold':fold,**value,'paired_baseline_score':FOLDS[fold-1],'paired_delta':value['official_score']-FOLDS[fold-1],'fit_counts':{k:v for k,v in ledger.value.items() if k!='events'}});unchanged();print(json.dumps({'fold_completed':fold,'score':value['official_score'],'paired_delta':value['official_score']-FOLDS[fold-1],'models_completed':ledger.value['models_completed']}),flush=True)
        value=summary(panel,pred);score=value['official_score'];delta=score-BASE;paired=[x-y for x,y in zip(result['fold_scores'],FOLDS)];positive=sum(x>0 for x in paired);passed=delta>=1 and positive>=4;unchanged()
        result.update({'status':'STEP1_PASSED_CONTINUE_STEP2' if passed else 'STOPPED_AT_STEP1_GATE','score':score,'delta':delta,'paired_fold_deltas':paired,'positive_folds':positive,'worst_fold':min(result['fold_scores']),'fold_standard_deviation_population':float(np.std(result['fold_scores'])),'relative_to_P2':score-result['P2_reference'],'weighted_losses':value['weighted_losses'],'step1_passed':passed,'metric_cross_check_difference':value['official_cross_check_difference'],'step1_decision_B':'分数差 ≥ +1.0 且 5 折中 ≥4 折为正' if passed else '分数差 ≤ 0' if delta<=0 else '0 < 分数差 < +1.0，或为正折数 < 4'});result['hard_gates']['指标']='通过'
        if passed:(R/'source/RELEASE_GATE.json').write_bytes(encode({'step1_passed':True,'delta':delta,'positive_folds':positive,'source_R10_commit':result['R10_commit'],'score':score,'not_platform_upload_authorization':True}))
    except Exception as exc:
        result.update({'status':'FAILED_STOP_NO_RETRY','failure_type':type(exc).__name__,'failure_code':str(exc) if type(exc) is RuntimeError else 'REDACTED_EXCEPTION_DETAILS'});print(json.dumps({'status':'FAILED_STOP_NO_RETRY','exception_type':type(exc).__name__}),flush=True)
    finally:
        if store:store.close()
        result['fit_counts']={k:v for k,v in ledger.value.items() if k!='events'};save('FIT_COUNTS.json',result['fit_counts']);save('RESULT_A2B033.json',result)
        if protected:save('INTEGRITY_AFTER_STEP1.json',{'protected_count':len(protected),'all_preexisting_files_unchanged':all(p.exists() and file_sha(p)==v for p,v in protected.items()),'anonymous_protected_snapshot_sha256':fingerprint({sha(str(p).encode()):v for p,v in protected.items()})})
    print(json.dumps({k:result[k] for k in ('status','score','delta','positive_folds','worst_fold','relative_to_P2','step1_passed','fit_counts')}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--manifest',required=True);p.add_argument('--original-config',required=True);run(p.parse_args())
