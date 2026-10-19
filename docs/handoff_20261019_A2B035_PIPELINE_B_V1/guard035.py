"""R13 immutable boundary, config admission and target representation."""
import contextlib,copy,json,re,socket
from pathlib import Path
from core import *

SCHEMA='A2B035-v1'
def validate_config(c):
    allowed={'schema','variant','purpose','cutoff','target','features','learner','evaluation','fusion','split_fingerprints'}
    require(isinstance(c,dict) and set(c)<=allowed and set(c)>=allowed-{'split_fingerprints'},'UNKNOWN_OR_MISSING_CONFIG_KEY')
    require(c['schema']==SCHEMA and bool(re.fullmatch(r'[A-Za-z0-9_-]{1,80}',c['variant'])),'CONFIG_ID')
    require(c['purpose'] in ('pipeline_benchmark','search','fusion_member'),'CONFIG_PURPOSE')
    require(c['cutoff'] in ('T0_minus_1','M_minus_1'),'CUTOFF_CONFIG_FORBIDDEN')
    require(c['cutoff']!='M_minus_1' or c['purpose'] in ('pipeline_benchmark','fusion_member'),'OLD_CUTOFF_FUSION_ONLY')
    require(c['features'] in ('base325','base325_R','base325_G','base325_R_G'),'FEATURE_CONFIG')
    require(set(c['target'])=={'transform','scale'},'TARGET_CONFIG_KEYS')
    t=c['target'];require(t['transform'] in ('log_ratio','log1p') and t['scale'] in ('last_legal','last3_valid_mean','presegment3_mean','none'),'TARGET_CONFIG')
    require((t['transform']=='log1p')==(t['scale']=='none'),'TARGET_SCALE_COMBINATION')
    e=c['evaluation'];require(set(e)=={'fixed','repeated','inner'},'EVAL_KEYS')
    require(e['fixed']=={'method':'GroupKFold','n_splits':5,'shuffle':False},'FIXED_SPLITS_CHANGED')
    require(e['repeated']=={'method':'GroupKFold','n_splits':5,'shuffle':True,'seeds':[1,2,3,4,5]},'REPEATS_CHANGED')
    require(e['inner']=={'method':'GroupKFold','n_splits':5,'shuffle':True,'seed':20260916},'INNER_SPLITS_CHANGED')
    l=c['learner'];name=l.get('name')
    if name in ('ExtraTrees','MultiOutputExtraTrees'):
        require(set(l)=={'name','n_estimators','min_samples_leaf','max_features','random_state','n_jobs'},'MODEL_KEYS')
        require(type(l['n_estimators']) is int and l['n_estimators'] in (400,800),'TREE_COUNT')
        require(type(l['min_samples_leaf']) is int and l['min_samples_leaf'] in (2,4,6,10),'LEAF_SIZE')
        require(type(l['max_features']) in (int,float) and l['max_features'] in (.3,.5,.75,1.),'MAX_FEATURES')
        require(l['random_state']==20260916 and l['n_jobs']==-1,'SEED_OR_PARALLELISM')
    elif name=='LightGBM':
        require(set(l)=={'name','num_leaves','learning_rate','n_estimators','min_child_samples','random_state','n_jobs'},'LGB_KEYS')
        require(l['num_leaves'] in (7,15,31) and l['learning_rate'] in (.03,.05) and l['n_estimators'] in (400,800) and l['min_child_samples'] in (10,20) and l['random_state']==20260916 and l['n_jobs']==-1,'LGB_SMALL_GRID')
    elif name=='CatBoost':
        require(set(l)=={'name','depth','random_state','thread_count'} and l['depth'] in (4,6) and l['random_state']==20260916 and l['thread_count']==-1,'CAT_CONFIG')
    elif name=='TabPFN_v2':require(l=={'name':'TabPFN_v2','random_state':20260916,'device':'cpu'},'TABPFN_DEFAULT_V2_ONLY')
    elif name=='Ensemble':require(set(l)=={'name'},'ENSEMBLE_KEYS')
    else:raise RuntimeError('UNSUPPORTED_LEARNER')
    if name=='Ensemble':
        f=c['fusion'];require(isinstance(f,dict) and set(f)=={'method','members'} and f['method'] in ('equal','inner_grid_0.1') and 2<=len(f['members'])<=4,'FUSION_CONFIG')
        for member in f['members']:
            validate_config(member);require(member['learner']['name']!='Ensemble','NESTED_ENSEMBLE_FORBIDDEN')
    else:require(c['fusion'] is None,'SINGLE_MODEL_FUSION_NOT_NULL')
    return copy.deepcopy(c)

