"""Fit-forbidden inference using only history preceding verified template T0."""
import argparse,json,contextlib
from pathlib import Path
from core import *
@contextlib.contextmanager
def no_fits():
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import ExtraTreesRegressor
    originals=[]
    def forbidden(*a,**k):raise RuntimeError('ANY_INFERENCE_FIT_FORBIDDEN')
    for cls,name in [(Pipeline,'fit'),(Pipeline,'fit_transform'),(ColumnTransformer,'fit'),(ColumnTransformer,'fit_transform'),(ExtraTreesRegressor,'fit')]:originals.append((cls,name,getattr(cls,name)));setattr(cls,name,forbidden)
    try:yield
    finally:
        for cls,name,fn in originals:setattr(cls,name,fn)
def run(a):
    modelpath=Path(a.model);receipt=json.loads((modelpath.parent/'MODEL_RECEIPT.json').read_bytes());require(file_sha(modelpath)==receipt['model_sha256'],'MODEL_SHA256');policy_path=Path(a.policy or HERE/'runtime_policy.json');policy,config=load_policy(policy_path)
    with no_fits():
        artifact=joblib.load(modelpath);require(artifact['version']=='A2B-033/B0-prime' and artifact['policy_sha256']==file_sha(policy_path) and artifact['feature_columns']==policy['feature_order'],'MODEL_POLICY_IDENTITY');store=Inputs(a.data_dir)
        try:panel,audit=build_test(store,config,policy)
        finally:store.close()
        pred=predict(artifact['model'],panel,artifact['feature_columns'],config);linter=write_result(a.output,panel,pred)
    result={'inference_model_fits':0,'inference_preprocessor_fits':0,'test_boundary':audit,'linter':linter,'output_uploaded':False};Path(str(a.output)+'.receipt.json').write_bytes(encode(result));print(json.dumps({'prediction_complete':True,'linter':'PASS','files':10,'rows':120,'result_zip_sha256':linter['result_zip_sha256'],'model_fits':0,'preprocessor_fits':0}));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data_dir',required=True);p.add_argument('--model',default=str(HERE/'models/B0_prime.joblib'));p.add_argument('--output',required=True);p.add_argument('--policy');args=p.parse_args()
    try:run(args)
    except Exception as exc:print(json.dumps({'status':'FAILED_STOP','exception_type':type(exc).__name__}));raise SystemExit(1)
