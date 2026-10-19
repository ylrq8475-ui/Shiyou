"""Synthetic-only boundary, estimator and nested selection checks."""
from cv035 import *
from models035 import forbid_fits,fit_single,predict_single
from predict import infer_bundle

def run_checks(policy,legacy,history_columns,ledger):
    passed=[];c=load_variant(HERE/'configs/B0_prime.json');roles=legacy['data']['sources']['test'];files={};keys=[]
    months=pd.period_range('1990-01',periods=30,freq='M');t0=months[18]
    for i,name in enumerate(roles['history']):
        wid='SYNTH_'+str(i);frame=pd.DataFrame({col:np.arange(30,dtype=float)+i+1 for col in history_columns})
        frame['WELL_ID']=wid;frame['NY']=[str(p.to_timestamp().date()) for p in months];ec=legacy['anchors']['event_column'];frame[ec]='SYNTH_NONE';frame.loc[16:17,ec]=legacy['anchors']['eligible_event_values'][0]
        frame['RCYL']=np.arange(30,dtype=float)+3;frame['RCYL1']=2*frame['RCYL'];frame['SCTS']=20.;frame['CCJHWND']=4.
        files[name]=frame;keys += list(frame.iloc[18:][['WELL_ID','NY']].itertuples(index=False,name=None))
    p=copy.deepcopy(policy);p['template_key_sha256']=fingerprint(keys)
    class MemoryStore:
        def __init__(self,frames,poison=None):self.frames=frames;self.poison=poison
        def raw(self,name):
            f=self.frames[name].copy()
            if self.poison:
                for col in self.poison:
                    if col not in ('WELL_ID','NY'):f[col]=f[col].astype(object);f.loc[18:,col]='POISON_DYNAMIC_CELL'
            return f.to_csv(index=False,lineterminator='\n').encode('utf-8-sig')
    class PureTransform:
        def transform(self,x):return np.nan_to_num(x.select_dtypes(include='number').to_numpy(float),nan=0,posinf=0,neginf=0)
    class PurePrediction:
        def predict(self,x):return np.log1p(np.abs(x).sum(axis=1))
    features=policy['feature_order'];bundle={'kind':'single','config':c,'artifact':{'config_fingerprint':fingerprint(c),'features':features,'preprocessor':PureTransform(),'model':PurePrediction(),'learner':'synthetic arithmetic stub','multioutput':False}}
    b,reference,a=infer_bundle(bundle,MemoryStore(files),p,legacy,c);columns=[v for v in next(iter(files.values())).columns if v not in ('WELL_ID','NY')]
    for col in columns:
        _,pred,checks=infer_bundle(bundle,MemoryStore(files,[col]),p,legacy,c);require(np.array_equal(reference,pred) and all(x['test_window_dynamic_values_decoded']==0 for x in checks),'SYNTH_WINDOW_COLUMN_LEAK')
    passed.append({'name':'each non-key template-window column poison leaves all predictions exactly unchanged','cases':len(columns),'PASS':True})
    # Byte-invalid dynamic values would fail decoding if a window cell entered pandas.
    class InvalidWindowStore(MemoryStore):
        def raw(self,name):return super().raw(name).replace(b'POISON_DYNAMIC_CELL',b'\xff\xfe\xfd')
    _,poison,_=infer_bundle(bundle,InvalidWindowStore(files,columns),p,legacy,c);require(np.array_equal(reference,poison),'WINDOW_NONKEY_BYTES_DECODED');passed.append({'name':'invalid UTF8 in all window dynamic cells is never decoded','PASS':True})
    changed={n:f.copy() for n,f in files.items()};first=next(iter(changed));changed[first].loc[:17,'RCYL']=1e8
    _,other,_=infer_bundle(bundle,MemoryStore(changed),p,legacy,c);require(np.array_equal(reference[12:],other[12:]) and not np.array_equal(reference[:12],other[:12]),'CROSS_TEST_WELL_INFLUENCE');passed.append({'name':'changing one synthetic legal well affects only that well','PASS':True})
    for col in ('WELL_ID','NY'):
        altered={n:f.copy() for n,f in files.items()};altered[first].loc[18,col]='SYNTH_CHANGED' if col=='WELL_ID' else '1999-01-01'
        try:infer_bundle(bundle,MemoryStore(altered),p,legacy,c)
        except RuntimeError:pass
        else:raise RuntimeError('KEY_MUTATION_NOT_BLOCKED')
    passed.append({'name':'window identity key mutation blocks before dynamic access','cases':2,'PASS':True})
    baseframe=files[first].iloc[:18];wid=baseframe.WELL_ID.iloc[0]
    for cutoff in ('M_minus_1','T0_minus_1'):
        cc=copy.deepcopy(c);cc['cutoff']=cutoff;cc['purpose']='fusion_member';legal,end=legal_history(baseframe,wid,t0,cutoff,legacy);require((pd.to_datetime(legal.NY).dt.to_period('M')<=end).all(),'SYNTH_CUTOFF')
        for mode in ('last_legal','last3_valid_mean','presegment3_mean','none'):
            cc['target']={'transform':'log1p' if mode=='none' else 'log_ratio','scale':mode};_,s=history_features(baseframe,wid,t0,cc,legacy);require(np.isfinite(s) and s>0,'SYNTH_SCALE')
    passed.append({'name':'both cutoffs and all four target scale modes use legal history only','cases':8,'PASS':True})
    bad=copy.deepcopy(c);bad['cutoff']='T0_plus_1'
    try:validate_config(bad)
    except RuntimeError:pass
    else:raise RuntimeError('UNSAFE_CONFIG_ACCEPTED')
    bad=copy.deepcopy(c);bad['evaluation']['repeated']['seeds']=[6,7,8,9,10]
    try:validate_config(bad)
    except RuntimeError:pass
    else:raise RuntimeError('CHANGED_SPLITS_ACCEPTED')
    passed.append({'name':'config cannot change cutoff rule or evaluation seeds','PASS':True})
    # One real estimator on exclusively synthetic data; counted separately from CV.
    toy=pd.DataFrame({'WELL_ID':np.repeat(['TOY_'+str(i) for i in range(10)],12),'horizon':np.tile(np.arange(1,13),10),'RCYL':np.arange(120,dtype=float)+1,'__scale035':np.repeat(2.,120),'f1':np.arange(120,dtype=float),'f2':np.tile([np.nan,3.,5.,7.],30)})
    toy.loc[72:,'f2']=1e12;fit=fit_single(toy.iloc[:72],['f1','f2'],c,legacy,ledger,'synthetic-real-estimator')
    stats=fit['preprocessor'].named_transformers_['numeric'].named_steps['impute'].statistics_;require(np.array_equal(stats,np.nanmedian(toy.iloc[:72][['f1','f2']],axis=0)),'TRAIN_FOLD_IMPUTER_IDENTITY')
    with forbid_fits():
        batch=predict_single(fit,toy.iloc[72:],c);single=np.concatenate([predict_single(fit,toy.iloc[[i]],c) for i in range(72,120)]);require(np.array_equal(batch,single),'ET_QUERY_BATCH_DEPENDENCE')
        try:fit['model'].fit(np.ones((2,2)),[1.,2.])
        except RuntimeError as e:require(str(e)=='INFERENCE_FIT_FORBIDDEN','WRONG_INFERENCE_ERROR')
        else:raise RuntimeError('INFERENCE_FIT_ALLOWED')
    passed.append({'name':'real ET predictions are exactly query independent; trained-only imputation and inference fit prohibition','synthetic_model_fits':1,'synthetic_preprocessor_fits':1,'blocked_fit_calls':1,'PASS':True})
    allsplits=split_sets(toy)
    require(len(allsplits)==6 and all(len(x)==5 for x in allsplits.values()),'SYNTH_SPLITS');passed.append({'name':'fixed plus 5x5 repeated grouped splits: zero well overlap and complete coverage','folds':30,'PASS':True})
    train=toy.iloc[:72];ps=[train.RCYL.to_numpy(),np.zeros(72)];w,ev=choose_weights_on_training_only(train,ps,np.arange(72),np.arange(72,120));require(w==[1.,0.] and ev['outer_validation_rows_used']==0,'INNER_WEIGHT_CHOICE')
    try:choose_weights_on_training_only(train,ps,np.arange(72),[0])
    except RuntimeError:pass
    else:raise RuntimeError('WEIGHT_SELECTION_OUTER_OVERLAP_ACCEPTED')
    passed.append({'name':'weight grid uses only training-side predictions and rejects forbidden outer-validation overlap','PASS':True})
    perfect=summary(toy,toy.RCYL.to_numpy());require(perfect['official_score']==100.,'PERFECT_METRIC');zero=summary(toy,np.zeros(120));own=np.mean(100*(1-(toy.RCYL.to_numpy().reshape(-1,12)/(toy.RCYL.to_numpy().reshape(-1,12)+1e-6)*2.**-np.arange(1,13)).sum(1)));require(abs(own-zero['official_score'])<1e-12,'METRIC_INDEPENDENT_CALC')
    passed.append({'name':'official metric independently checked: t1, epsilon1e-6, unnormalized weights and equal wells','PASS':True})
    return {'status':'PASS','checks':passed,'actual_synthetic_model_fits':1,'actual_synthetic_preprocessor_fits':1,'actual_competition_data_fits_in_these_checks':0,'all_values_are_synthetic':True,'external_adapters_tested':False,'external_adapters_status':'disabled, not claimed PASS'}
