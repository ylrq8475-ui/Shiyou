import subprocess,json,hashlib,zipfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'CODEX_A2B035_PIPELINE_REVIEW_20261019/publication_git'
COMMIT='6601551152ce4b21d8447fef6ad455e1277023e4'
PREFIX='docs/handoff_20261019_A2B035_SEARCH_B_V1'
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
out=ROOT/'sources';out.mkdir(exist_ok=True)
ident=[]
for path in git('ls-tree','-r','--name-only',COMMIT,'--',PREFIX).decode().splitlines():
    b=git('show',COMMIT+':'+path); p=out/Path(path).name;p.write_bytes(b)
    ident.append({'path':path,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
z=zipfile.ZipFile(io.BytesIO((out/'SEARCH_REPRO_ANONYMOUS.zip').read_bytes()))
assert z.testzip() is None
for n in z.namelist():
    assert not n.startswith('/') and '..' not in Path(n).parts
    if n.endswith('/'):continue
    p=ROOT/'bundle'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
(ROOT/'SOURCE_IDENTITIES.json').write_text(json.dumps({'commit':COMMIT,'files':ident,'zip_members':z.namelist()},indent=2),encoding='utf-8')
r=json.loads((out/'RESULT_DAILY_DELIVERY.json').read_bytes())
print(json.dumps({'files':len(ident),'zip_members':len(z.namelist()),'result_keys':list(r),'variant_keys':list(r['all_config_results'][0]),'fixed':r['all_config_results'][0]['fixed'],'repeat':r['all_config_results'][0].get('repeated')},ensure_ascii=False)[:10000])
