"""Read only fixed public anonymous evidence. No competition data access."""
from pathlib import Path,PurePosixPath
from concurrent.futures import ThreadPoolExecutor
import hashlib,io,json,stat,time,urllib.request,zipfile
HERE=Path(__file__).resolve().parent
def need(ok,msg):
    if not ok:raise RuntimeError(msg)
sha=lambda b:hashlib.sha256(b).hexdigest()
spec=json.loads((HERE/'SOURCE_SPEC.json').read_bytes())
dest=HERE/'sources';need(not dest.exists(),'NEW_SOURCE_DESTINATION_REQUIRED')
def get(e):
    url=e['download_url'];need(url.startswith('https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/'),'PUBLIC_SOURCE_HOST')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Account-A2-independent-readonly-audit'}),timeout=45) as r:b=r.read()
            break
        except Exception:
            if attempt==2:raise
            time.sleep(1)
    need(len(b)==e['size'] and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==e['sha'],'GIT_BLOB_IDENTITY')
    return e['name'],b
all_sources={}
for s in spec:
    with ThreadPoolExecutor(max_workers=4) as pool:all_sources[s['tag']]=dict(pool.map(get,s['entries']))
score=all_sources['score'];checks=json.loads(score['SHA256SUMS.json'])
need(set(checks)==set(score)-{'SHA256SUMS.json'},'SCORE_CHECKSUM_COVERAGE')
for n,v in checks.items():need(sha(score[n])==v,'SCORE_SHA256')
need(sha(all_sources['deploy']['ANONYMOUS_REVIEW_BUNDLE.zip'])=='c7415aece02ea6cc360121f7498dd728d077bf71433aaee50937bbe89a499e4d','DEPLOYMENT_BUNDLE_SHA256')
records=[]
for s in spec:
    for n,b in all_sources[s['tag']].items():
        p=dest/s['tag']/n;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(b)
        records.append({'role':s['tag'],'file':n,'commit':s['commit'],'bytes':len(b),'sha256':sha(b),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()})
for tag,zname in [('deploy','ANONYMOUS_REVIEW_BUNDLE.zip'),('research','A2B024_R2_B_ANONYMOUS_REVIEW_BUNDLE.zip')]:
    inner={}
    with zipfile.ZipFile(io.BytesIO(all_sources[tag][zname])) as z:
        need(z.testzip() is None,'ZIP_CRC');infos=z.infolist()
        need(sum(i.file_size for i in infos)<30_000_000,'ZIP_SIZE')
        need(len(infos)==len({i.filename.casefold() for i in infos}),'DUPLICATE_PATH')
        for i in infos:
            p=PurePosixPath(i.filename);need(not p.is_absolute() and '..' not in p.parts and ':' not in i.filename and '\\' not in i.filename,'ZIP_PATH')
            need(not stat.S_ISLNK(i.external_attr>>16),'ZIP_SYMLINK')
            if i.is_dir():continue
            need(p.suffix.lower() in {'.md','.json','.py','.txt','.toml','.yaml','.yml','.log','.sha256','.diff'},'PUBLIC_BUNDLE_FILE_TYPE')
            inner[i.filename]=z.read(i)
    for n,b in inner.items():
        p=HERE/(tag+'_bundle')/n;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(b)
result={'signature':'账户A（新接手）独立审核与交付','public_files':len(records),'source_records':records,
        'fixed_public_git_blobs_verified':True,'score_manifest_verified':True,'deployment_bundle_expected_sha256_verified':True,
        'model_or_preprocessing_fits':0,'original_competition_data_read_or_copied':False}
with (HERE/'SOURCE_RECEIPT_A2.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='source_records'},ensure_ascii=False))
