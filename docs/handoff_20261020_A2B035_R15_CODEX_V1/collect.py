import subprocess,json,hashlib,zipfile,io
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parent/'CODEX_A2B035_R14_REVIEW_20261020/publication_git'
COMMITS={'first':'51055b6458f17fc19f46c4b7a03da2f9a7a557e6','close':'42a5c66406f56af86520c3d65eb71d1fbb616fea'}
PREFIX={'first':'docs/handoff_20261020_A2B035_R15_W_B_V1','close':'docs/handoff_20261020_A2B035_R15_CLOSEOUT_B_V1'}
def git(*a):return subprocess.check_output(['git','-C',str(REPO),'-c','http.sslBackend=openssl','-c','http.version=HTTP/1.1',*a])
identity={}
for key,commit in COMMITS.items():
 git('fetch','--no-tags','--depth=1','origin',commit);src=R/key/'sources';src.mkdir(parents=True,exist_ok=True);files=[];members=[]
 for path in git('ls-tree','-r','--name-only',commit,'--',PREFIX[key]).decode().splitlines():
  b=git('show',commit+':'+path);dest=src/Path(path).name;dest.write_bytes(b);files.append({'path':path,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
  if dest.suffix=='.zip':
   z=zipfile.ZipFile(io.BytesIO(b));assert z.testzip() is None
   for n in z.namelist():
    if n.endswith('/'):continue
    assert not n.startswith('/') and '..' not in Path(n).parts
    out=R/key/'bundle'/n;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(n));members.append(n)
 identity[key]={'commit':commit,'files':files,'zip_members':members}
(R/'SOURCE_IDENTITIES.json').write_text(json.dumps(identity,indent=2),encoding='utf-8')
print(json.dumps({k:{'files':len(v['files']),'members':v['zip_members']} for k,v in identity.items()},indent=2))
