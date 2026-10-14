"""Route B B-2: baseline first, 25-model/20-preprocessor cap, train-only OOF.

Run from a fixed repository checkout with its original src/ and the authorized
private archive/config/manifest. Never extracts data or saves models/row OOF.
"""
import argparse, contextlib, hashlib, importlib.metadata, io, json, os, platform, sys, time
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.dont_write_bytecode=True
for _name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_name]='1'
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from route_b_core import *
from train_reader import TrainingArchive,sha_file

def stamp():return datetime.now(timezone(timedelta(hours=8))).isoformat()
def write_new(p,x):
    payload=json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    with Path(p).open('x',encoding='utf-8') as f:f.write(payload)
def identity(frame,features,pd):
    return {'feature_order_sha256':fingerprint(features),'feature_dtype_sha256':fingerprint(list(zip(features,frame[features].dtypes.astype(str)))),'feature_frame_sha256':hashlib.sha256(pd.util.hash_pandas_object(frame[features],index=True).values.tobytes()).hexdigest(),'label_key_frame_sha256':hashlib.sha256(pd.util.hash_pandas_object(frame[['WELL_ID','horizon','RCYL']],index=True).values.tobytes()).hexdigest()}
def validate_splits(frame,splits):
    coverage=np.zeros(len(frame),int);universe=set(range(len(frame)))
    for tr,va in splits:
        require(len(tr)==len(set(tr)) and len(va)==len(set(va)) and not set(tr)&set(va) and set(tr)|set(va)==universe,'SPLIT_ROW_PARTITION')
        require(not set(frame.iloc[tr].WELL_ID)&set(frame.iloc[va].WELL_ID),'WELL_ISOLATION_FAILED')
        coverage[va]+=1
    require(np.array_equal(coverage,np.ones(len(frame),int)),'OOF_COVERAGE_FAILED')
def protected_snapshot(roots):
    answer={}
    for root in roots:
        root=Path(root)
        require(root.exists(),'PROTECTED_ROOT_MISSING')
        for p in root.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts:answer[str(p)]=sha_file(p)
    return answer

