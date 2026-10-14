"""Receive exactly the public modules bound by B's source receipt."""
import concurrent.futures, hashlib, json, urllib.request
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parent
receipt=json.loads((ROOT/'sources/B/SOURCE_RECEIPT.json').read_bytes())
def receive(row):
    rel=PurePosixPath(row['path'])
    if rel.is_absolute() or '..' in rel.parts or rel.suffix!='.py':raise RuntimeError('PUBLIC_MODULE_PATH_INVALID')
    commit=row['public_git_source_commit']
    url='https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/'+commit+'/src/'+rel.as_posix()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Account-A2-public-module-check'}),timeout=25) as response:body=response.read()
    if len(body)!=row['bytes'] or hashlib.sha256(body).hexdigest()!=row['sha256']:raise RuntimeError('PUBLIC_MODULE_IDENTITY_MISMATCH')
    target=ROOT/'sources/project_src'/rel;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.read_bytes()!=body:raise RuntimeError('LOCAL_MODULE_BYTES_CHANGED')
    else:
        with target.open('xb') as out:out.write(body)
    return {'path':rel.as_posix(),'commit':commit,'sha256':row['sha256'],'bytes':len(body),'public_module_identity_verified':True}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(receive,receipt['project_sources']))
with (ROOT/'PUBLIC_MODULE_IDENTITY_CODEX.json').open('x',encoding='utf-8') as out:json.dump({'modules':rows,'verified':len(rows),'real_data_read':False},out,indent=2)
print(json.dumps({'public_modules_verified':len(rows),'model_fits':0,'real_data_read':False}))
