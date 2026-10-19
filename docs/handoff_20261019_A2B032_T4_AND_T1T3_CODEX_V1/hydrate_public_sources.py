"""Recover only pinned public audit texts; never obtain competition data."""
import hashlib, json, urllib.request
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parent
records=json.loads((ROOT/'SOURCE_IDENTITY_CODEX.json').read_bytes())
assert len(records)==27
for r in records:
    key=PurePosixPath(r['key']);assert not key.is_absolute() and '..' not in key.parts
    ref=r['commit'];assert len(ref)==40 and all(c in '0123456789abcdef' for c in ref)
    path=r['path'];assert path=='LATEST.json' or path.startswith('docs/')
    assert Path(path).suffix in {'.md','.py','.json','.txt'}
    url='https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/'+ref+'/'+urllib.request.quote(path)
    b=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Public-audit-source-review'}),timeout=30).read()
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
    out=ROOT/'sources'/key;out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as f:f.write(b)
print(json.dumps({'pinned_public_files':27,'all_hashes_match':True,'competition_data_accessed':False,'fits':0}))