def main(a):
    require(a.authorized,'LOCAL_DATA_AUTHORIZATION_REQUIRED')
    root=Path(a.output);require(not root.exists(),'OUTPUT_ALREADY_EXISTS_NO_RETRAIN');root.mkdir(parents=True)
    budget=FitBudget();events=[];store=None;protected={};counts=budget.counts
    gates={name:'UNKNOWN' for name in ('泄漏','错位','井级隔离','指标')}
    result={'task':'A2B-026/路线B-B2','role':'账户B执行与交付','status':'PREPARING','started_at':stamp(),'baseline_reference':BASELINE,'baseline_tolerance':TOLERANCE,'baseline_reproduced':None,'baseline_difference':None,'baseline_gate_passed':False,'two_stage_OOF':None,'OOF 分数差':None,'分数差':None,'threshold_selection_records':[],'fit_counts':counts,'hard_gates':gates,'test_labels_read':False,'test_tables_parsed':0,'test_predictions_generated':0,'model_weights_loaded':0,'model_weights_saved':0,'submission_packages_created':0,'platform_submissions':0,'decision_row_B_self_report':None,'decision_row_Codex':'不适用（待独立审核）','Claude_instruction_commit':a.claude_commit,'rules_commit':'0536eafab45b71ffd5f8f0160ee7957f1edd661d','preregistration_commit':'213b1b465c61d799371e2b4326ebc71922c4f7ee','startup_original':STARTUP,'historical_dtype':'UNKNOWN','new_environment_not_historical_identity_claim':True}
    def event(name,**extra):
        row={'sequence':len(events)+1,'time':stamp(),'event':name,'fit_counts':budget.snapshot(),**extra};events.append(row)
        write_new(root/f'EVENT_{len(events):03d}.json',row)
        print(json.dumps({'event':name,'model_fits':counts['model_completed'],'preprocessor_fits':counts['preprocessor_completed'],**extra},ensure_ascii=True),flush=True)
    t0=time.perf_counter()
    try:
        params=json.loads(Path(a.prereg_parameters).read_bytes())
        received=json.loads((HERE/'SOURCE_RECEIPT.json').read_bytes())
        require(a.claude_commit==received['Claude_instruction']['commit'] and sha_file(a.claude_original)==received['Claude_instruction']['sha256'],'CLAUDE_SOURCE_IDENTITY')
        archive=Path(a.claude_original).read_text(encoding='utf-8-sig')
        require(TABLE in archive and STARTUP in archive and '批准B-2并发布' in archive,'CLAUDE_INSTRUCTION_SCOPE_MISMATCH')
        require(sha_file(a.prereg_parameters)==received['prereg_parameters']['sha256'],'PREREG_BYTE_IDENTITY')
        codex=json.loads(Path(a.codex_result).read_bytes());require(codex['item_11_closed'] is True,'CODEX_ITEM11_NOT_CLOSED')
        require(json.loads((HERE/'SYNTHETIC_RESULTS.json').read_bytes())['passed'],'SYNTHETIC_GATE_NOT_PASSED')
        sys.path.insert(0,str(Path(a.project_src)))
        import pandas as pd
        from sklearn.model_selection import GroupKFold
        from sklearn.ensemble import ExtraTreesClassifier
        from oil_uplift import training,a2b013_safe as safe,multistep as multi,config as config_module
        from oil_uplift.scoring import official_twelve_month_score
        for row in received['project_sources']:
            require(sha_file(Path(a.project_src)/row['path'])==row['sha256'],'PROJECT_SOURCE_DRIFT')
        env={'python':platform.python_version(),'build':platform.python_build(),'compiler':platform.python_compiler(),'executable_role':'approved isolated Python interpreter','versions':dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())),'cpu_count':os.cpu_count(),'parallelism':{'active_models':1,'model_n_jobs':-1,'folds_parallel':False,'BLAS_OpenMP_threads':1},'executable_sha256':sha_file(sys.executable)}
        write_new(root/'ENVIRONMENT_LOCK.json',env)
        event('required_imports_passed_no_real_fit')
        config=safe.safe_config(config_module.load_config(a.config))
        require(sha_file(a.config)==received['private_config_sha256'],'PRIVATE_CONFIG_DRIFT')
        store=TrainingArchive(a.archive,a.manifest)
        require(store.before==received['raw_input_hashes'],'RAW_IDENTITY_DRIFT')
        protected=protected_snapshot(a.protected_root)
        initial_files={str(p):sha_file(p) for p in HERE.glob('*.py')}
        for p in [Path(a.config),Path(a.manifest),Path(a.claude_original),Path(a.prereg_parameters),Path(a.codex_result),Path(a.history_lock)]:initial_files[str(p)]=sha_file(p)
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            tables=store.load_train(config,multi.MultiSourceTables)
            panel,audit,anchors=safe._build_train_panel(tables,config)
            features=training.configured_feature_columns(panel,config)
            cutoff=safe.audit_pre_anchor_cutoff(tables.history,anchors,config)
        require(len(panel)==972 and panel.WELL_ID.nunique()==81 and len(features)==325,'COHORT_FEATURE_COUNT_DRIFT')
        require(not {'WELL_ID','RCYL','anchor_time','NY'}&set(features) and not any(x.startswith(('layer__','plan_first__')) for x in features),'FORBIDDEN_FEATURE')
        frozen=json.loads(Path(a.history_lock).read_bytes())['contract']
        require(identity(panel,features,pd)==frozen['panel_identity'] and features==frozen['feature_order'],'FROZEN_PANEL_IDENTITY_DRIFT')
        require(fingerprint(features)==params['features']['feature_order_sha256'],'PREREG_FEATURE_ORDER_DRIFT')
        require(np.isfinite(panel.RCYL).all() and (panel.RCYL>=0).all(),'INVALID_TARGET')
        periods=safe._periods(tables.history,config['anchors']['date_column'])
        well_col=config['anchors']['well_column'];target_col=config['schema']['mapping']['target']
        for well,m in anchors[[well_col,'anchor_period']].itertuples(index=False,name=None):
            rows=panel.loc[panel.WELL_ID==well]
            require(rows.horizon.tolist()==list(range(1,13)) and (rows.anchor_time==m.to_timestamp()).all(),'TARGET_WINDOW_ALIGNMENT')
            truth=[]
            for h in range(1,13):
                raw=tables.history.loc[(tables.history[well_col]==well)&(periods==m+h),target_col]
                require(len(raw)==1,'TARGET_MONTH_MISSING_OR_DUPLICATE');truth.append(float(pd.to_numeric(raw).iloc[0]))
            require(np.array_equal(rows.RCYL.to_numpy(float),np.array(truth)),'TARGET_VALUE_ALIGNMENT')
            legal=tables.history.loc[(tables.history[well_col]==well)&(periods<m)]
            require(len(legal)>0,'NO_LEGAL_HISTORY')
            legal=legal.assign(_period=periods.loc[legal.index]).sort_values('_period',kind='mergesort')
            last=float(pd.to_numeric(legal[target_col],errors='coerce').iloc[-1]);constructed=float(rows['history__RCYL__last'].iloc[0])
            require((np.isnan(last) and np.isnan(constructed)) or last==constructed,'RAW_SCALE_NOT_LEGAL_LAST')
        require(np.array_equal(raw_scale(panel['history__RCYL__last']),training._target_scale(panel,'log_ratio_last')),'SCALE_TRANSFORM_MISMATCH')
        splits=list(GroupKFold(5,shuffle=False).split(panel,groups=panel.WELL_ID));validate_splits(panel,splits)
        split_hash=fingerprint([(array_hash(tr),array_hash(va)) for tr,va in splits])
        require(split_hash==params['validation']['outer_split_sha256'],'ORIGINAL_OUTER_FOLD_DRIFT')
        inner_plan=[]
        for tr,va in splits:
            outer_train=panel.iloc[tr]
            inner=list(GroupKFold(3,shuffle=False).split(outer_train,groups=outer_train.WELL_ID));validate_splits(outer_train,inner);inner_plan.append(inner)
        structural={'train_wells':81,'train_rows':972,'features':325,'feature_order_sha256':fingerprint(features),'outer_split_sha256':split_hash,'all_outer_inner_well_intersections':0,'all_target_windows_M_plus_1_to_12':True,'raw_scale_from_legal_cutoff':True,'history_cutoff':'M-1','cutoff_audit':cutoff,'test_tables_parsed':0,'raw_members_byte_verified_only':100,'train_history_tables_parsed':88,'archive_extracted_or_copied':False}
        gates.update(泄漏='通过',错位='通过',井级隔离='通过')
        write_new(root/'STRUCTURE_GATES.json',structural)
        implementation_lock={'time':stamp(),'before_first_real_fit_and_new_score':True,'Claude_instruction_commit':a.claude_commit,'source_receipt_sha256':sha_file(HERE/'SOURCE_RECEIPT.json'),'environment_sha256':sha_file(root/'ENVIRONMENT_LOCK.json'),'params_sha256':sha_file(a.prereg_parameters),'source_fingerprints':{Path(p).name:h for p,h in initial_files.items()},'new_panel_identity':identity(panel,features,pd),'ordered_dtypes':list(zip(features,panel[features].dtypes.astype(str))),'features':features,'structure':structural,'protected_old_files_count':len(protected),'protected_old_digest':fingerprint(protected),'budgets':params['budget_proposed_for_separate_B2_approval'],'baseline_tolerance':TOLERANCE,'baseline_first_then_reuse_in_memory':True,'historical_dtype':'UNKNOWN'}
        write_new(root/'IMPLEMENTATION_PREFIT_LOCK.json',implementation_lock)
        event('pre_fit_lock_and_structural_gates_passed')
        def unchanged():
            require(store.unchanged() and all(sha_file(p)==h for p,h in initial_files.items()),'RUNTIME_INPUT_OR_SOURCE_CHANGED')
        def fit_call(kind,role,fold,fn):
            unchanged();budget.enter(kind,role);tick=time.perf_counter();event(kind+'_fit_entered',role=role,outer_fold=fold)
            try:answer=fn()
            except Exception:
                budget.failed(kind);event(kind+'_fit_failed',role=role,outer_fold=fold);raise
            budget.completed(kind);event(kind+'_fit_completed',role=role,outer_fold=fold,seconds=time.perf_counter()-tick)
            unchanged();return answer
        def fit_reg(train,valid,role,fold):
            require(not set(train.WELL_ID)&set(valid.WELL_ID),'FOLD_TRAIN_VALID_OVERLAP')
            x=train[features]
            pipe=training._model_pipeline('extra_trees_log_ratio_last',x,config)
            prep,model=pipe.named_steps['preprocess'],pipe.named_steps['model']
            require(model.get_params()==params['regressor']['params'],'REGRESSOR_HYPERPARAMETER_DRIFT')
            z=training._transform_target(train.RCYL,train,'log_ratio_last')
            require(np.array_equal(z,np.log1p(train.RCYL.to_numpy(float)/raw_scale(train['history__RCYL__last']))),'TARGET_TRANSFORM_DRIFT')
            xt=fit_call('preprocessor',role,fold,lambda:prep.fit_transform(x,z))
            require(np.array_equal(np.asarray(xt),np.asarray(prep.transform(x)),equal_nan=True),'PREPROCESS_SCOPE_MISMATCH')
            fit_call('model',role,fold,lambda:model.fit(xt,z))
            p=np.clip(training.predict_pipeline_output(pipe,'extra_trees_log_ratio_last',valid[features],valid),0,None)
            require(np.isfinite(p).all(),'NONFINITE_B0_PREDICTION')
            return pipe,xt,p
        def summary(frame,p):
            own=numeric_summary(frame,p)
            check=frame[['WELL_ID','horizon','RCYL']].copy();check['prediction']=p
            official=official_twelve_month_score(check,truth_column='RCYL',prediction_column='prediction',epsilon=EPSILON).total
            require(abs(official-own['official_score'])<1e-10,'OFFICIAL_METRIC_MISMATCH')
            own['official_score']=float(official);return own
        b0=np.full(len(panel),np.nan);cached=[];b0_folds=[]
        for fold,(tr,va) in enumerate(splits,1):
            pipe,xt,p=fit_reg(panel.iloc[tr],panel.iloc[va],'outer_regressor',fold)
            b0[va]=p;cached.append((pipe,xt));b0_folds.append(summary(panel.iloc[va],p)['official_score'])
        result['baseline_summary']=summary(panel,b0);gates['指标']='通过'
        result['baseline_reproduced']=result['baseline_summary']['official_score'];result['baseline_difference']=result['baseline_reproduced']-BASELINE
        result['baseline_fold_scores']=b0_folds;result['baseline_worst_fold']=min(b0_folds);result['baseline_fold_std_ddof0']=float(np.std(b0_folds,ddof=0))
        result['baseline_gate_passed']=abs(result['baseline_difference'])<=TOLERANCE
        write_new(root/'BASELINE_REPRODUCTION.json',{'reproduced':result['baseline_reproduced'],'reference':BASELINE,'difference':result['baseline_difference'],'tolerance':TOLERANCE,'passed':result['baseline_gate_passed'],'fold_scores':b0_folds,'fits':budget.snapshot()})
        event('baseline_reproduction_evaluated',passed=result['baseline_gate_passed'],absolute_difference=abs(result['baseline_difference']))
        require(result['baseline_gate_passed'],'BASELINE_REPRODUCTION_FAILED_STOP_BEFORE_ROUTE_B')
        candidate=np.full(len(panel),np.nan);routed=np.zeros(len(panel),bool);candidate_folds=[]
        for fold,((tr,va),inner,(pipe,xt)) in enumerate(zip(splits,inner_plan,cached,strict=True),1):
            train,valid=panel.iloc[tr],panel.iloc[va];inner_records=[];lp_values=[]
            for inner_fold,(itr,iva) in enumerate(inner,1):
                ipipe,ixt,ip=fit_reg(train.iloc[itr],train.iloc[iva],'inner_regressor',fold)
                lp,meta=positive_inner_loss(train.iloc[iva],ip);lp_values.append(lp);inner_records.append({'inner_fold':inner_fold,'training_wells':int(train.iloc[itr].WELL_ID.nunique()),'validation_wells':int(train.iloc[iva].WELL_ID.nunique()),'well_intersection':0,**meta})
                del ipipe,ixt,ip
            tau,lp=tau_from_folds(lp_values)
            event('tau_frozen_from_inner_folds_before_classifier',outer_fold=fold,tau=tau,l_plus=lp)
            clf=ExtraTreesClassifier(**params['classifier']['params'])
            require(clf.get_params()==params['classifier']['params'],'CLASSIFIER_HYPERPARAMETER_DRIFT')
            label=zero_labels(train.RCYL)
            require(np.array_equal(np.asarray(xt),np.asarray(pipe.named_steps['preprocess'].transform(train[features])),equal_nan=True),'SHARED_PREPROCESS_REUSE_DRIFT')
            fit_call('model','outer_classifier',fold,lambda:clf.fit(xt,label))
            q=zero_probability(clf,pipe.named_steps['preprocess'].transform(valid[features]))
            pred,route=route_prediction(b0[va],q,tau);candidate[va]=pred;routed[va]=route
            score=summary(valid,pred)['official_score'];candidate_folds.append(score)
            result['threshold_selection_records'].append({'outer_fold':fold,'tau':tau,'l_plus':lp,'inner_fold_estimates':inner_records,'tau_method':'fixed formula; equal mean of three inner-fold positive conditional losses','outer_OOF_used_for_tau':False,'inner_classifier_fits':0,'train_zero_rows':int(label.sum()),'train_positive_rows':int((label==0).sum()),'validation_rows_routed_to_zero':int(route.sum()),'unrouted_B0_outputs_identical':True})
            event('outer_two_stage_fold_completed',outer_fold=fold,rows_routed_to_zero=int(route.sum()))
        require(np.isfinite(candidate).all(),'CANDIDATE_OOF_COVERAGE')
        result['candidate_summary']=summary(panel,candidate);result['two_stage_OOF']=result['candidate_summary']['official_score']
        delta=result['two_stage_OOF']-result['baseline_reproduced'];result['OOF 分数差']=delta;result['分数差']=delta
        result['candidate_fold_scores']=candidate_folds;result['candidate_worst_fold']=min(candidate_folds);result['candidate_fold_std_ddof0']=float(np.std(candidate_folds,ddof=0))
        result['paired_fold_deltas']=[c-b for c,b in zip(candidate_folds,b0_folds,strict=True)]
        y=panel.RCYL.to_numpy(float);h=panel.horizon.to_numpy(float);signed=(losses(y,b0)-losses(y,candidate))*np.power(.5,h)*100/81
        contributions=[]
        for name,mask in [('true_zero_routed',routed&(y==0)),('true_positive_routed',routed&(y>0)),('unrouted',~routed)]:
            contributions.append({'group':name,'rows':int(mask.sum()),'wells':int(panel.loc[mask,'WELL_ID'].nunique()),'net_official_points':float(np.sum(signed[mask]))})
        require(abs(sum(x['net_official_points'] for x in contributions)-delta)<1e-9,'ERROR_CONTRIBUTION_NOT_CLOSED')
        result['error_contributions']=contributions;result['routing_counts']={'total_rows_routed':int(routed.sum()),'true_zero_rows_routed':int((routed&(y==0)).sum()),'true_positive_rows_routed':int((routed&(y>0)).sum()),'unrouted_rows':int((~routed).sum()),'target_zero_rows':int((y==0).sum())}
        require(counts['model_entered']==counts['model_completed']==25 and counts['preprocessor_entered']==counts['preprocessor_completed']==20 and counts['inner_regressor']==15 and counts['outer_regressor']==5 and counts['outer_classifier']==5,'FINAL_FIT_BUDGET_COUNT_MISMATCH')
        result['decision_row_B_self_report']=decision(delta,True);result['status']='COMPLETED';event('B2_completed',baseline=result['baseline_reproduced'],candidate=result['two_stage_OOF'],delta=delta)
    except Exception as exc:
        result['status']='STOPPED';result['stop_code']=str(exc) if isinstance(exc,GateError) else type(exc).__name__
        result['decision_row_B_self_report']='不适用（实验未完成，不将运行阻断误判为候选淘汰）'
        if isinstance(exc,GateError) and any(x in str(exc) for x in ('ISOLATION','TARGET','SCORING','METRIC','FORBIDDEN_FEATURE','CUTOFF','COHORT','SCALE','INPUT_OR_SOURCE')):
            result['decision_row_B_self_report']=decision(0,False)
        event('execution_stopped',stop_code=result['stop_code'])
    finally:
        old_ok=all(Path(p).is_file() and sha_file(p)==h for p,h in protected.items())
        raw_ok=store is not None and store.unchanged()
        result['integrity']={'protected_old_files_checked':len(protected),'protected_old_files_unchanged':old_ok,'archive_and_manifest_unchanged':raw_ok,'private_config_unchanged':sha_file(a.config)==json.loads((HERE/'SOURCE_RECEIPT.json').read_bytes())['private_config_sha256']}
        if result['status']=='COMPLETED' and not (old_ok and raw_ok and result['integrity']['private_config_unchanged']):
            result['status']='STOPPED';result['stop_code']='POST_RUN_INTEGRITY_FAILED';result['decision_row_B_self_report']=decision(0,False)
        result['fit_counts']=budget.snapshot();result['finished_at']=stamp();result['elapsed_seconds']=time.perf_counter()-t0
        write_new(root/'FIT_COUNTS.json',budget.snapshot());write_new(root/'EVENTS.json',events);write_new(root/'RESULT_B2.json',result)
        if store:store.close()
        print(json.dumps({'status':result['status'],'model_fits':counts['model_completed'],'preprocessor_fits':counts['preprocessor_completed'],'baseline':result['baseline_reproduced'],'candidate':result['two_stage_OOF'],'delta':result['OOF 分数差'],'stop_code':result.get('stop_code')},ensure_ascii=True),flush=True)
    return 0 if result['status']=='COMPLETED' else 2

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('archive','manifest','config','history-lock','prereg-parameters','claude-original','claude-commit','codex-result','output'):p.add_argument('--'+n,required=True)
    p.add_argument('--project-src',default=str(HERE.parents[1]/'src'))
    p.add_argument('--protected-root',action='append',default=[])
    p.add_argument('--authorized',action='store_true')
    try:sys.exit(main(p.parse_args()))
    except GateError as e:print(json.dumps({'status':'PRE_RUN_BLOCKED','code':str(e)}));sys.exit(2)
