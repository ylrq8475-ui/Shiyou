"""R5 controlled 20-fit OOF run; all row data and predictions remain in memory."""
import argparse,contextlib,hashlib,importlib.metadata,io,json,os,platform,subprocess,sys,time,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.dont_write_bytecode=True
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from experiment_core import *
from train_reader import TrainingArchive,sha_file
R5='5154fd9b0363b2f2a51eda89d6169aa8a90d6580'
def stamp():return datetime.now(timezone(timedelta(hours=8))).isoformat()
def save(p,value):
    with Path(p).open('x',encoding='utf-8') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def environment():
    return {'python':platform.python_version(),'build':platform.python_build(),'compiler':platform.python_compiler(),'executable_sha256':sha_file(sys.executable),'dependencies':dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())),'cpu_count':os.cpu_count(),'parallelism':{'active_models':1,'model_n_jobs':-1,'folds_parallel':False,'BLAS_OpenMP_threads':1}}
def protected_snapshot(roots):
    return {str(p):sha_file(p) for r in roots for p in Path(r).rglob('*') if p.is_file() and not {'.git','__pycache__'}&set(p.parts)}
def main(a):
    require(a.authorized,'LOCAL_AUTHORIZATION_REQUIRED');root=Path(a.output);require(not root.exists(),'OUTPUT_ALREADY_EXISTS_DO_NOT_REFIT');root.mkdir(parents=True)
    counts={k:0 for k in ('model_entered','model_completed','model_failed','preprocessor_entered','preprocessor_completed','preprocessor_failed','retries','FM_model_fits')}
    events=[];store=None;protected={};locked={};start=time.perf_counter();r030=None;d030=None
    r={'task':'A2B-028/阶段1+A2B-029/零样本诊断','role':'账户B执行与交付','Claude_instruction_commit':R5,'status':'PREPARING','started_at':stamp(),'B0_reference':BASELINE,'B0_tolerance':1e-9,'B0_reproduced':None,'B0_reproduction_passed':False,'candidates':{},'FM_zero_shot_score':None,'FM_blend_score':None,'FM_blend_delta':None,'FM_blend_positive_folds':None,'fit_counts':counts,'hard_gates':{k:'UNKNOWN' for k in ('泄漏','错位','井级隔离','指标')},'historical_dtype':'UNKNOWN P1; user exception in R5, not closed by current replay','test_tables_parsed':0,'test_labels_read':False,'test_prediction_rows_generated':0,'row_OOF_persisted':False,'models_saved':0,'formal_packages_created':0,'platform_submissions':0,'decision_row_Codex':'不适用（待独立审核）'}
    def event(name,**extra):
        item={'sequence':len(events)+1,'time':stamp(),'event':name,'fit_counts':dict(counts),**extra};events.append(item);save(root/f'EVENT_{len(events):03d}.json',item);print(json.dumps({'event':name,**extra},ensure_ascii=True),flush=True)
    try:
        receipt=json.loads((HERE/'received/A027_SOURCE_RECEIPT.json').read_bytes())
        require(sha_file(HERE/'received/INSTRUCTION_ORIGINAL_R5.md')=='66f0f5bf1dfba5e9a3194a8eab051455e9f8e9cb0b2db6714739082ca83d552b','R5_IDENTITY')
        require(sha_file(a.config)==receipt['private_config_sha256'],'CONFIG_DRIFT')
        for row in receipt['project_sources']:require(sha_file(Path(a.project_src)/row['path'])==row['sha256'],'PROJECT_SOURCE_DRIFT')
        prereg=json.loads((HERE/'PREREG_A2B029.json').read_bytes())
        require(prereg['before_any_real_score'] is True and prereg['weight_sha256']==sha_file(Path(a.fm_model)/'model.safetensors'),'FM_PREREG_IDENTITY')
        require(prereg['model']=='amazon/chronos-bolt-tiny' and prereg['context_length']==512,'FM_MODEL_SELECTION_DRIFT')
        tests=io.StringIO();outcome=unittest.TextTestRunner(stream=tests,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_experiment'))
        (root/'SYNTHETIC_LOG.txt').write_text(tests.getvalue(),encoding='utf-8');save(root/'SYNTHETIC_RESULTS.json',{'passed':outcome.wasSuccessful(),'tests':outcome.testsRun,'model_fits':0,'preprocessor_fits':0});require(outcome.wasSuccessful(),'SYNTHETIC_FAILED')
        sys.path.insert(0,str(Path(a.project_src)))
        from sklearn.model_selection import GroupKFold
        from oil_uplift import training,a2b013_safe as safe,multistep as multi,config as cfg
        from oil_uplift.scoring import official_twelve_month_score
        config=safe.safe_config(cfg.load_config(a.config));store=TrainingArchive(a.archive,a.manifest)
        require(store.before==receipt['raw_input_hashes'],'RAW_IDENTITY_DRIFT')
        protected=protected_snapshot(a.protected_root)
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            tables=store.load_train(config,multi.MultiSourceTables);panel,audit,anchors=safe._build_train_panel(tables,config)
            features=training.configured_feature_columns(panel,config);cutoff=safe.audit_pre_anchor_cutoff(tables.history,anchors,config)
        ref=json.loads((HERE/'received/REFERENCE_PANEL_CONTRACT.json').read_bytes())['contract']
        require(len(panel)==972 and panel.WELL_ID.nunique()==81 and len(features)==325,'BASE_COHORT_DRIFT')
        require(features==ref['feature_order'] and identity(panel,features)==ref['panel_identity'],'BASE_PANEL_IDENTITY_DRIFT')
        splits=list(GroupKFold(5,shuffle=False).split(panel,groups=panel.WELL_ID));coverage=np.zeros(len(panel),int);fold_rows=np.full(len(panel),-1,int)
        for f,(tr,va) in enumerate(splits):
            require(not set(panel.iloc[tr].WELL_ID)&set(panel.iloc[va].WELL_ID),'WELL_ISOLATION');coverage[va]+=1;fold_rows[va]=f
        require((coverage==1).all(),'OOF_COVERAGE')
        sh=fingerprint([(array_hash(tr),array_hash(va)) for tr,va in splits]);require(sh==json.loads((HERE/'received/SPLIT_REFERENCE.json').read_bytes())['outer_split_sha256'],'FOLD_IDENTITY')
        h=tables.history;p=safe._periods(h,config['anchors']['date_column']);wcol=config['anchors']['well_column'];target=config['schema']['mapping']['target']
        for well,m in anchors[[wcol,'anchor_period']].itertuples(index=False,name=None):
            rows=panel.loc[panel.WELL_ID==well];require(rows.horizon.tolist()==list(range(1,13)) and (rows.anchor_time==m.to_timestamp()).all(),'TARGET_KEY_ALIGNMENT')
            truth=[]
            for step in range(1,13):
                raw=pd.to_numeric(h.loc[(h[wcol]==well)&(p==m+step),target],errors='coerce');require(len(raw)==1,'TARGET_CALENDAR_ALIGNMENT');truth.append(raw.iloc[0])
            require(np.array_equal(rows.RCYL.to_numpy(float),np.asarray(truth,float)),'TARGET_VALUE_ALIGNMENT')
            legal=h.loc[(h[wcol]==well)&(p<m)].assign(_p=p).sort_values('_p',kind='stable');last=float(pd.to_numeric(legal[target],errors='coerce').iloc[-1]);actual=float(rows['history__RCYL__last'].iloc[0])
            require(safe._same_feature_value(last,actual),'RAW_SCALE_CUTOFF')
        if a.diagnostics_src:
            import importlib.util
            spec=importlib.util.spec_from_file_location('diagnose_030',Path(a.diagnostics_src)/'diagnose_030.py');d030=importlib.util.module_from_spec(spec);spec.loader.exec_module(d030)
            r030=d030.prepare(a.diagnostics_output,store,h,anchors,cfg.load_config(a.config),safe)
            event('A030_N1_N2_completed_zero_fits')
        full=add_f0(panel,h,config,safe);aux,auxaudit=auxiliary_panel(h,anchors,config,safe);auxfull=add_f0(aux,h,config,safe)
        for well,m in anchors[[wcol,'anchor_period']].itertuples(index=False,name=None):
            one=f0_event(h,well,m,config,safe);two=f0_event(h.loc[(h[wcol]==well)&(p<m)],well,m,config,safe)
            require(all(safe._same_feature_value(one[k],two[k]) for k in one),'BASE_F0_FUTURE_SENSITIVITY')
        require(set(features)<=set(aux.columns) and not set(zip(panel.WELL_ID,panel.anchor_time,panel.horizon))&set(zip(aux.WELL_ID,aux.anchor_time,aux.horizon)),'AUX_DUPLICATES_BASE')
        fold_audit=[]
        for f,(tr,va) in enumerate(splits):
            valid_wells=set(panel.iloc[va].WELL_ID);aa=aux.loc[~aux.WELL_ID.isin(valid_wells)]
            require(not set(aa.WELL_ID)&valid_wells,'AUX_VALID_WELL_LEAK')
            fold_audit.append({'fold':f+1,'base_training_wells':int(panel.iloc[tr].WELL_ID.nunique()),'validation_wells':len(valid_wells),'base_training_rows':len(tr),'aux_training_rows':len(aa),'aux_events_in_train':int(aa[['WELL_ID','anchor_time']].drop_duplicates().shape[0]),'validation_well_intersection_all_events':0})
        contexts=[]
        for well,m in anchors[[wcol,'anchor_period']].itertuples(index=False,name=None):
            part=h.loc[(h[wcol]==well)&(p<m)];pp=p.loc[part.index];values=pd.to_numeric(part[target],errors='coerce')
            require(not pp.duplicated().any() and len(pp)>0,'FM_CONTEXT_MONTHS')
            series=pd.Series(values.to_numpy(float),index=pd.PeriodIndex(pp)).reindex(pd.period_range(pp.min(),m-1,freq='M')).iloc[-512:]
            require(series.index[-1]==m-1 and np.isfinite(series).any(),'FM_CONTEXT_CUTOFF')
            contexts.append([float(x) if np.isfinite(x) else None for x in series])
        structure={'history_cutoff':'M-1','targets':'M+1..M+12','baseline_cohort_wells':81,'baseline_rows':972,'baseline_features':325,'F0_extra_features':10,'F0_feature_names':F0_NAMES,'F0_original_numeric_pipeline_directly_applicable':True,'F0_missing_rule':'original SimpleImputer(median,add_indicator=True) and StandardScaler in each training fold','cutoff_audit':cutoff,'auxiliary':auxaudit,'folds':fold_audit,'split_sha256':sh,'test_tables_parsed':0,'all_raw_members_verified':100,'train_tables_parsed':88,'raw_archive_extracted':False,'FM_origin':'M-1','FM_generated_steps':13,'FM_discard_bridge_M':True,'FM_final_target_steps':12,'FM_native_missing':True}
        r['hard_gates'].update(泄漏='通过',错位='通过',井级隔离='通过');save(root/'STRUCTURE_GATES.json',structure)
        env=environment();save(root/'ENVIRONMENT_LOCK.json',env)
        paths=list(HERE.glob('*.py'))+[HERE/'PLAN_R5.json',HERE/'PREREG_A2B029.json',HERE/'FM_ENVIRONMENT_LOCK.json',Path(a.config),Path(a.manifest),Path(a.fm_model)/'model.safetensors',Path(a.fm_model)/'config.json']
        locked={str(z):sha_file(z) for z in paths}
        lock={'time':stamp(),'before_first_real_fit_and_score':True,'R5_commit':R5,'sources':{Path(z).name:hashvalue for z,hashvalue in locked.items()},'environment_sha256':sha_file(root/'ENVIRONMENT_LOCK.json'),'base_identity':identity(panel,features),'F0_identity':identity(full,features+F0_NAMES),'aux_identity':identity(aux,features),'aux_F0_identity':identity(auxfull,features+F0_NAMES),'ordered_feature_dtypes':list(zip(full[features+F0_NAMES].columns,full[features+F0_NAMES].dtypes.astype(str))),'folds':structure['folds'],'raw_inputs':store.before,'protected_count':len(protected),'protected_snapshot_digest':fingerprint(protected),'budget':{'model':20,'preprocessor':20,'retries':0},'historical_dtype':'UNKNOWN','FM_prereg_sha256':sha_file(HERE/'PREREG_A2B029.json')}
        save(root/'IMPLEMENTATION_PREFIT_LOCK.json',lock);event('all_structures_and_prereg_locked',aux_events=32,aux_rows=len(aux))
        def unchanged():require(store.unchanged() and all(sha_file(z)==v for z,v in locked.items()),'INPUT_SOURCE_DRIFT')
        def fitting(kind,role,fold,fn):
            unchanged();require(counts[kind+'_entered']<20,'FIT_BUDGET');counts[kind+'_entered']+=1;event(kind+'_fit_entered',config=role,fold=fold);tick=time.perf_counter()
            try:value=fn()
            except Exception:counts[kind+'_failed']+=1;event(kind+'_fit_failed',config=role,fold=fold);raise
            counts[kind+'_completed']+=1;event(kind+'_fit_completed',config=role,fold=fold,seconds=time.perf_counter()-tick);unchanged();return value
        expected=json.loads((HERE/'received/PREREG_PARAMETERS.json').read_bytes())['regressor']['params']
        require(panel.WELL_ID.iloc[::12].tolist()==anchors[wcol].tolist(),'FM_ROW_ORDER_ALIGNMENT')
        y=panel.RCYL.to_numpy(float).reshape(81,12);folds=fold_rows.reshape(81,12)[:,0]
        require(np.all(fold_rows.reshape(81,12)==folds[:,None]),'WELL_FOLD_ROWS')
        allpred={};alpha_records={};configs=[('B0',panel,None,features),('B0_F0',full,None,features+F0_NAMES),('B0_AUG',panel,aux,features),('B0_F0_AUG',full,auxfull,features+F0_NAMES)]
        def official_check(prediction):
            check=panel[['WELL_ID','horizon','RCYL']].copy();check['prediction']=prediction.reshape(-1)
            score=official_twelve_month_score(check,truth_column='RCYL',prediction_column='prediction',epsilon=1e-6).total
            require(abs(score-official_summary(y,prediction)['official_score'])<1e-10,'OFFICIAL_METRIC_MISMATCH')
        for name,data,extra,cols in configs:
            pred=np.full(len(panel),np.nan)
            for f,(tr,va) in enumerate(splits,1):
                train=data.iloc[tr].copy();valid=data.iloc[va]
                if extra is not None:train=pd.concat([train,extra.loc[~extra.WELL_ID.isin(set(valid.WELL_ID))]],ignore_index=True)
                require(not set(train.WELL_ID)&set(valid.WELL_ID),'TRAIN_VALID_WELL_LEAK')
                x=train[cols];pipe=training._model_pipeline('extra_trees_log_ratio_last',x,config);prep,model=pipe.named_steps['preprocess'],pipe.named_steps['model']
                require(model.get_params()==expected,'MODEL_PARAMS_DRIFT')
                z=training._transform_target(train.RCYL,train,'log_ratio_last')
                raw=train['history__RCYL__last'].to_numpy(float);scale=np.where(np.isfinite(raw)&(raw>0),raw,1.)
                require(np.array_equal(z,np.log1p(train.RCYL.to_numpy(float)/scale)),'TARGET_SCALE_TRANSFORM')
                xx=fitting('preprocessor',name,f,lambda:prep.fit_transform(x,z));fitting('model',name,f,lambda:model.fit(xx,z))
                pred[va]=training.predict_pipeline_output(pipe,'extra_trees_log_ratio_last',valid[cols],valid)
            pred=pred.reshape(81,12);official_check(pred);allpred[name]=pred
            if name=='B0':
                r['B0_reproduced']=official_summary(y,pred)['official_score'];r['B0_difference']=r['B0_reproduced']-BASELINE;r['B0_reproduction_passed']=abs(r['B0_difference'])<=1e-9
                save(root/'BASELINE_REPRODUCTION.json',{'score':r['B0_reproduced'],'reference':BASELINE,'difference':r['B0_difference'],'tolerance':1e-9,'passed':r['B0_reproduction_passed'],'fits':5,'same_evaluation_code':True})
                require(r['B0_reproduction_passed'],'B0_REPRODUCTION_FAILED_STOP_ALL');r['hard_gates']['指标']='通过';r['baseline_summary']=summarize(y,pred,folds)
                event('baseline_reproduced',score=r['B0_reproduced'])
                if r030 is not None:
                    d030.finish(a.diagnostics_output,r030,y,pred);r030=None;event('A030_N4_completed_same_process_memory_zero_fits')
            else:r['candidates'][name]=summarize(y,pred,folds,allpred['B0'])
            adjusted,records=cross_residual_adjust(y,pred,folds);official_check(adjusted)
            r['candidates'][name+'_ALPHA']=summarize(y,adjusted,folds,allpred['B0']);alpha_records[name]=records
            event('configuration_and_Dalpha_completed',config=name)
        require(counts['model_completed']==counts['preprocessor_completed']==20,'FIT_TOTAL')
        r['Dalpha_records']=alpha_records;r['Dalpha_caveat']='Prescribed other-fold residual diagnostic; no current fold labels used directly. Other-fold base models may include current validation wells. Not nested deployment validation or independent confirmation.'
        # Competition series and predictions travel only through anonymous pipes.
        request=json.dumps({'protocol':'A029_CONTEXT_ONLY_V1','contexts':contexts},allow_nan=False).encode()
        fm_env=os.environ.copy();fm_env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',PYTHONDONTWRITEBYTECODE='1')
        event('FM_offline_inference_started',models=1,competition_model_fits=0)
        process=subprocess.run([a.fm_python,'-I',str(HERE/'fm_worker.py'),'--model-dir',a.fm_model],input=request,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=fm_env,timeout=600)
        if process.returncode:
            r['FM_status']='BLOCKED_INFERENCE';r['FM_failure_class']='FM_CHILD_NONZERO';r['FM_stderr_sha256']=hashlib.sha256(process.stderr).hexdigest();r['FM_error_bytes']=len(process.stderr)
        else:
            payload=json.loads(process.stdout);fm=np.asarray(payload['prediction'],float);require(fm.shape==(81,12),'FM_OUTPUT_SHAPE');official_check(fm)
            r['FM_metadata']=payload['metadata'];require(r['FM_metadata']['weight_sha256']==prereg['weight_sha256'] and r['FM_metadata']['parameters']==prereg['parameters'],'FM_IDENTITY_DRIFT')
            r['FM_zero_shot_summary']=summarize(y,fm,folds,allpred['B0']);r['FM_zero_shot_score']=r['FM_zero_shot_summary']['score'];r['FM_status']='COMPLETED'
            if r['FM_zero_shot_score']>=70:
                blend,records=cross_blend(y,allpred['B0'],fm,folds);official_check(blend);summary=summarize(y,blend,folds,allpred['B0'])
                r.update(FM_blend_summary=summary,FM_blend_score=summary['score'],FM_blend_delta=summary['delta'],FM_blend_positive_folds=summary['positive_folds'],FM_blend_records=records)
            event('FM_diagnostic_completed',zero_shot_score=r['FM_zero_shot_score'],blend_score=r['FM_blend_score'])
        all_candidates=dict(r['candidates'])
        if 'FM_blend_summary' in r:all_candidates['B0_FM_BLEND']=r['FM_blend_summary']
        r['retained_candidates']=[k for k,v in all_candidates.items() if v.get('meets_retention')];r['selected_candidate_B_self_report']=select_retained(all_candidates)
        best=max(v['delta'] for v in r['candidates'].values());passed=any(v['meets_retention'] for v in r['candidates'].values())
        r['A028_decision_B_self_report']='某候选分数差 ≥ +1.0 且 5 折中 ≥4 折为正' if passed else ('所有候选分数差 ≤ 0' if best<=0 else '最佳候选 0 < 分数差 < +1.0，或达标折数 < 4')
        r['A029_decision_B_self_report']='UNKNOWN：推理未完成' if r['FM_zero_shot_score'] is None else ('零样本得分 < 70' if r['FM_zero_shot_score']<70 else ('零样本 ≥ 70，融合分数差 ≥ +1.0 且 ≥4/5 折为正' if r.get('FM_blend_summary',{}).get('meets_retention') else '零样本 ≥ 70，但融合未达上一行'))
        r['status']='COMPLETED' if r['FM_status']=='COMPLETED' else 'A028_COMPLETED_FM_BLOCKED'
    except Exception as exc:
        import traceback
        r['status']='STOPPED';r['stop_code']=str(exc) if type(exc).__name__=='GateError' else type(exc).__name__;r['sanitized_failure_frames']=[{'file':Path(t.filename).name,'line':t.lineno,'function':t.name} for t in traceback.extract_tb(exc.__traceback__)];event('stopped',code=r['stop_code'])
    finally:
        if r030 is not None:d030.finish(a.diagnostics_output,r030)
        r['integrity']={'protected_files_checked':len(protected),'protected_unchanged':all(Path(p).is_file() and sha_file(p)==v for p,v in protected.items()),'raw_archive_manifest_unchanged':store.unchanged() if store else None,'locked_source_inputs_unchanged':all(sha_file(p)==v for p,v in locked.items())}
        r['fit_counts']=dict(counts);r['finished_at']=stamp();r['elapsed_seconds']=time.perf_counter()-start
        save(root/'FIT_COUNTS.json',counts);save(root/'EVENTS.json',events);save(root/'RESULT_A2B028_029.json',r)
        if store:store.close()
        print(json.dumps({'status':r['status'],'counts':counts,'stop_code':r.get('stop_code')},ensure_ascii=True),flush=True)
    return 2 if r['status']=='STOPPED' else 0
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--authorized',action='store_true')
    for x in ('project-src','config','archive','manifest','output','fm-python','fm-model'):p.add_argument('--'+x,required=True)
    p.add_argument('--protected-root',action='append',default=[])
    p.add_argument('--diagnostics-src');p.add_argument('--diagnostics-output')
    sys.exit(main(p.parse_args()))
