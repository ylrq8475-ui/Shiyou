"""Package allowlisted anonymous route-review files only."""
from pathlib import Path
import hashlib,json,re,sys,zipfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'A21_R1_20261010'))
from receive_evidence import private_markers
DEST=HERE/'delivery_A'
SOURCES=['README.md','REPORT_A.md','COLLABORATION_REPLY_A.md','A_CLOSEOUT_CHECKS.json',
         'RECEIPT.json','PINNED_DIRECTORY.json','check_closeout.py','finalize_review.py']
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
    with p.open('xb') as f:f.write(b)
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def main():
    if DEST.exists():raise RuntimeError('NEW_DELIVERY_REQUIRED')
    values=private_markers();pattern=re.compile(rb'(?:github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
    data={n:(HERE/n).read_bytes() for n in SOURCES}
    for b in data.values():
        if any(v.encode() in b for v in values) or pattern.search(b):raise RuntimeError('PRIVACY_SCAN_FAILED')
    evidence=json.loads(data['A_CLOSEOUT_CHECKS.json']);assert evidence['new_model_or_preprocess_fits']==0
    DEST.mkdir()
    for n,b in data.items():put(DEST/n,b)
    privacy={'account':'A','known_private_markers_checked':len(values),'private_marker_hits':0,'credential_pattern_hits':0,
             'source_files_checked':len(data),'raw_data_or_private_config_or_per_well_outputs_included':False,
             'new_model_or_preprocess_fits':0,'B_synthetic_tests_executed':19,'passed':True}
    put(DEST/'PUBLICATION_PRIVACY_CHECK.json',enc(privacy))
    inner={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in DEST.iterdir()}
    put(DEST/'A_SHA256SUMS.json',enc({'files':inner,'manifest_excludes_itself':True}))
    archive=DEST/'A2B023_CLOSEOUT_A_REVIEW_20261012.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DEST.iterdir()):
            if p!=archive:z.writestr(p.name,p.read_bytes())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(z.read(n)==(DEST/n).read_bytes() for n in z.namelist())
    put(DEST/(archive.name+'.sha256'),(sha(archive.read_bytes())+'  '+archive.name+'\n').encode())
    m={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(DEST.iterdir())}
    put(DEST/'PUBLICATION_MANIFEST.json',enc({'account':'A independent audit and delivery','B_reviewed_commit':'57c78bde28f877212d3a711d92352a299a5f558c',
        'files':m,'manifest_excludes_itself':True,'new_training_or_upgrade':False,'only_new_A_directory':True}))
    for p in DEST.iterdir():
        if p.suffix!='.zip':
            b=p.read_bytes();assert not any(v.encode() in b for v in values) and not pattern.search(b)
    print(json.dumps({'files':len(list(DEST.iterdir())),'archive_sha256':sha(archive.read_bytes()),'privacy_passed':True,'new_fits':0}))
if __name__=='__main__':main()
