"""Per-well inference; test dynamic window cells are never decoded."""
import argparse
from cv035 import *
from models035 import forbid_fits

def model_types(bundle):
    if bundle['kind']=='single':return [type(bundle['artifact']['model'])]
    return [t for m in bundle['members'] for t in model_types(m)]

def infer_bundle(bundle,store,policy,legacy,c):
    require(fingerprint(bundle['config'])==fingerprint(c),'INFERENCE_CONFIG_CHANGED');cache={}
    def get(m):
        key=fingerprint(m)
        if key not in cache:cache[key]=build_variant_test(store,policy,legacy,m)
        return cache[key][0]
    first=c['fusion']['members'][0] if c['learner']['name']=='Ensemble' else c
    base=get(first);result=np.full(len(base),np.nan)
    # No fit, sample-dependent normalization or joint query adaptation.
    with forbid_fits(model_types(bundle)):
        for wid in base.WELL_ID.drop_duplicates():
            indices=np.flatnonzero((base.WELL_ID==wid).to_numpy())
            def one_well(m):
                panel=get(m);require(panel[['WELL_ID','NY']].equals(base[['WELL_ID','NY']]),'FUSION_TEST_KEYS');return panel.iloc[indices]
            result[indices]=predict_fitted(bundle,one_well)
    require(np.isfinite(result).all(),'INFERENCE_COMPLETE');return base,result,[v[2] for v in cache.values()]

def main():
    a=argparse.ArgumentParser();a.add_argument('--config',required=True);a.add_argument('--data_dir',required=True);a.add_argument('--policy',required=True);a.add_argument('--model',required=True);a.add_argument('--output',required=True);v=a.parse_args()
    verify_source_lock();c=load_variant(v.config);require_release(c);policy,legacy=load_locked_policy(v.policy)
    model=Path(v.model);receipt=json.loads((model.parent/'MODEL_RECEIPT.json').read_bytes());require(file_sha(model)==receipt['model_sha256'],'MODEL_BYTES_CHANGED')
    with offline_only():
        bundle=joblib.load(model);require(bundle['pipeline_lock_sha256']==file_sha(HERE/'PIPELINE_LOCK.json') and bundle['policy_sha256']==file_sha(v.policy),'TRAIN_INFER_IDENTITY');store=Inputs(v.data_dir)
        try:panel,pred,audit=infer_bundle(bundle,store,policy,legacy,c)
        finally:store.close()
        lint=write_result(v.output,panel,pred)
    Path(str(v.output)+'.receipt.json').write_bytes(encode({'lint':lint,'input_boundary_checks':audit,'inference_model_fits':0,'inference_preprocessor_fits':0,'inference_scope':'one well per call; TabPFN one row per query','config_fingerprint':fingerprint(c)}));print('PREDICTION_AND_LINTER_COMPLETED')
if __name__=='__main__':main()
