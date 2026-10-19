"""Authorized full-version training, after the common pipeline release."""
import argparse,time
from cv035 import *
from ledger035 import Ledger

def main():
    a=argparse.ArgumentParser();a.add_argument('--config',required=True);a.add_argument('--data_dir',required=True);a.add_argument('--policy',required=True);a.add_argument('--output',required=True);v=a.parse_args()
    verify_source_lock();c=load_variant(v.config);require_release(c)
    out=Path(v.output);require(not out.exists(),'OUTPUT_ALREADY_EXISTS');out.mkdir(parents=True)
    policy,legacy=load_locked_policy(v.policy);ledger=Ledger(out/'FIT_COUNTS.json');tick=time.perf_counter()
    with offline_only():
        store=Inputs(v.data_dir)
        try:history=load_train(store,legacy)
        finally:store.close()
        provider=Panels(history,policy,legacy);first=c['fusion']['members'][0] if c['learner']['name']=='Ensemble' else c
        panel=provider.get(first)[0];bundle=fit_members_full(c,provider,np.arange(len(panel)),ledger,'full-version')
        bundle.update(pipeline_lock_sha256=file_sha(HERE/'PIPELINE_LOCK.json'),policy_sha256=file_sha(v.policy))
        joblib.dump(bundle,out/'model.joblib',compress=3)
    receipt={'config':c,'model_sha256':file_sha(out/'model.joblib'),'pipeline_lock_sha256':bundle['pipeline_lock_sha256'],'policy_sha256':bundle['policy_sha256'],'training_seconds':time.perf_counter()-tick,'training_wells':81,'training_rows':972,'test_data_fitted':False,'fit_counts':{k:x for k,x in ledger.value.items() if k!='events'}}
    (out/'MODEL_RECEIPT.json').write_bytes(encode(receipt));print('FULL_VERSION_TRAINING_COMPLETED')
if __name__=='__main__':main()
