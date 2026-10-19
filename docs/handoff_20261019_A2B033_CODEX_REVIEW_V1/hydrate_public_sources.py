"""Fetch pinned public source/aggregate texts only, no competition data."""
import argparse,hashlib,json,time,urllib.parse,urllib.request
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--public-cache',type=Path);args=parser.parse_args()
records=json.loads((ROOT/'SOURCE_IDENTITY_CODEX.json').read_bytes())
records +=[dict(r,key='baseline/'+Path(r['path']).name) for r in json.loads((ROOT/'BASELINE_SOURCE_IDENTITY_CODEX.json').read_bytes())]
assert len(records)==51
network_retries=0
for r in records:
    key=PurePosixPath(r['key']);assert not key.is_absolute() and '..' not in key.parts
    ref=r['commit'];assert len(ref)==40 and set(ref)<=set('0123456789abcdef')
    path=r['path'];assert path=='LATEST.json' or path.startswith(('docs/','src/oil_uplift/'));assert Path(path).suffix in {'.md','.json','.py','.txt'}
    url='https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/'+ref+'/'+urllib.parse.quote(path)
    p=ROOT/'sources'/key
    if p.exists():
        b=p.read_bytes()
    elif args.public_cache:
        b=(args.public_cache/key).read_bytes()
    else:
        for attempt in range(3):
            try:
                b=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Public-source-audit'}),timeout=20).read();break
            except (OSError,urllib.error.URLError):
                if attempt==2:raise
                network_retries+=1;time.sleep(attempt+1)
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
    p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        with p.open('xb') as f:f.write(b)
B=ROOT/'sources/B033'
for r in json.loads((B/'FROZEN_SOURCES.json').read_bytes())['files']:
    b=r['text'].encode();p=(B/r['path']).resolve();assert p.is_relative_to(B.resolve()) and r['path'].startswith('src/oil_uplift/') and p.suffix=='.py'
    assert hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r['bytes'];p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==b
    else:
        with p.open('xb') as f:f.write(b)
print(json.dumps({'pinned_public_files':51,'embedded_public_method_modules':10,'all_hashes_match':True,'public_network_read_retries_not_fit_retries':network_retries,'competition_records_read':False,'fits':0}))
