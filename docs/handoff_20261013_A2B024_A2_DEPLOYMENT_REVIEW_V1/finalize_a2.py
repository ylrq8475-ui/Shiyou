"""Publishable allowlist only; private attached values stay in memory for scanning."""
import argparse,csv,hashlib,io,json,re,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;DEST=HERE/'delivery_A2'
sha=lambda b:hashlib.sha256(b).hexdigest()
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b)
NAMES=['README.md','REPORT_A.md','COLLABORATION_REPLY_A.md','SCORE_LEDGER_A2.json','AUDIT_QUEUE_A2.md','FINAL_SIGNOFF_A2.md','SOURCE_AND_LEVELS_A2.json',
       'ATTACHMENT_COMPARISON_A2.json','PACKAGE_METADATA_A2.json','INDEPENDENT_AGGREGATE_A2.json','ERROR_MECHANISM_A2.json',
       'B_SYNTHETIC_RESULT_A2.json','B_SYNTHETIC_LOG_A2.txt','A2_INDEPENDENT_SYNTHETIC_RESULT.json','A2_INDEPENDENT_SYNTHETIC_LOG.txt',
       'SOURCE_SPEC.json','SOURCE_RECEIPT_A2.json','receive_public_sources.py','inspect_attachments.py','package_metadata_a2.py',
       'independent_evidence_a2.py','derive_mechanism_a2.py','run_synthetic_a2.py','test_independent_a2.py','finalize_a2.py']
def main(a):
    assert not DEST.exists()
    identifiers=set()
    for p in [a.old_result,a.new_result]:
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                for row in csv.DictReader(io.StringIO(z.read(n).decode('utf-8-sig'))):identifiers.add(row['WELL_ID'])
    assert len(identifiers)==10
    secret=re.compile(rb'(github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
    data={n:(HERE/n).read_bytes() for n in NAMES}
    for b in data.values():assert not any(x.encode() in b for x in identifiers) and not secret.search(b)
    evidence=json.loads(data['ATTACHMENT_COMPARISON_A2.json']);assert evidence['prediction_comparison']['changed_prediction_rows']==0
    assert json.loads(data['INDEPENDENT_AGGREGATE_A2.json'])['all_passed']
    for n in ['B_SYNTHETIC_RESULT_A2.json','A2_INDEPENDENT_SYNTHETIC_RESULT.json']:assert json.loads(data[n])['passed']
    DEST.mkdir()
    for n,b in data.items():put(DEST/n,b)
    privacy={'signature':'账户A（新接手）独立审核与交付','account':'A2','passed':True,'manual_review_complete':True,
             'known_marker_scan_executed':True,'known_markers_checked':10,'known_marker_hits':0,'known_marker_origin':'authorized attached result ZIP identifiers in memory only',
             'full_training_well_or_private_candidate_value_inventory_scanned':False,'credential_pattern_hits':0,
             'source_scope':'explicit A2 anonymous reports and programs; no attached archives or weights included',
             'raw_data_private_config_weights_per_well_values_included':False,'private_models_loaded':0,'real_model_or_preprocessor_fits':0,
             'audit_does_not_claim_complete_detection_of_all_unknown_private_values':True}
    put(DEST/'PUBLICATION_PRIVACY_CHECK.json',enc(privacy));data['PUBLICATION_PRIVACY_CHECK.json']=enc(privacy)
    sums={'files':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in data.items()},'manifest_excludes_itself':True}
    put(DEST/'A_SHA256SUMS.json',enc(sums));data['A_SHA256SUMS.json']=enc(sums)
    archive='A2B024_A2_DEPLOYMENT_READONLY_REVIEW_20261013.zip'
    with zipfile.ZipFile(DEST/archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,b in sorted(data.items()):z.writestr(n,b)
    with zipfile.ZipFile(DEST/archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(data)
        assert all(z.read(n)==data[n] for n in z.namelist())
    put(DEST/(archive+'.sha256'),(sha((DEST/archive).read_bytes())+'  '+archive+'\n').encode())
    manifest={'signature':'账户A（新接手）独立审核与交付','account':'A2','files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(DEST.iterdir())},
              'manifest_excludes_itself':True,'B_deployment_commit':'519b00da7dc29bae0448c797ee2e74e3e3cc35b3','score_handoff_commit':'b5e54cb8b5c0408a5eb620ac3026ce7fe71e7477',
              'no_raw_data_or_models_published':True,'formal_submission':False}
    put(DEST/'PUBLICATION_MANIFEST.json',enc(manifest))
    for p in DEST.iterdir():
        if p.suffix!='.zip':assert not any(x.encode() in p.read_bytes() for x in identifiers) and not secret.search(p.read_bytes())
    out={'public_files':len(list(DEST.iterdir())),'archive':archive,'archive_sha256':sha((DEST/archive).read_bytes()),'privacy_checked_markers':10,'hits':0,'real_fits':0}
    put(HERE/'LOCAL_DELIVERY_RECEIPT_A2.json',enc(out));print(json.dumps(out))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--old-result',required=True);p.add_argument('--new-result',required=True);main(p.parse_args())
