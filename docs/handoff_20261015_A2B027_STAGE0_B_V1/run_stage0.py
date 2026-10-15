"""A2B-027 stage 0. No model fitting, raw extraction or row-level persistence."""
import argparse, contextlib, hashlib, importlib.metadata, io, json, os, platform, sys, time, unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
sys.dont_write_bytecode=True
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from diagnostic_core import *

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp():return datetime.now(timezone(timedelta(hours=8))).isoformat()
def write_new(p,obj):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def identity(frame,features,pd):
    return {'feature_order_sha256':fingerprint(features),'feature_dtype_sha256':fingerprint(list(zip(features,frame[features].dtypes.astype(str)))),'feature_frame_sha256':hashlib.sha256(pd.util.hash_pandas_object(frame[features],index=True).values.tobytes()).hexdigest(),'label_key_frame_sha256':hashlib.sha256(pd.util.hash_pandas_object(frame[['WELL_ID','horizon','RCYL']],index=True).values.tobytes()).hexdigest()}

def main(args):
    require(args.authorized,'DATA_AUTHORIZATION_REQUIRED')
    root=Path(args.output);require(not root.exists(),'OUTPUT_EXISTS_NO_AUTOMATIC_REPEAT');root.mkdir()
    import pandas as pd
    sys.path.insert(0,str(Path(args.project_src)))
    from oil_uplift import a2b013_safe as safe,training,multistep as multi,config as cfg
    from oil_uplift.scoring import official_twelve_month_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.base import BaseEstimator
    import sklearn.ensemble,sklearn.preprocessing,sklearn.impute,sklearn.tree,sklearn.decomposition,joblib
    prior_reader=HERE.parent/'A2B026_ROUTE_B_B2_20261014_v1'
    sys.path.insert(0,str(prior_reader))
    from train_reader import TrainingArchive
    counts={'model_fit_attempted':0,'model_fit_completed':0,'preprocessor_fit_entered':0,'preprocessor_fit_completed':0,'preprocessor_fit_failed':0,'forbidden_preprocessing_attempts':0,'model_weights_loaded':0,'model_weights_saved':0,'synthetic_SVD_calls':0}
    def blocked(*a,**k):
        counts['model_fit_attempted']+=1;raise GateError('ANY_ESTIMATOR_FIT_FORBIDDEN')
    def no_prep(*a,**k):
        counts['forbidden_preprocessing_attempts']+=1;raise GateError('NON_SVD_PREPROCESSING_FORBIDDEN')
    for module,fn in [(sklearn.ensemble,blocked),(sklearn.tree,blocked),(sklearn.preprocessing,no_prep),(sklearn.impute,no_prep),(sklearn.decomposition,no_prep)]:
        for cls in vars(module).values():
            if isinstance(cls,type) and issubclass(cls,BaseEstimator):
                for name in ('fit','fit_transform','partial_fit'):
                    if hasattr(cls,name):setattr(cls,name,fn)
    for cls in (Pipeline,ColumnTransformer):
        for name in ('fit','fit_transform','partial_fit'):
            if hasattr(cls,name):setattr(cls,name,no_prep)
    def no_weight(*a,**k):raise GateError('WEIGHT_IO_FORBIDDEN')
    joblib.load=joblib.dump=no_weight
    def no_rows(*a,**k):raise GateError('ROW_PERSISTENCE_FORBIDDEN')
    for name in ('to_csv','to_pickle','to_parquet','to_feather','to_excel'):
        setattr(pd.DataFrame,name,no_rows)
    np.save=np.savez=np.savez_compressed=no_rows
    original_svd=np.linalg.svd
    allow_svd=False
    def guarded_svd(*a,**k):
        require(allow_svd,'SVD_OUTSIDE_AUTHORIZED_TRAINING_FOLD')
        return original_svd(*a,**k)
    np.linalg.svd=guarded_svd
    events=[]
    def event(name,**more):
        e={'sequence':len(events)+1,'time':stamp(),'event':name,'fit_counts':dict(counts),**more};events.append(e)
        write_new(root/f'EVENT_{len(events):03d}.json',e)
        print(json.dumps({'event':name,**more},ensure_ascii=True),flush=True)
    plan=json.loads((HERE/'PLAN_STAGE0.json').read_bytes())
    receipt=json.loads((HERE/'SOURCE_RECEIPT.json').read_bytes())
    protected={}
    for base in args.protected_root:
        for p in Path(base).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts:protected[str(p)]=sha(p)
    own={str(p):sha(p) for p in HERE.glob('*') if p.is_file() and p.suffix in ('.py','.json')}
    result={'task':'A2B-027/阶段0合并诊断','role':'账户B执行与交付','status':'STARTED','started_at':stamp(),'Claude_instruction_commit':plan['Claude_instruction_commit'],'delta':DELTA,'epsilon':EPSILON,'model_fits':0,'preprocessor_fits':0,'Dalpha_score':None,'Dalpha_delta':None,'Dalpha_losses':None,'hard_gates':{k:'UNKNOWN' for k in ('泄漏','错位','井级隔离','指标')},'test_labels_read':False,'test_predictions_generated':0,'external_training_data_used':False,'pretrained_models_used':False,'formal_packages_created':0,'platform_submissions':0,'historical_dtype':'UNKNOWN P1; nonblocking for stage0 under R4','open_unknowns':[]}
    store=None;start=time.perf_counter()
    try:
        require(sha(HERE/'received/INSTRUCTION_ORIGINAL_R4.md')==receipt['R4']['sha256'],'R4_SOURCE_CHANGED')
        for item in receipt['project_sources']:require(sha(Path(args.project_src)/item['path'])==item['sha256'],'PROJECT_SOURCE_CHANGED')
        require(sha(args.config)==receipt['private_config_sha256'],'PRIVATE_CONFIG_CHANGED')
        buf=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromName('test_diagnostics')
        tests=unittest.TextTestRunner(stream=buf,verbosity=2).run(suite)
        (root/'SYNTHETIC_LOG.txt').write_text(buf.getvalue(),encoding='utf-8')
        write_new(root/'SYNTHETIC_RESULTS.json',{'tests':tests.testsRun,'passed':tests.wasSuccessful(),'model_fits':0,'preprocessor_fits':0,'SVD_calls':0})
        require(tests.wasSuccessful() and tests.testsRun==16,'SYNTHETIC_GATE_FAILED')
        event('synthetic_checks_passed_before_competition_data',tests=16)
        config=safe.safe_config(cfg.load_config(args.config));store=TrainingArchive(args.archive,args.manifest)
        require(store.before==receipt['raw_input_hashes'],'RAW_IDENTITY_CHANGED')
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            tables=store.load_train(config,multi.MultiSourceTables)
            panel,audit,anchors=safe._build_train_panel(tables,config)
            features=training.configured_feature_columns(panel,config)
            cutoff=safe.audit_pre_anchor_cutoff(tables.history,anchors,config)
        ref=json.loads((HERE/'received/REFERENCE_PANEL_CONTRACT.json').read_bytes())['contract']
        require(len(panel)==972 and panel.WELL_ID.nunique()==81 and len(features)==325,'COHORT_DRIFT')
        require(features==ref['feature_order'] and identity(panel,features,pd)==ref['panel_identity'],'PANEL_IDENTITY_DRIFT')
        splits=list(GroupKFold(5,shuffle=False).split(panel,groups=panel.WELL_ID))
        split_hash=fingerprint([(array_hash(tr),array_hash(va)) for tr,va in splits])
        require(split_hash==json.loads((HERE/'received/SPLIT_REFERENCE.json').read_bytes())['outer_split_sha256'],'SPLIT_IDENTITY_DRIFT')
        coverage=np.zeros(len(panel),int)
        for tr,va in splits:
            require(not set(panel.iloc[tr].WELL_ID)&set(panel.iloc[va].WELL_ID),'WELL_ISOLATION_FAILED');coverage[va]+=1
        require((coverage==1).all(),'OOF_COVERAGE')
        # No test target column is ever parsed, including rows before the target window.
        settings=config['data']['csv'];test_frames=[]
        for rel in config['data']['sources']['test']['history']:
            member=store.declared[rel.replace('\\','/')]
            test_frames.append(pd.read_csv(io.BytesIO(store.zip.read(store.members[member])),encoding=settings.get('encoding','utf-8-sig'),sep=settings.get('delimiter',','),usecols=lambda name:name!='RCYL'))
        test=pd.concat(test_frames,ignore_index=True)
        require('RCYL' not in test.columns,'TEST_LABEL_COLUMN_READ')
        require(not set(test.WELL_ID)&set(panel.WELL_ID),'TRAIN_TEST_WELL_OVERLAP')
        test_anchors,_=safe.segment_end_anchors(test,config)
        require(len(test_anchors)==10,'TEST_ANCHOR_COUNT')
        th=tables.history;well,date=config['anchors']['well_column'],config['anchors']['date_column']
        period=safe._periods(th,date);test_period=safe._periods(test,date)
        all_anchors,_=safe.segment_end_anchors(th,config)
        included=list(anchors[well]);full_set=set(included)
        anchor_map=dict(all_anchors[[well,'anchor_period']].itertuples(index=False,name=None))
        test_anchor_map=dict(test_anchors[[well,'anchor_period']].itertuples(index=False,name=None))
        require(len(anchor_map)==88 and len(full_set)==81,'TRAIN_POPULATION')
        pre_mask=pd.Series([p<anchor_map[w] for w,p in zip(th[well],period)],index=th.index)
        test_pre=pd.Series([p<test_anchor_map[w] for w,p in zip(test[well],test_period)],index=test.index)
        test_future=pd.Series([test_anchor_map[w]<p<=test_anchor_map[w]+12 for w,p in zip(test[well],test_period)],index=test.index)
        require(int(test_future.sum())==120,'TEST_WINDOW_COUNT')
        require(all(test_period[(test[well]==w)&test_future].sort_values().tolist()==[m+h for h in range(1,13)] for w,m in test_anchor_map.items()),'TEST_WINDOW_ALIGNMENT')
        for w,m in anchors[[well,'anchor_period']].itertuples(index=False,name=None):
            rows=panel.loc[panel.WELL_ID==w]
            require(rows.horizon.tolist()==list(range(1,13)),'TARGET_HORIZON_ALIGNMENT')
            expected=[]
            for h in range(1,13):
                values=pd.to_numeric(th.loc[(th[well]==w)&(period==m+h),'RCYL'],errors='coerce')
                require(len(values)==1,'TARGET_MONTH_MISSING_DUPLICATE');expected.append(values.iloc[0])
            require(np.array_equal(rows.RCYL.to_numpy(float),np.asarray(expected,float)),'TARGET_VALUE_ALIGNMENT')
        result['hard_gates'].update(泄漏='通过',错位='通过',井级隔离='通过')
        write_new(root/'STRUCTURE_GATES.json',{'train_complete_wells':81,'train_rows':972,'features':325,'all_train_wells':88,'test_history_tables_parsed_without_RCYL':10,'test_target_columns_parsed':0,'test_window_rows_counted_by_keys_only':120,'well_overlap':0,'fixed_split_sha256':split_hash,'frozen_panel_identity':identity(panel,features,pd),'cutoff_audit':cutoff,'raw_files_verified':100,'raw_files_extracted':0})
        lock={'time':stamp(),'before_first_real_SVD_and_diagnostic_scores':True,'plan_sha256':sha(HERE/'PLAN_STAGE0.json'),'source_receipt_sha256':sha(HERE/'SOURCE_RECEIPT.json'),'sources':{Path(p).name:h for p,h in own.items()},'environment':{'python':platform.python_version(),'build':platform.python_build(),'executable_sha256':sha(sys.executable),'dependencies':dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())),'threads':1},'protected_files':len(protected),'protected_snapshot_sha256':fingerprint(protected),'panel_identity':identity(panel,features,pd),'split_sha256':split_hash,'raw_inputs':store.before,'config_sha256':sha(args.config),'historical_dtype':'UNKNOWN'}
        write_new(root/'IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json',lock);event('identity_structure_and_plan_locked')
        # F0: official dictionary, all history columns, no inferred abbreviations.
        dictionary=json.loads((HERE/'FIELD_DICTIONARY.json').read_bytes());defs={x[0]:x[1:] for x in dictionary['fields']}
        num=lambda f,c:pd.to_numeric(f[c],errors='coerce')
        field_records=[]
        for col in th.columns:
            history=th.loc[pre_mask,col]
            numeric=pd.to_numeric(history,errors='coerce')
            official=defs.get(col,['UNKNOWN: absent from official dictionary','UNKNOWN'])
            rec={'field':col,'official_meaning':official[0],'official_unit':official[1],'official_dictionary_matched':col in defs,'missing_zero_meaning':'UNKNOWN; not specified in official dictionary','historical_rows':len(history),'historical_missing_fraction':float(history.isna().mean()),'historical_numeric_zero_fraction':float((numeric==0).mean()),'pre_M_observed_train_well_fraction':float(th.loc[pre_mask&th[col].notna(),well].nunique()/88),'used_in_current_325':any(f.startswith('history__'+col+'__') for f in features),'M_minus_1_availability':'observed under versioned cutoff; original measurement/publication timestamp UNKNOWN','risk':'P1 semantic/acquisition-time unknown; IDs/dates/event text excluded as model inputs' if col in ('WELL_ID','NY','CSLB','BZ') else 'P2 missing/zero business semantics not supplied; future values excluded'}
            if col=='RCYL':rec['test_window_missing_fraction']=None;rec['test_status']='RCYL never parsed from test history'
            elif col in test:
                rec['test_window_missing_fraction']=float(test.loc[test_future,col].isna().mean());rec['test_pre_M_observed_well_fraction']=float(test.loc[test_pre&test[col].notna(),well].nunique()/10)
            else:rec['test_window_missing_fraction']=None;rec['test_status']='field absent'
            field_records.append(rec)
        legal=th.loc[pre_mask].copy()
        def coverage_combo(mask):
            count=int(legal.loc[mask&legal[well].isin(full_set),well].nunique())
            all_count=int(legal.loc[mask,well].nunique())
            return {'valid_complete_wells':count,'complete_well_denominator':81,'coverage':count/81,'valid_all_train_wells':all_count,'all_train_denominator':88,'all_train_coverage':all_count/88,'M_minus_1_available':True,'passes':count/81>=.8}
        combos=[]
        with np.errstate(all='ignore'):
            for item in plan['F0']['combinations']:
                rec=dict(item)
                if 'status' in rec:rec.update({'coverage':None,'M_minus_1_available':False,'passes':False});combos.append(rec);continue
                fields=rec['fields']
                if not set(fields)<=set(legal.columns):rec.update({'status':'required field absent','coverage':None,'passes':False});combos.append(rec);continue
                ident=rec['id']
                if ident=='F0-C01':
                    l,o=num(legal,'RCYL1'),num(legal,'RCYL');values=(l-o)/l;mask=np.isfinite(l)&np.isfinite(o)&(l>0)&(o>=0)&(o<=l)
                elif ident=='F0-C02':
                    a,b=num(legal,'YY'),num(legal,'TY');values=a-b;mask=np.isfinite(a)&np.isfinite(b)&(a>=0)&(b>=0)
                elif ident=='F0-C03':
                    a,b=num(legal,'PL'),num(legal,'BX');values=a*b/100;mask=np.isfinite(a)&np.isfinite(b)&(a>0)&(b>=0)&(b<=100)
                elif ident=='F0-C04':
                    a,b=num(legal,'SXDL'),num(legal,'XXDL');values=(a-b)/(a+b);mask=np.isfinite(a)&np.isfinite(b)&(a>=0)&(b>=0)&(a+b>0)
                else:
                    a=num(legal,'SCTS');days=period.loc[legal.index].dt.days_in_month;values=a/days;mask=np.isfinite(a)&(a>=0)&(a<=days)
                mask &= np.isfinite(values)
                rec.update(coverage_combo(mask));rec['valid_historical_rows']=int(mask.sum());combos.append(rec)
        result['F0_combo_pass_count']=sum(x['passes'] for x in combos)
        result['F0_injection_assessment']={'official_injection_rate_fields':0,'produced_chemical_fields':['CCJHWND','CCJND','CCBHJND','CCYND'],'produced_not_injected':True,'well_pair_mapping_table_declared':False,'CRM_or_LSTM_implemented':False,'conclusion':'Only produced-fluid chemical fields are documented; no injection-rate or injector-producer mapping input established. Do not relabel them as injection data.'}
        write_new(root/'F0_FIELD_RESULTS.json',{'dictionary_source_sha256':dictionary['dictionary_image_sha256'],'scope':'history columns only; frozen boundary excludes layer and first-plan raw tables','fields':field_records,'combinations':combos,'injection':result['F0_injection_assessment'],'F0_combo_pass_count':result['F0_combo_pass_count']})
        event('F0_completed',F0_combo_pass_count=result['F0_combo_pass_count'])
        # D-beta and D-gamma before any SVD; no score-conditioned rule changes.
        event_col=config['anchors']['event_column'];eligible_values=config['anchors']['eligible_event_values']
        incomplete=set(anchor_map)-full_set;inc=[0,0];history_totals={};histories=[]
        for w,group in th.groupby(well,sort=False):
            numeric=pd.to_numeric(group.RCYL,errors='coerce');months=period.loc[group.index]
            mapping=dict(zip((int(p.ordinal) for p in months),numeric.to_numpy(float)))
            final=anchor_map[w].ordinal
            if w in incomplete:
                for h in (1,2):
                    value=mapping.get(final+h,np.nan)
                    inc[h-1]+=int(np.isfinite(value) and value>=0)
            if w in full_set:
                event_months=[int(p.ordinal) for p in months.loc[group[event_col].isin(eligible_values)]]
                current=historical_event_counts(mapping,event_months,final)
                for key,value in current.items():history_totals[key]=history_totals.get(key,0)+value
            histories.append({m:v for m,v in mapping.items() if m<final})
        result['Dbeta_counts']={'incomplete_wells':len(incomplete),'incomplete_new_m1_labels':inc[0],'incomplete_new_m2_labels':inc[1],'complete_cohort_historical_events':history_totals,'denominator':81,'test_history_counted':False}
        result['Dbeta_increase_m1']=(inc[0]+history_totals['new_m1_labels'])/81
        result['Dbeta_increase_m2']=(inc[1]+history_totals['new_m2_labels'])/81
        gamma=lagged_common_trend(histories);result.update({k:gamma[k] for k in ('Dgamma_share','Dgamma_lag1')});result['Dgamma_details']=gamma
        event('Dbeta_and_Dgamma_completed',Dbeta_increase_m1=result['Dbeta_increase_m1'],Dbeta_increase_m2=result['Dbeta_increase_m2'],Dgamma_share=result['Dgamma_share'],Dgamma_lag1=result['Dgamma_lag1'])
        # F1: exactly one real target-basis fit per train fold; no learned input preprocessing.
        y=panel.RCYL.to_numpy(float).reshape(81,12)
        raw=panel['history__RCYL__last'].to_numpy(float).reshape(81,12)[:,0]
        scale=np.where(np.isfinite(raw)&(raw>0),raw,1.)
        z=np.log1p(y/scale[:,None]);result['F1_shape_counts']=shape_counts(y)
        pred={k:np.full_like(y,np.nan) for k in (1,2,3,4)};svd_records=[]
        for fold,(tr,va) in enumerate(splits,1):
            require(counts['preprocessor_fit_entered']<5,'SVD_BUDGET_EXHAUSTED')
            require(store.unchanged() and all(sha(p)==h for p,h in own.items()),'RUNTIME_INPUT_CHANGED')
            trw=np.unique(tr//12);vaw=np.unique(va//12)
            require(not set(trw)&set(vaw),'SVD_WELL_OVERLAP')
            counts['preprocessor_fit_entered']+=1;event('F1_training_SVD_entered',fold=fold,training_wells=len(trw),validation_wells=len(vaw))
            mean=z[trw].mean(axis=0);allow_svd=True
            try:_,singular,components=np.linalg.svd(z[trw]-mean,full_matrices=False)
            except Exception:counts['preprocessor_fit_failed']+=1;raise
            finally:allow_svd=False
            counts['preprocessor_fit_completed']+=1
            require(np.allclose(components@components.T,np.eye(12),rtol=0,atol=1e-10),'SVD_ORTHONORMALITY')
            for k in (1,2,3,4):pred[k][vaw]=project_oracle(z[vaw],mean,components,scale[vaw],k)
            svd_records.append({'fold':fold,'training_wells':len(trw),'validation_wells':len(vaw),'training_validation_well_intersection':0,'basis_fits':1,'K_reuse':[1,2,3,4],'train_basis_scope':'train-fold target vectors only','validation_action':'oracle projection using validation truth, not model prediction','training_first4_explained_variance_ratios':((singular[:4]**2)/(singular**2).sum()).tolist()})
            event('F1_training_SVD_completed',fold=fold)
        for k in (1,2,3,4):
            summary=official_summary(y,pred[k]);result[f'F1_oracle_K{k}']=summary['official_score']
            check=panel[['WELL_ID','horizon','RCYL']].copy();check['prediction']=pred[k].reshape(-1)
            official=official_twelve_month_score(check,truth_column='RCYL',prediction_column='prediction',epsilon=EPSILON).total
            require(abs(official-summary['official_score'])<1e-10,'OFFICIAL_METRIC_MISMATCH')
            result[f'F1_K{k}_summary']=summary
        result['F1_SVD_records']=svd_records;result['hard_gates']['指标']='通过'
        result['Dalpha_status']='UNKNOWN P1: exact row-level fixed OOF predictions not retained; model fitting is forbidden and no all-data model substitution allowed'
        result['open_unknowns']=[{'id':'A027-OOF-SOURCE','grade':'P1','missing':'Existing exact A2B-013 row-level fixed OOF predictions plus identity; prior runs retained aggregates only. D-alpha not executed.'},{'id':'HIST-DTYPE','grade':'P1','missing':'Historical per-source loaded dtype identity; expressly nonblocking for this phase under R4'},{'id':'F0-ZERO-SEMANTICS','grade':'P2','missing':'Official explanation of field-specific zeros/missing values; no unsupported shut-in interpretation or imputation'},{'id':'F0-ACQUISITION-TIME','grade':'P2','missing':'Original field acquisition/publication timestamps; availability conclusions restricted to versioned M-1 contract'},{'id':'CODEX-027-REVIEW','grade':'P1','missing':'Independent review of this delivery; B does not self-sign Codex decision rows'}]
        result['decisions_B_self_report']=decisions(result)
        result['status']='PARTIAL_COMPLETED_DALPHA_INPUT_MISSING'
        event('available_diagnostics_completed_Dalpha_blocked_no_training',F1_oracle_K1=result['F1_oracle_K1'],F1_oracle_K2=result['F1_oracle_K2'],F1_oracle_K3=result['F1_oracle_K3'],F1_oracle_K4=result['F1_oracle_K4'])
    except Exception as exc:
        result['status']='STOPPED';result['stop_code']=str(exc) if isinstance(exc,GateError) else type(exc).__name__
        event('stopped',stop_code=result['stop_code'])
    finally:
        result['integrity']={'protected_files_checked':len(protected),'protected_files_unchanged':all(Path(p).is_file() and sha(p)==h for p,h in protected.items()),'raw_archive_manifest_unchanged':store.unchanged() if store else None,'private_config_unchanged':sha(args.config)==receipt['private_config_sha256'],'own_sources_unchanged':all(sha(p)==h for p,h in own.items())}
        result['fit_counts']=dict(counts);result['preprocessor_fits']=counts['preprocessor_fit_completed'];result['finished_at']=stamp();result['elapsed_seconds']=time.perf_counter()-start
        write_new(root/'FIT_COUNTS.json',counts);write_new(root/'EVENTS.json',events);write_new(root/'RESULT_A2B027_STAGE0.json',result)
        if store:store.close()
        print(json.dumps({'status':result['status'],'model_fits':counts['model_fit_completed'],'SVD_fits':counts['preprocessor_fit_completed'],'stop_code':result.get('stop_code')},ensure_ascii=True),flush=True)
    return 2 if result['status']=='STOPPED' else 0

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('project-src','archive','manifest','config','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--protected-root',action='append',default=[]);p.add_argument('--authorized',action='store_true')
    sys.exit(main(p.parse_args()))
