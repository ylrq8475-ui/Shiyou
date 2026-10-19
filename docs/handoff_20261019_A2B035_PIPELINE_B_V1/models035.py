"""Model switches behind common features/scale/boundary, never test fitting."""
import contextlib,json
from pathlib import Path
from guard035 import *

def resource_gate(name):
    p=HERE/'RESOURCE_RELEASES.json';require(p.exists(),'EXTERNAL_MODEL_EVIDENCE_REQUIRED');r=json.loads(p.read_bytes()).get(name,{});require(r.get('enabled') is True and r.get('license_checked') is True,'EXTERNAL_MODEL_NOT_RELEASED')
    if name=='TabPFN_v2':
        require(r.get('model_version')=='v2' and r.get('sample_independence_passed') is True and r.get('offline_synthetic_evidence_sha256') and r.get('weights'),'TABPFN_V2_IDENTITY_AND_INDEPENDENCE_REQUIRED')
        for item in r['weights']:require(file_sha(item['path'])==item['sha256'],'EXTERNAL_WEIGHT_SHA')
    return r

def estimator_for(c,x,legacy_config):
    p=c['learner'];name=p['name']
    if name in ('ExtraTrees','MultiOutputExtraTrees'):
        model=training._model_pipeline(safe.MODEL_NAME,x,legacy_config).named_steps['model'];model.set_params(**{k:v for k,v in p.items() if k!='name'});return model
    if name=='LightGBM':
        resource_gate(name)
        from lightgbm import LGBMRegressor
        return LGBMRegressor(**{k:v for k,v in p.items() if k!='name'},verbosity=-1)
    if name=='CatBoost':
        resource_gate(name)
        from catboost import CatBoostRegressor
        return CatBoostRegressor(depth=p['depth'],random_seed=p['random_state'],thread_count=p['thread_count'],verbose=False,allow_writing_files=False)
    if name=='TabPFN_v2':
        r=resource_gate(name)
        from tabpfn import TabPFNRegressor
        from tabpfn.constants import ModelVersion
        return TabPFNRegressor.create_default_for_version(ModelVersion.V2,device='cpu',random_state=p['random_state'],model_path=r['weights'][0]['path'])
    raise RuntimeError('LEARNER_NOT_SINGLE_TRAINABLE')

def fit_single(panel,features,c,legacy_config,ledger,stage):
    c=validate_config(c);multiout=c['learner']['name']=='MultiOutputExtraTrees'
    if multiout:
        require((panel.groupby('WELL_ID',sort=False).size()==12).all(),'MULTIOUTPUT_GROUP_SIZE');starts=np.arange(0,len(panel),12);x=panel[features].iloc[starts];y=transform_target(panel,c).reshape(-1,12)
    else:x=panel[features];y=transform_target(panel,c)
    model=estimator_for(c,x,legacy_config);prep=training._preprocessor(x);xx=ledger.run('preprocessor',stage,lambda:prep.fit_transform(x,y));ledger.run('model',stage,lambda:model.fit(xx,y))
    return {'config_fingerprint':fingerprint(c),'features':features,'preprocessor':prep,'model':model,'learner':c['learner']['name'],'multioutput':multiout}

def predict_single(artifact,panel,c,independent_query=True):
    require(artifact['config_fingerprint']==fingerprint(c),'MODEL_CONFIG_IDENTITY');features=artifact['features'];prep,model=artifact['preprocessor'],artifact['model'];single=artifact['learner']=='TabPFN_v2'
    with joblib.parallel_backend('sequential'):
        # Standard sklearn transforms are training-fitted and rowwise. Test
        # execution calls this on one well at a time; TabPFN always one row.
        if single:
            z=np.asarray([float(np.asarray(model.predict(prep.transform(panel[features].iloc[[i]]))).reshape(-1)[0]) for i in range(len(panel))])
        elif artifact['multioutput']:
            require((panel.groupby('WELL_ID',sort=False).size()==12).all(),'MULTIOUTPUT_PREDICT_GROUP');x=panel[features].iloc[np.arange(0,len(panel),12)];z=np.asarray(model.predict(prep.transform(x))).reshape(-1)
        else:z=np.asarray(model.predict(prep.transform(panel[features])))
    return inverse_target(z,panel)

def simplex_weights(members,units=10):
    if members==1:return [(1.,)]
    def all_units(n,total):
        if n==1:yield (total,);return
        for i in range(total+1):
            for tail in all_units(n-1,total-i):yield (i,)+tail
    return [tuple(x/units for x in a) for a in all_units(members,units)]

def choose_weights_on_training_only(train_panel,member_predictions,training_indices,forbidden_validation_indices):
    require(not set(training_indices)&set(forbidden_validation_indices),'OUTER_VALIDATION_ENTERED_WEIGHT_SELECTION')
    require(len(member_predictions)>=2 and all(len(x)==len(train_panel) and np.isfinite(x).all() for x in member_predictions),'INNER_OOF_SHAPE')
    best=None;best_score=-np.inf
    for weights in simplex_weights(len(member_predictions)):
        p=np.sum(np.asarray(member_predictions)*np.asarray(weights)[:,None],axis=0);score=summary(train_panel,p)['official_score']
        if score>best_score:best_score=score;best=weights
    return list(best),{'source':'outer-training wells inner GroupKFold OOF only','outer_validation_rows_used':0,'weight_grid_step':0.1,'inner_training_score':best_score}

@contextlib.contextmanager
def forbid_fits(extra_classes=()):
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import ExtraTreesRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler,OneHotEncoder
    patched=[]
    def denied(*a,**k):raise RuntimeError('INFERENCE_FIT_FORBIDDEN')
    for cls in dict.fromkeys((Pipeline,ColumnTransformer,ExtraTreesRegressor,SimpleImputer,StandardScaler,OneHotEncoder,*extra_classes)):
        for name in ('fit','fit_transform'):
            if hasattr(cls,name):patched.append((cls,name,getattr(cls,name)));setattr(cls,name,denied)
    try:yield
    finally:
        for cls,name,old in reversed(patched):setattr(cls,name,old)
