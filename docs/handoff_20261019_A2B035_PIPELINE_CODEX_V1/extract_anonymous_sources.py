import hashlib,json,zipfile
from pathlib import Path,PurePosixPath
R=Path(__file__).resolve().parent;B=R/'sources/B';D=R/'source_runtime';D.mkdir(exist_ok=False);manifest=json.loads((B/'SOURCE_BUNDLE_MANIFEST.json').read_bytes());expected={r['path']:r for r in manifest['members']}
with zipfile.ZipFile(B/'PIPELINE_SOURCE_ANONYMOUS.zip') as z:
    assert set(z.namelist())==set(expected) and z.testzip() is None
    for info in z.infolist():
        p=PurePosixPath(info.filename);assert p.parts[0]=='source' and not p.is_absolute() and '..' not in p.parts;b=z.read(info);assert hashlib.sha256(b).hexdigest()==expected[info.filename]['sha256'] and len(b)==expected[info.filename]['bytes'];out=D.joinpath(*p.parts[1:]);assert out.resolve().is_relative_to(D.resolve());out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('xb') as f:f.write(b)
print(json.dumps({'public_source_members':len(expected),'ML_imports':0,'fits':0}))