def verify_source_lock():
    lock=json.loads((HERE/'PIPELINE_LOCK.json').read_bytes())
    for name,h in lock['files'].items():
        p=(HERE/name).resolve();require(p.is_relative_to(HERE.resolve()) and file_sha(p)==h,'IMMUTABLE_PIPELINE_CHANGED')
    return lock

def load_variant(path):return validate_config(json.loads(Path(path).read_bytes()))

def load_locked_policy(path):
    contract=json.loads((HERE/'DATA_CONTRACT.json').read_bytes());require(file_sha(path)==contract['private_policy_sha256'],'PRIVATE_POLICY_CHANGED_OUTSIDE_ALLOWED_KNOBS')
    return load_policy(path)

def require_release(c,allow_benchmark=False):
    if c['purpose']=='pipeline_benchmark' and allow_benchmark:
        ref=json.loads((HERE/'BASELINE_ALLOWLIST.json').read_bytes());check=copy.deepcopy(c);check.pop('split_fingerprints',None)
        require(fingerprint(check) in ref['config_fingerprints'],'BENCHMARK_NAME_NOT_AUTHORIZATION')
        return
    require(c['purpose']=='search' and c['cutoff']=='T0_minus_1','OLD_CUTOFF_ONLY_AS_FUSION_MEMBER')
    p=HERE/'PIPELINE_APPROVAL.json';require(p.exists(),'CODEX_PIPELINE_RELEASE_REQUIRED_BEFORE_SEARCH')
    a=json.loads(p.read_bytes());require(a.get('role')=='Codex' and a.get('can_search') is True and a.get('pipeline_lock_sha256')==file_sha(HERE/'PIPELINE_LOCK.json') and bool(re.fullmatch('[0-9a-f]{40}',a.get('review_commit',''))),'CODEX_RELEASE_IDENTITY')

@contextlib.contextmanager
def offline_only():
    old=socket.socket.connect
    def denied(sock,address):
        if sock.family in (socket.AF_INET,socket.AF_INET6):raise RuntimeError('COMPETITION_DATA_NETWORK_FORBIDDEN')
        return old(sock,address)
    keys={'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','DO_NOT_TRACK':'1','TABPFN_DISABLE_TELEMETRY':'1'};previous={k:os.environ.get(k) for k in keys}
    for k,v in keys.items():os.environ[k]=v
    socket.socket.connect=denied
    try:yield
    finally:
        socket.socket.connect=old
        for k,v in previous.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

def legal_history(history,wid,t0,cutoff,config):
    require(cutoff in ('T0_minus_1','M_minus_1'),'CUTOFF_CONFIG_FORBIDDEN')
    well,date=config['anchors']['well_column'],config['anchors']['date_column'];period=pd.to_datetime(history[date],errors='coerce').dt.to_period('M');require(period.notna().all(),'INVALID_HISTORY_DATE')
    end=t0-1
    if cutoff=='M_minus_1':
        prefix=history.loc[(history[well]==wid)&(period<t0)]
        _,event_end=segment(prefix,config);end=event_end-1
    frame=history.loc[(history[well]==wid)&(period<=end)].copy();p=pd.to_datetime(frame[date]).dt.to_period('M');require(not frame.empty and (p<t0).all() and (p<=end).all(),'LEGAL_HISTORY_ASSERTION')
    require(not p.duplicated().any(),'DUPLICATE_LEGAL_MONTH');return frame,end

