"""R10 single-factor cutoff implementation, using original frozen methods."""
import copy,hashlib,io,json,os,sys,zipfile,csv
from pathlib import Path,PurePosixPath
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def require(x,code):
    if not x:raise RuntimeError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(obj):return (json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def file_sha(path):return sha(Path(path).read_bytes())
def fingerprint(x):return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def ensure_sources():
    bundle=json.loads((HERE/'FROZEN_SOURCES.json').read_bytes())
    for row in bundle['files']:
        p=(HERE/row['path']).resolve();require(p.is_relative_to(HERE.resolve()),'UNSAFE_SOURCE_PATH');raw=row['text'].encode('utf-8');require(sha(raw)==row['sha256'],'SOURCE_BUNDLE_CORRUPT')
        if p.exists():require(p.read_bytes()==raw,'FROZEN_SOURCE_MODIFIED')
        else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    sys.path.insert(0,str(HERE/'src'))
ensure_sources()
import numpy as np,pandas as pd,joblib
from oil_uplift import a2b013_safe as safe,multistep as multi,training
from oil_uplift.scoring import official_twelve_month_score
from csv_projection import key_projection,header_and_rows,cell
for mod in (safe,multi,training):require(Path(mod.__file__).resolve().is_relative_to((HERE/'src').resolve()),'IMPORT_ROOT')

class Inputs:
    def __init__(self,path):
        self.path=Path(path).resolve();self.z=None;self.files={};self.read_bytes=0;self.test_window_dynamic_decoded=0
        if self.path.is_file():
            self.z=zipfile.ZipFile(self.path,'r')
            for info in self.z.infolist():
                if info.is_dir():continue
                name=info.filename
                if not info.flag_bits&0x800:
                    try:name=name.encode('cp437').decode('gb18030')
                    except UnicodeError:pass
                name=name.replace('\\','/');require('..' not in PurePosixPath(name).parts and not PurePosixPath(name).is_absolute() and ':' not in name,'UNSAFE_DATA_MEMBER');require(name not in self.files,'DUPLICATE_MEMBER');self.files[name]=info
        else:
            require(self.path.is_dir(),'DATA_PATH_MISSING')
            self.files={p.relative_to(self.path).as_posix():p for p in self.path.rglob('*.csv') if p.is_file()}
    def raw(self,rel):
        rel=rel.replace('\\','/');matches=[n for n in self.files if n==rel or n.endswith('/'+rel)];require(len(matches)==1,'DATA_ROLE_NOT_UNIQUE')
        value=self.z.read(self.files[matches[0]]) if self.z else self.files[matches[0]].read_bytes();self.read_bytes+=len(value);return value
    def close(self):
        if self.z:self.z.close()

def load_policy(path):
    value=json.loads(Path(path).read_bytes());config=safe.safe_config(value['config']);require(len(value['feature_order'])==325,'POLICY_FEATURES');return value,config
def load_train(store,config):
    settings=config['data']['csv'];frames=[pd.read_csv(io.BytesIO(store.raw(n)),encoding=settings.get('encoding','utf-8-sig'),sep=settings.get('delimiter',',')) for n in config['data']['sources']['train']['history']]
    require(len(frames)==88 and all(list(x.columns)==list(frames[0].columns) for x in frames),'TRAIN_SCHEMA');return pd.concat(frames,ignore_index=True)
def history_values(history,wid,t0,config):
    w,d=config['anchors']['well_column'],config['anchors']['date_column'];months=pd.to_datetime(history[d],errors='coerce').dt.to_period('M');require(months.notna().all(),'INVALID_HISTORY_KEY')
    legal=history.loc[(history[w]==wid)&(months<t0)].copy();require(not legal.empty and (pd.to_datetime(legal[d]).dt.to_period('M')<t0).all(),'CUTOFF_FILTER_FAILED')
    values=multi._history_features(legal,wid,(t0-1).to_timestamp(),config)
    return {'history_month_count':values['history_month_count'],**{k:v for k,v in values.items() if k.startswith('history__')}}
def identity(panel,features):
    return {'feature_order_sha256':fingerprint(features),'feature_dtype_sha256':fingerprint(list(zip(features,panel[features].dtypes.astype(str)))),'feature_frame_sha256':sha(pd.util.hash_pandas_object(panel[features],index=True).values.tobytes()),'label_key_frame_sha256':sha(pd.util.hash_pandas_object(panel[['WELL_ID','horizon','RCYL']],index=True).values.tobytes())}
def build_train(history,config,policy,audit=True):
    tables=multi.MultiSourceTables(history,pd.DataFrame(),pd.DataFrame(),None);baseline,ba,anchors=safe._build_train_panel(tables,config);features=training.configured_feature_columns(baseline,config)
    require(identity(baseline,features)==policy['baseline_identity'] and features==policy['feature_order'],'BASELINE_INPUT_IDENTITY')
    rows=[];checks=0;raw_scale_checks=0
    for anchor in anchors.to_dict('records'):
        wid,end=anchor['WELL_ID'],anchor['anchor_period'];t0=end+1;values=history_values(history,wid,t0,config)
        for step,target in enumerate(baseline.loc[baseline.WELL_ID==wid,'RCYL'],1):rows.append({'WELL_ID':wid,'anchor_time':end.to_timestamp(),'horizon':step,'forecast_step':step,'RCYL':float(target),**values})
        if audit:
            months=pd.to_datetime(history[config['anchors']['date_column']]).dt.to_period('M');trimmed=history.loc[(history.WELL_ID==wid)&(months<t0)]
            again=history_values(trimmed,wid,t0,config);require(values.keys()==again.keys() and all(safe._same_feature_value(values[k],again[k]) for k in values),'FUTURE_SENSITIVE_FEATURE');checks+=len(values)
            ordered=trimmed.assign(__month=pd.to_datetime(trimmed[config['anchors']['date_column']]).dt.to_period('M')).sort_values('__month',kind='stable');raw=pd.to_numeric(ordered.RCYL,errors='coerce').iloc[-1];require(safe._same_feature_value(raw,values['history__RCYL__last']),'RAW_SCALE_CUTOFF');raw_scale_checks+=1
    panel=pd.DataFrame(rows);candidate_features=training.configured_feature_columns(panel,config)
    require(candidate_features==features==policy['feature_order'] and len(features)==325,'FEATURE_325_SAME_ORDER');require(len(panel)==972 and panel.WELL_ID.nunique()==81,'COHORT_SHAPE');require(panel[['WELL_ID','horizon','RCYL']].equals(baseline[['WELL_ID','horizon','RCYL']]),'TARGET_ROW_ORDER_CHANGED')
    ident=identity(panel,features)
    if 'candidate_identity' in policy:require(ident==policy['candidate_identity'],'CANDIDATE_INPUT_IDENTITY')
    return panel,features,anchors,{'cohort':ba,'candidate_identity':ident,'baseline_identity':identity(baseline,features),'cutoff_feature_checks':checks,'raw_last_RCYL_checks':raw_scale_checks,'future_sensitive_feature_count':0,'features_same_name_and_order':True,'labels_keys_rows_unchanged':True,'cutoff':'T0-1 = M','lag_rolling_trend_definition_changed':False}

def test_keys_and_history(store,config,policy):
    settings=config['data']['csv'];encoding=settings.get('encoding','utf-8-sig');delimiter=settings.get('delimiter',',');roles=config['data']['sources']['test'];require(roles['history']==roles['template'] and len(roles['history'])==10,'TEST_ROLE_MAPPING');allkeys=[];origins=[]
    for filename in roles['template']:
        keys,_=key_projection(store.raw(filename),'WELL_ID','NY',encoding,delimiter);require(len(keys)>=12 and len(set(keys))==len(keys) and len({k[0] for k in keys})==1,'TEMPLATE_KEYS');periods=[pd.Timestamp(k[1]).to_period('M') for k in keys];require(len(set(periods))==len(periods),'DUPLICATE_TEST_MONTH');last=sorted(periods)[-12:];require(last==[last[0]+i for i in range(12)],'TEMPLATE_MONTHS');selected=[k for k,p in zip(keys,periods) if p in set(last)];allkeys+=selected;origins.append((filename,last[0]))
    require(fingerprint(allkeys)==policy['template_key_sha256'],'TEMPLATE_IDENTITY_BEFORE_DYNAMIC_ACCESS')
    histories=[];skipped=0
    for filename,t0 in origins:
        raw=store.raw(filename);header,rows=header_and_rows(raw,delimiter);di=header.index('NY');kept=[]
        # Reconstruct a memory-only CSV made exclusively of permitted prefix
        # records. No window dynamic cell is decoded or passed to pandas.
        header_bytes=next(iter(__import__('csv_projection').csv_spans(raw,delimiter.encode()[0])))
        head=raw[header_bytes[0][0]:header_bytes[-1][1]]
        for spans in rows:
            require(len(spans)==len(header),'TEST_CSV_WIDTH');month=pd.Timestamp(cell(raw,spans[di],encoding)).to_period('M')
            if month>=t0:skipped+=1;continue
            kept.append(raw[spans[0][0]:spans[-1][1]])
        require(bool(kept),'EMPTY_LEGAL_TEST_HISTORY');frame=pd.read_csv(io.BytesIO(head+b'\n'+b'\n'.join(kept)+b'\n'),encoding=encoding,sep=delimiter);require((pd.to_datetime(frame.NY).dt.to_period('M')<t0).all(),'TEST_WINDOW_ENTERED_PANDAS');histories.append((frame,t0))
    require(skipped==120 and len(allkeys)==120 and len({k[0] for k in allkeys})==10,'TEST_COVERAGE')
    return allkeys,histories,{'template_rows':120,'test_wells':10,'template_key_sha256':fingerprint(allkeys),'test_window_rows_skipped':skipped,'test_window_dynamic_values_decoded':0,'test_window_RCYL_parsed':0,'template_key_hash_verified_before_dynamic_access':True}
def build_test(store,config,policy):
    keys,histories,audit=test_keys_and_history(store,config,policy);rows=[]
    for frame,t0 in histories:
        ids=set(frame.WELL_ID);require(len(ids)==1,'TEST_WELL');wid=next(iter(ids));values=history_values(frame,wid,t0,config);group=[k for k in keys if k[0]==wid];require(len(group)==12,'TEST_TEMPLATE_GROUP')
        for step,(_,ny) in enumerate(group,1):rows.append({'WELL_ID':wid,'NY':ny,'horizon':step,'forecast_step':step,**values})
    panel=pd.DataFrame(rows);require(list(panel[['WELL_ID','NY']].itertuples(index=False,name=None))==keys,'TEMPLATE_ORDER');require(set(policy['feature_order'])<=set(panel),'TEST_FEATURE_SCHEMA')
    return panel,audit
def predict(pipe,frame,features,config):
    # Deterministic summation; training still uses locked n_jobs=-1.
    with joblib.parallel_backend('sequential'):pred=training.predict_pipeline_output(pipe,safe.MODEL_NAME,frame[features],frame)
    pred=np.clip(np.asarray(pred,float),0,None);require(len(pred)==len(frame) and np.isfinite(pred).all(),'PREDICTION_INVALID');return pred
def summary(panel,prediction):
    scored=panel[['WELL_ID','horizon','RCYL']].copy();scored['prediction']=prediction;official=official_twelve_month_score(scored,truth_column='RCYL',prediction_column='prediction',epsilon=1e-6).total
    y=panel.RCYL.to_numpy(float).reshape(-1,12);p=np.asarray(prediction,float).reshape(-1,12);weighted=np.abs(y-p)/(np.abs(y)+np.abs(p)+1e-6)*np.power(.5,np.arange(1,13));own=float((100*(1-weighted.sum(1))).mean());require(abs(official-own)<1e-12,'METRIC_MISMATCH')
    return {'official_score':official,'weighted_losses':{f'm1_to_{n}':float(weighted[:,:n].sum(1).mean()) for n in (1,2,4,12)},'wells':len(y),'official_cross_check_difference':official-own}
def write_result(path,panel,pred):
    path=Path(path);require(not path.exists(),'OUTPUT_ALREADY_EXISTS');path.parent.mkdir(parents=True,exist_ok=True);require(len(panel)==120 and len(pred)==120,'OUTPUT_SHAPE')
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for wid,group in panel.assign(__prediction=pred).groupby('WELL_ID',sort=False):
            require(str(wid).replace('_','').isalnum(),'UNSAFE_WELL_FILENAME');out=io.StringIO(newline='');writer=csv.writer(out,lineterminator='\n');writer.writerow(['WELL_ID','NY','RCYL'])
            for w,ny,p in group[['WELL_ID','NY','__prediction']].itertuples(index=False,name=None):writer.writerow([w,ny,format(float(p),'.17g')])
            info=zipfile.ZipInfo(str(wid)+'.csv',date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,out.getvalue().encode('utf-8'))
    return lint_result(path,panel)
def lint_result(path,panel):
    keys=list(panel[['WELL_ID','NY']].itertuples(index=False,name=None));bywell={w:[k for k in keys if k[0]==w] for w in panel.WELL_ID.drop_duplicates()};rows=[];csv_records=[]
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None and len(z.infolist())==10,'ZIP_CRC_OR_COUNT');require({x.filename for x in z.infolist()}=={str(w)+'.csv' for w in bywell},'ZIP_FILENAME_SET')
        for info in z.infolist():
            require('/' not in info.filename and '\\' not in info.filename and not info.is_dir(),'ZIP_NOT_FLAT');raw=z.read(info);parsed=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))));require(parsed[0]==['WELL_ID','NY','RCYL'] and len(parsed)==13,'CSV_SCHEMA_ROWS');wid=info.filename[:-4];require([(r[0],r[1]) for r in parsed[1:]]==bywell[wid],'CSV_TEMPLATE_KEYS_ORDER');values=[float(r[2]) for r in parsed[1:]];require(np.isfinite(values).all() and min(values)>=0,'CSV_VALUES');rows+=parsed[1:];csv_records.append({'sha256':sha(raw),'bytes':len(raw),'rows':12})
    require(len(rows)==120 and len({(r[0],r[1]) for r in rows})==120,'DUPLICATE_OUTPUT_KEYS');return {'status':'PASS','files':10,'rows':120,'columns':['WELL_ID','NY','RCYL'],'exact_template_keys_dates_order':True,'duplicate_keys':0,'extra_columns':0,'NaN_Inf_negative':0,'flat_ZIP':True,'CRC_passed':True,'result_zip_sha256':file_sha(path),'result_zip_bytes':Path(path).stat().st_size,'CSV_hashes_anonymous_archive_order':csv_records}
