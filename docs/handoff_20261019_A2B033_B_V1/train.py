"""Train the retained B0-prime from raw issued data. No local cache required."""
import argparse,json
from pathlib import Path
from core import *
from fit_ledger import Ledger,fit_once
def run(a):
    out=Path(a.output).resolve();require(not out.exists(),'TRAIN_OUTPUT_EXISTS_NO_REFIT');out.mkdir(parents=True)
    release=json.loads((HERE/'RELEASE_GATE.json').read_bytes());require(release['step1_passed'] and release['delta']>=1 and release['positive_folds']>=4,'STEP1_NOT_PASSED')
    policy,config=load_policy(a.policy or HERE/'runtime_policy.json');store=Inputs(a.data_dir)
    try:history=load_train(store,config);panel,features,anchors,audit=build_train(history,config,policy)
    finally:store.close()
    ledger=Ledger(a.ledger or out/'FIT_LEDGER.json');pipe=fit_once(panel,features,config,ledger,a.stage)
    artifact={'version':'A2B-033/B0-prime','model':pipe,'feature_columns':features,'policy_sha256':file_sha(a.policy or HERE/'runtime_policy.json'),'training_identity':identity(panel,features),'cutoff':'T0-1','target':'M+1..M+12','status':'待Codex独立复核，未指定平台最终版本'}
    modelpath=out/'B0_prime.joblib';joblib.dump(artifact,modelpath,compress=3)
    receipt={'model_sha256':file_sha(modelpath),'model_bytes':modelpath.stat().st_size,'training_wells':81,'training_rows':972,'features':325,'stage':a.stage,'fit_counts':{k:v for k,v in ledger.value.items() if k!='events'},'audit':audit,'policy_sha256':artifact['policy_sha256']};(out/'MODEL_RECEIPT.json').write_bytes(encode(receipt));print(json.dumps({'stage':a.stage,'model_saved':True,'model_sha256':receipt['model_sha256'],'model_bytes':receipt['model_bytes'],'model_fits':1,'preprocessor_fits':1}));return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data_dir',required=True);p.add_argument('--output',required=True);p.add_argument('--policy');p.add_argument('--ledger');p.add_argument('--stage',default='standalone-full');args=p.parse_args()
    try:run(args)
    except Exception as exc:print(json.dumps({'status':'FAILED_STOP_NO_RETRY','exception_type':type(exc).__name__}));raise SystemExit(1)
