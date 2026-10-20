import subprocess,json,hashlib,zipfile,io
from pathlib import Path
R=Path(__file__).resolve().parent
REPO=R.parent/'CODEX_A2B035_SEARCH_REVIEW_20261020/publication_git'
B='f252407dba3af7b3800c8242518c8e156ad04a42';PREFIX='docs/handoff_20261020_A2B035_R14_PIPELINE_B_V1'
def git(*a):return subprocess.check_output(['git','-C',str(REPO),'-c','http.sslBackend=openssl','-c','http.version=HTTP/1.1',*a])
src=R/'sources';src.mkdir(exist_ok=True);ident=[]
for path in git('ls-tree','-r','--name-only',B,'--',PREFIX).decode().splitlines():
 b=git('show',B+':'+path);(src/Path(path).name).write_bytes(b);ident.append({'path':path,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
z=zipfile.ZipFile(io.BytesIO((src/'R14_INCREMENT_REVIEW_ANONYMOUS.zip').read_bytes()));assert z.testzip() is None
for n in z.namelist():
 if n.endswith('/'):continue
 assert not n.startswith('/') and '..' not in Path(n).parts
 p=R/'bundle'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
(R/'SOURCE_IDENTITIES.json').write_text(json.dumps({'reviews_commit':B,'published_files':ident,'zip_members':z.namelist()},indent=2),encoding='utf-8')
print(json.dumps({'files':len(ident),'members':z.namelist()},indent=2))
