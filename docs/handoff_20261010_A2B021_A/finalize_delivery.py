"""Build an allowlisted anonymous A audit package, never a competition package."""
from pathlib import Path
import hashlib,json,re,zipfile
from receive_evidence import private_markers
HERE=Path(__file__).resolve().parent
DEST=HERE/'delivery_A'
SOURCES=['README.md','REPORT_A.md','COLLABORATION_REPLY_A.md','NEXT_STEP.md','AUDIT_QUEUE.md','FINAL_SIGNOFF.md',
         'RECEIPT.json','A_INDEPENDENT_REVIEW.json','A_CHECK_DETAILS.json','A_DATA_FINDINGS.json','A_SYNTHETIC_TESTS.log',
         'independent_review.py','derive_data_findings.py','receive_evidence.py','PINNED_DIRECTORY.json','finalize_delivery.py']
def sha(data):return hashlib.sha256(data).hexdigest()
def need(ok,code):
    if not ok:raise RuntimeError(code)
def put(path,data):
    with path.open('xb') as f:f.write(data)
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

def main():
    need(not DEST.exists(),'DELIVERY_EXISTS')
    markers=private_markers();creds=re.compile(rb'(?:github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
    files={n:(HERE/n).read_bytes() for n in SOURCES}
    need(not any(m.encode() in d for m in markers for d in files.values()),'PRIVATE_MARKER')
    need(not any(creds.search(d) for d in files.values()),'CREDENTIAL')
    review=json.loads(files['A_INDEPENDENT_REVIEW.json']);need(review['synthetic']['passed'] and review['all_aggregate_checks_pass'] and review['A_real_fit_count']==0,'REVIEW_NOT_PASS')
    DEST.mkdir()
    for n,d in files.items():put(DEST/n,d)
    privacy={'account':'A independent audit and delivery','date':'2026-10-10','source_text_files_checked':len(files),
             'private_markers_checked':len(markers),'private_marker_hits':0,'credential_pattern_hits':0,
             'raw_data_copied':False,'raw_tables_private_config_per_well_labels_predictions_OOF_weights_included':False,
             'real_fits_for_review_or_publication':0,'public_file_allowlist_enforced':True,
             'scope':'known local private markers plus common credential patterns; not proof against every unknown sensitive value',
             'passed':True}
    put(DEST/'PUBLICATION_PRIVACY_CHECK.json',encoded(privacy))
    inner={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in DEST.iterdir() if p.is_file()}
    put(DEST/'A_SHA256SUMS.json',encoded({'files':inner,'manifest_excludes_itself':True}))
    archive=DEST/'A2B021_ACCOUNT_A_REVIEW_BUNDLE_20261010.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DEST.iterdir()):
            if p==archive:continue
            z.writestr(p.name,p.read_bytes())
    with zipfile.ZipFile(archive) as z:
        need(z.testzip() is None,'AUDIT_ZIP_CRC')
        for n in z.namelist():need(z.read(n)==(DEST/n).read_bytes(),'AUDIT_ZIP_BYTE_MISMATCH')
    put(DEST/(archive.name+'.sha256'),(sha(archive.read_bytes())+'  '+archive.name+'\n').encode())
    outer={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(DEST.iterdir()) if p.is_file()}
    manifest={'account':'A independent audit and delivery','date':'2026-10-10','B_reviewed_commit':'f3764bcc58337f9a4d86def44d5d6da9fc87ab95',
              'repository_directory':'docs/handoff_20261010_A2B021_A','additive_branch_delivery_only':True,'main_or_B_files_overwritten':False,
              'files':outer,'manifest_excludes_itself':True,'audit_package_is_not_formal_submission':True}
    put(DEST/'PUBLICATION_MANIFEST.json',encoded(manifest))
    for p in DEST.iterdir():
        if p.suffix=='.zip':continue
        d=p.read_bytes();need(not any(m.encode() in d for m in markers),'FINAL_PRIVATE_MARKER');need(not creds.search(d),'FINAL_CREDENTIAL')
    need(len(list(DEST.iterdir()))==len(SOURCES)+5,'PUBLIC_ALLOWLIST_FINAL')
    print(json.dumps({'status':'PASS','files':len(list(DEST.iterdir())),'audit_archive_sha256':sha(archive.read_bytes()),
                      'audit_archive_bytes':archive.stat().st_size,'known_private_markers_checked':len(markers),'privacy_hits':0,
                      'fits':0,'destination':str(DEST)},indent=2))
if __name__=='__main__':main()
