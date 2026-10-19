"""Fixed grouped evaluation and genuinely nested training-side fusion."""
from sklearn.model_selection import GroupKFold
from guard035 import *
from models035 import fit_single,predict_single,choose_weights_on_training_only

def array_hash(a):
    x=np.ascontiguousarray(a,dtype=np.int64);return sha(x.dtype.str.encode()+str(x.shape).encode()+x.tobytes())
def fold_hash(tr,va):return fingerprint([array_hash(tr),array_hash(va)])
def split_sets(panel):
    groups=panel.WELL_ID.to_numpy();sets={'fixed':list(GroupKFold(5,shuffle=False).split(panel,groups=groups))}
    for seed in range(1,6):sets['repeat_'+str(seed)]=list(GroupKFold(5,shuffle=True,random_state=seed).split(panel,groups=groups))
    for name,folds in sets.items():
        coverage=np.zeros(len(panel),int)
        for tr,va in folds:require(not set(groups[tr])&set(groups[va]),'WELL_OVERLAP');coverage[va]+=1
        require((coverage==1).all(),'VALIDATION_COVERAGE')
    return sets
def split_fingerprints(splits):return {name:[fold_hash(tr,va) for tr,va in folds] for name,folds in splits.items()}

class Panels:
    def __init__(self,history,policy,config):self.history=history;self.policy=policy;self.config=config;self.cache={}
    def get(self,c):
        key=fingerprint(c)
        if key not in self.cache:self.cache[key]=build_variant_train(self.history,self.policy,self.config,c)
        return self.cache[key]

def fit_members_full(c,provider,indices,ledger,stage,forbidden_validation_indices=()):
    if c['learner']['name']!='Ensemble':
        p,f,_=provider.get(c);return {'kind':'single','artifact':fit_single(p.iloc[indices],f,c,provider.config,ledger,stage),'config':c}
    members=c['fusion']['members'];first=provider.get(members[0])[0];require(all(first[['WELL_ID','horizon','RCYL']].equals(provider.get(m)[0][['WELL_ID','horizon','RCYL']]) for m in members),'FUSION_MEMBER_TARGET_KEYS')
    weights=[1/len(members)]*len(members);evidence={'source':'equal fixed weights','outer_validation_rows_used':0}
    if c['fusion']['method']=='inner_grid_0.1':
        train=first.iloc[indices];inner=list(GroupKFold(5,shuffle=True,random_state=20260916).split(train,groups=train.WELL_ID));preds=[]
        for j,m in enumerate(members):
            member_pred=np.full(len(indices),np.nan);p,f,_=provider.get(m)
            for k,(itr,iva) in enumerate(inner,1):
                global_train=np.asarray(indices)[itr];global_valid=np.asarray(indices)[iva]
                require(not set(first.iloc[global_train].WELL_ID)&set(first.iloc[global_valid].WELL_ID),'INNER_WELL_OVERLAP');require(not set(global_train)&set(forbidden_validation_indices) and not set(global_valid)&set(forbidden_validation_indices),'INNER_SEES_OUTER_VALIDATION')
                model=fit_single(p.iloc[global_train],f,m,provider.config,ledger,f'{stage}-weight-member{j}-inner{k}');member_pred[iva]=predict_single(model,p.iloc[global_valid],m)
            preds.append(member_pred)
        weights,evidence=choose_weights_on_training_only(train,preds,indices,forbidden_validation_indices)
    fitted=[fit_members_full(m,provider,indices,ledger,f'{stage}-member{j}',forbidden_validation_indices) for j,m in enumerate(members)]
    return {'kind':'ensemble','members':fitted,'weights':weights,'weight_evidence':evidence,'config':c}

def predict_fitted(bundle,panel_provider):
    if bundle['kind']=='single':return predict_single(bundle['artifact'],panel_provider(bundle['config']),bundle['config'])
    pred=[predict_fitted(m,panel_provider) for m in bundle['members']];return np.sum(np.asarray(pred)*np.asarray(bundle['weights'])[:,None],axis=0)

def evaluate_split(c,provider,splits,ledger,stage,folder=None):
    first=c['fusion']['members'][0] if c['learner']['name']=='Ensemble' else c
    panel=provider.get(first)[0];coverage=np.zeros(len(panel),int);oof=np.full(len(panel),np.nan);folds=[]
    for fold,(tr,va) in enumerate(splits,1):
        require(not set(panel.iloc[tr].WELL_ID)&set(panel.iloc[va].WELL_ID),'OUTER_WELL_OVERLAP')
        bundle=fit_members_full(c,provider,tr,ledger,f'{stage}-fold{fold}',forbidden_validation_indices=va)
        pred=predict_fitted(bundle,lambda m:provider.get(m)[0].iloc[va]);oof[va]=pred;coverage[va]+=1;value=summary(panel.iloc[va],pred)
        row={'fold':fold,'score':value['official_score'],'weighted_losses':value['weighted_losses'],'train_wells':int(panel.iloc[tr].WELL_ID.nunique()),'validation_wells':int(panel.iloc[va].WELL_ID.nunique()),'well_overlap':0,'row_split_sha256':fold_hash(tr,va),'inner_fusion_weight_evidence':bundle.get('weight_evidence')};folds.append(row)
        if folder:
            p=Path(folder);p.mkdir(parents=True,exist_ok=True);(p/f'{stage}-fold{fold}.json').write_bytes(encode(row))
    require((coverage==1).all() and np.isfinite(oof).all(),'OOF_COVERAGE_OR_FINITE')
    value=summary(panel,oof);score=value['official_score'];scores=[f['score'] for f in folds]
    result={'score':score,'fold_scores':scores,'worst_fold':min(scores),'fold_std_population':float(np.std(scores)),'weighted_losses':value['weighted_losses'],'official_formula_difference':value['official_cross_check_difference'],'folds':folds,'validation_coverage_each_row_once':True,'models_and_preprocessors_fitted_only_on_training_rows':True}
    if folder:(Path(folder)/(stage+'-SUMMARY.json')).write_bytes(encode(result))
    return result,oof

def repeated_summary(values):
    scores=np.asarray([v['score'] for v in values],float);require(len(scores)==5,'REPEAT_COUNT')
    return {'repeat_scores':scores.tolist(),'mean':float(scores.mean()),'sample_std':float(scores.std(ddof=1)),'standard_error':float(scores.std(ddof=1)/np.sqrt(5)),'weighted_loss_means':{k:float(np.mean([v['weighted_losses'][k] for v in values])) for k in ('m1_to_1','m1_to_2','m1_to_4','m1_to_12')},'SE_interpretation':'split variability from the same81 wells; not independent data replicates or significance evidence'}