def segment(legal,config):
    a=config['anchors'];period=pd.to_datetime(legal[a['date_column']]).dt.to_period('M');events=sorted(period.loc[legal[a['event_column']].isin(a['eligible_event_values'])].tolist());require(bool(events),'NO_LEGAL_EVENT')
    end=events[-1];start=end
    for p in reversed(events[:-1]):
        if p==start-1:start=p
        else:break
    return start,end

def row_value(frame,month,column,config):
    if column not in frame:return np.nan
    p=pd.to_datetime(frame[config['anchors']['date_column']]).dt.to_period('M');v=pd.to_numeric(frame.loc[p==month,column],errors='coerce');require(len(v)<=1,'DUPLICATE_MONTH')
    return float(v.iloc[0]) if len(v) else np.nan

def target_scale(legal,end,c,config,event_segment=None):
    mode=c['target']['scale']
    if mode=='none':return 1.
    if mode=='last_legal':
        # The historical scale is the raw final observed legal RCYL, before filling.
        ordered=legal.assign(__period=pd.to_datetime(legal[config['anchors']['date_column']]).dt.to_period('M')).sort_values('__period',kind='stable');value=float(pd.to_numeric(ordered.RCYL,errors='coerce').iloc[-1])
    elif mode=='last3_valid_mean':
        v=np.asarray([row_value(legal,end-i,'RCYL',config) for i in range(3)],float);valid=v[np.isfinite(v)&(v>=0)];value=float(valid.mean()) if len(valid) else np.nan
    elif mode=='presegment3_mean':
        start,_=event_segment if event_segment is not None else segment(legal,config);v=np.asarray([row_value(legal,start-i,'RCYL',config) for i in (3,2,1)],float);value=float(v.mean()) if np.isfinite(v).all() and (v>=0).all() else np.nan
    else:raise RuntimeError('SCALE_MODE')
    return value if np.isfinite(value) and value>0 else 1.

def response_features(legal,config,event_segment=None):
    start,end=event_segment if event_segment is not None else segment(legal,config)
    def value(m,col):return row_value(legal,m,col,config)
    def avg(col):
        v=np.asarray([value(start-i,col) for i in (3,2,1)],float);return float(v.mean()) if np.isfinite(v).all() else np.nan
    def quality(m):
        liquid,oil=value(m,'RCYL1'),value(m,'RCYL');return (liquid-oil)/liquid if np.isfinite(liquid) and np.isfinite(oil) and liquid>0 and 0<=oil<=liquid else np.nan
    def ratio(a,b):return a/b if np.isfinite(a) and np.isfinite(b) and b!=0 else np.nan
    q=np.asarray([quality(start-i) for i in (3,2,1)],float);qm=float(q.mean()) if np.isfinite(q).all() else np.nan
    return {'R1':ratio(value(end,'RCYL'),value(end-1,'RCYL')),'R2':ratio(value(end,'RCYL'),avg('RCYL')),'R3':quality(end)-qm,'R4':value(end,'CCJHWND')-avg('CCJHWND'),'R5':value(end,'SCTS')/end.days_in_month}

def history_features(history,wid,t0,c,config):
    legal,end=legal_history(history,wid,t0,c['cutoff'],config)
    values=history_values(legal,wid,end+1,config)
    a=config['anchors'];p=pd.to_datetime(history[a['date_column']]).dt.to_period('M');prefix=history.loc[(history[a['well_column']]==wid)&(p<t0)];current_segment=segment(prefix,config)
    if '_G' in c['features']:raise RuntimeError('GEOLOGY_DISABLED_PENDING_ACTUAL_CODEX_Q1_WHITELIST')
    if '_R' in c['features']:
        values.update(response_features(legal,config,current_segment))
    return values,target_scale(legal,end,c,config,current_segment)

