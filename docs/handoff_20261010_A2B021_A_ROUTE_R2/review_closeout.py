"""Review B closeout and route evidence without raw data or any model fitting."""
from pathlib import Path
import hashlib,json,urllib.request,statistics
HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'A21_R1_20261010'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def need(ok,code):
    if not ok:raise RuntimeError(code)
def put(p,b):
    with p.open('xb') as f:f.write(b)
def main():
    folder=HERE/'received';need(not folder.exists(),'NEW_DIRECTORY_REQUIRED');folder.mkdir()
    sources=load(HERE/'PINNED_SOURCES.json');files={}
    for e in sources:
        url=e['download_url'];need('/2c677b28a9060874b872716bab3b389ae4f2dd7f/' in url and url.startswith('https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/'),'UNPINNED_URL')
        with urllib.request.urlopen(url,timeout=40) as response:b=response.read()
        need(len(b)==e['size'] and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==e['sha'],'GIT_BLOB_MISMATCH')
        files[e['name']]=b;put(folder/e['name'],b)
    m=json.loads(files['PUBLICATION_MANIFEST.json']);checks=[]
    for n,v in m['files'].items():need(len(files[n])==v['bytes'] and sha(files[n])==v['sha256'],'CLOSEOUT_MANIFEST');checks.append(n)
    receipt=json.loads(files['RECEIPT_VERIFICATION.json'])
    need(receipt['A_source_commit']=='13e25c5ee43ef9a3e5f7498c8969867d6388c89f','A_SOURCE_VERSION')
    for item in receipt['received_file_hashes']:
        b=(PRIOR/'delivery_A'/item['name']).read_bytes()
        need(sha(b)==item['sha256'] and len(b)==item['bytes'],'B_RECEIPT_VS_A_BYTES')
    need(receipt['new_fits_for_this_receipt']==0 and receipt['new_diagnostic_or_training_started'] is False,'NOT_A_NEW_MODEL_EXPERIMENT')
    need(receipt['A_real_fit_reproduction'] is False and receipt['research_status']=='STOPPED_NO_QUALIFIED_CANDIDATE','LIMITED_REVIEW_STATUS')
    seeds=[20260917,20261031,20261219,20270107,20270303]
    rows=[load(PRIOR/f'bundle/payload/execution/REPEAT_{seed}.json')['arms']['B0'] for seed in seeds]
    loss=statistics.mean(r['official_weighted_prefix_loss']['12'] for r in rows)
    groups={}
    for name in rows[0]['diagnostics']['prediction_state_groups']:
        group=[r['diagnostics']['prediction_state_groups'][name] for r in rows]
        need(all(g['status']=='RELEASED' for g in group),'UNRELEASED_GROUP')
        n=statistics.mean(g['group_wells'] for g in group)
        contribution=statistics.mean(g['group_wells']*g['full_mean_weighted_loss']/81 for g in group)
        groups[name]={'mean_wells_across_existing_five_repeats':n,'well_share':n/81,'loss_share':contribution/loss,
                      'loss_share_minus_well_share_percentage_points':100*(contribution/loss-n/81)}
    result={'account':'A','reviewed_B_commit':'2c677b28a9060874b872716bab3b389ae4f2dd7f',
            'delivery_type':'A2B021_RECEIPT_CLOSEOUT_NOT_NEW_TRAINING','B_public_files_verified':len(sources),
            'B_closeout_manifest_entries_verified':len(checks),'B_receipt_matches_A_original_files':len(receipt['received_file_hashes']),
            'B_new_model_fits':0,'A_new_model_or_preprocess_fits':0,'prior_tests_not_rerun':True,
            'forecast_state_loss_and_population_comparison':groups,'independent_wells_still':81,
            'five_repeats_are_not_405_independent_wells':True,
            'event_and_forecast_time_P0':'OPEN','historical_dtype':'UNKNOWN','status':'PASS_LIMITED_CLOSEOUT_REVIEW'}
    put(HERE/'ROUTE_REVIEW_EVIDENCE.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
