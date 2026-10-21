"""Read fixed anonymous public handoffs, never competition data or model weights."""
import subprocess,json,hashlib,zipfile,io
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parent/'CODEX_A2B035_R16_REVIEW_20261020/publication_git'
OBJECTS={
 'instruction':('7f44d70aa53410a2d072d69874003f3a8946adbb','docs/handoff_20261020_A2B035_CLAUDE_INSTRUCTIONS_R17'),
 'b0':('bc6963756f1feaf16154e9edacc96e648c74e63a','docs/handoff_20261020_A2B035_R17_B0_AUDITII_B_V1'),
 'fusion':('742e573cac082cc6921f46255e07c566439360e4','docs/handoff_20261020_A2B035_R17_FIXED_FUSIONS_B_V1')}
def git(*a):return subprocess.check_output(['git','-C',str(REPO),'-c','http.sslBackend=openssl','-c','http.version=HTTP/1.1',*a],timeout=60)
def main():
 identities={}
 for key,(commit,prefix) in OBJECTS.items():
  git('fetch','--no-tags','--depth=1','origin',commit);listing=git('ls-tree','-r','-l',commit,'--',prefix).decode();print(key,listing)
  dest=R/key/'sources';dest.mkdir(parents=True,exist_ok=True);files=[];members=[]
  for path in git('ls-tree','-r','--name-only',commit,'--',prefix).decode().splitlines():
   filename=Path(path).name
   assert filename not in ['result.zip','submission_code.zip'] and Path(filename).suffix.lower() not in ['.joblib','.pt','.ckpt','.safetensors','.csv']
   b=git('show',commit+':'+path);out=dest/filename;assert not out.exists();out.write_bytes(b);files.append({'path':path,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
   if out.suffix=='.zip':
    assert any(s in filename.lower() for s in ['source','anonymous'])
    z=zipfile.ZipFile(io.BytesIO(b));assert z.testzip() is None
    for n in z.namelist():
     if n.endswith('/'):continue
     assert not n.startswith('/') and '..' not in Path(n).parts and ':' not in n and Path(n).suffix.lower() not in ['.csv','.joblib','.pt','.ckpt','.safetensors']
     p=R/key/'bundle'/n;p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(z.read(n));members.append(n)
  identities[key]={'commit':commit,'files':files,'zip_members':members};print('members',key,json.dumps(members))
 (R/'SOURCE_IDENTITIES.json').write_text(json.dumps(identities,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