def build_variant_train(history,policy,config,c):
    c=validate_config(c);base,audit,anchors=safe._build_train_panel(multi.MultiSourceTables(history,pd.DataFrame(),pd.DataFrame(),None),config);base_features=training.configured_feature_columns(base,config)
    require(base_features==policy['feature_order'] and identity(base,base_features)==policy['baseline_identity'],'HISTORICAL_BASELINE_INPUT_IDENTITY')
    rows=[];checks=0
    for a in anchors.to_dict('records'):
        wid,end=a['WELL_ID'],a['anchor_period'];t0=end+1;v,s=history_features(history,wid,t0,c,config)
        # Keep the legal event metadata while removing all target/future rows;
        # M-1 statistics themselves remain restricted inside legal_history.
        aconf=config['anchors'];months=pd.to_datetime(history[aconf['date_column']]).dt.to_period('M');prefix=history.loc[(history[aconf['well_column']]==wid)&(months<t0)];again,scale2=history_features(prefix,wid,t0,c,config)
        require(v.keys()==again.keys() and all(safe._same_feature_value(v[k],again[k]) for k in v) and s==scale2,'FUTURE_SENSITIVE_INPUT');checks+=len(v)
        for h,y in enumerate(base.loc[base.WELL_ID==wid,'RCYL'],1):rows.append({'WELL_ID':wid,'anchor_time':end.to_timestamp(),'horizon':h,'forecast_step':h,'RCYL':float(y),**v,'__scale035':s})
    panel=pd.DataFrame(rows);features=policy['feature_order']+(['R1','R2','R3','R4','R5'] if '_R' in c['features'] else [])
    require(len(panel)==972 and panel.WELL_ID.nunique()==81 and panel[['WELL_ID','horizon','RCYL']].equals(base[['WELL_ID','horizon','RCYL']]),'COHORT_TARGET_ORDER')
    return panel,features,{'wells':81,'rows':972,'features':len(features),'history_cutoff_assertion':'NY<T0; additional M-1 for legacy B0','future_sensitive_input_count':0,'feature_comparisons':checks,'target_keys_unchanged':True,'identity':identity(panel,features),'historical_dtype':'UNKNOWN'}

def build_variant_test(store,policy,config,c):
    c=validate_config(c);keys,histories,audit=test_keys_and_history(store,config,policy);rows=[]
    for frame,t0 in histories:
        require(frame.WELL_ID.nunique()==1,'TEST_WELL_KEY');wid=frame.WELL_ID.iloc[0];v,s=history_features(frame,wid,t0,c,config);group=[k for k in keys if k[0]==wid];require(len(group)==12,'TEST_TEMPLATE_ROWS')
        for step,(_,ny) in enumerate(group,1):rows.append({'WELL_ID':wid,'NY':ny,'horizon':step,'forecast_step':step,**v,'__scale035':s})
    panel=pd.DataFrame(rows);features=policy['feature_order']+(['R1','R2','R3','R4','R5'] if '_R' in c['features'] else []);require(list(panel[['WELL_ID','NY']].itertuples(index=False,name=None))==keys,'TEMPLATE_OUTPUT_KEY_ORDER')
    return panel,features,audit

def transform_target(panel,c):
    y=panel.RCYL.to_numpy(float);s=panel['__scale035'].to_numpy(float);require(np.isfinite(y).all() and (y>=0).all() and np.isfinite(s).all() and (s>0).all(),'TARGET_SCALE_VALIDITY')
    return np.log1p(y/s)

def inverse_target(z,panel):
    pred=np.clip(np.expm1(np.asarray(z,float))*panel['__scale035'].to_numpy(float),0,None);require(len(pred)==len(panel) and np.isfinite(pred).all(),'PREDICTION_VALIDITY');return pred
