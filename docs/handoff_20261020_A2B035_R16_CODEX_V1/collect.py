"""Read fixed, anonymous public handoffs into A-only audit workspace."""
import subprocess,json,hashlib,zipfile,io
from pathlib import Path
R=Path(__file__).resolve().parent
REPO=R.parent/'CODEX_A2B035_R15_REVIEW_20261020/publication_git'
OBJECTS={
 'instruction':('441966be673da9083505168077a4d6ac63805e90','docs/handoff_20261020_A2B035_CLAUDE_INSTRUCTIONS_R16'),
 'first':('6ab552ef1cb007b13f0bc350957b7b82037f1348','docs/handoff_20261020_A2B035_R16_FIRST_B_V2'),
 'native':('12a197b396f80bb83e3a4ab18c8a45509b128026','docs/handoff_20261020_A2B035_R16_NATIVE_B_V1')}
def git(*a):
 return subprocess.check_output(['git','-C',str(REPO),'-c','http.sslBackend=openssl','-c','http.version=HTTP/1.1',*a],timeout=60)
def main():
 identities={}
 for key,(commit,prefix) in OBJECTS.items():
  git('fetch','--no-tags','--depth=1','origin',commit)
  dest=R/key/'sources';dest.mkdir(parents=True,exist_ok=True);files=[];members=[]
  for path in git('ls-tree','-r','--name-only',commit,'--',prefix).decode().splitlines():
   b=git('show',commit+':'+path);out=dest/Path(path).name;assert not out.exists();out.write_bytes(b)
   files.append({'path':path,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
   if out.suffix=='.zip':
    z=zipfile.ZipFile(io.BytesIO(b));assert z.testzip() is None
    for n in z.namelist():
     if n.endswith('/'):continue
     assert not n.startswith('/') and '..' not in Path(n).parts and ':' not in n
     p=R/key/'bundle'/n;p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(z.read(n));members.append(n)
  identities[key]={'commit':commit,'files':files,'zip_members':members}
  print(json.dumps({'object':key,'files':[Path(x['path']).name for x in files],'members':members},ensure_ascii=False))
 (R/'SOURCE_IDENTITIES.json').write_text(json.dumps(identities,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
