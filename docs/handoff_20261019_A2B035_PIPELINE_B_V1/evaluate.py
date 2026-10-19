"""One complete config, fixed plus prespecified repeated group CV."""
import argparse
from cv035 import *
from ledger035 import Ledger

def main():
    a=argparse.ArgumentParser();a.add_argument('--config',required=True);a.add_argument('--data_dir',required=True);a.add_argument('--policy',required=True);a.add_argument('--output',required=True);v=a.parse_args()
    verify_source_lock();c=load_variant(v.config);require_release(c);out=Path(v.output);require(not out.exists(),'OUTPUT_ALREADY_EXISTS');out.mkdir(parents=True)
    policy,legacy=load_locked_policy(v.policy);ledger=Ledger(out/'FIT_COUNTS.json')
    with offline_only():
        store=Inputs(v.data_dir)
        try:history=load_train(store,legacy)
        finally:store.close()
        provider=Panels(history,policy,legacy);first=c['fusion']['members'][0] if c['learner']['name']=='Ensemble' else c;panel=provider.get(first)[0];splits=split_sets(panel)
        require(split_fingerprints(splits)==json.loads((HERE/'DATA_CONTRACT.json').read_bytes())['split_fingerprints'],'GROUP_SPLITS_CHANGED')
        if 'split_fingerprints' in c:require(c['split_fingerprints']==split_fingerprints(splits),'CONFIG_SPLITS_CHANGED')
        results={}
        for name,folds in splits.items():
            verify_source_lock();results[name],oof=evaluate_split(c,provider,folds,ledger,name,out/'folds');del oof
        results['repeated_summary']=repeated_summary([results['repeat_'+str(i)] for i in range(1,6)])
    (out/'RESULT.json').write_bytes(encode({'config':c,'results':results,'row_oof_persisted':False}));print('COMPLETE_CONFIG_EVALUATED')
if __name__=='__main__':main()
