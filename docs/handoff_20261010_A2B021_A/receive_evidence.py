"""Receive public, commit-pinned audit evidence; never copy competition data."""
from pathlib import Path, PurePosixPath
import csv, hashlib, json, stat, urllib.request, zipfile
import yaml

HERE = Path(__file__).resolve().parent
COMMIT = 'f3764bcc58337f9a4d86def44d5d6da9fc87ab95'
B = Path(r'C:\Users\Admin\petroleum_uplift_prediction')

def need(ok, code):
    if not ok: raise RuntimeError(code)

def sha(data): return hashlib.sha256(data).hexdigest()

def private_markers():
    cfg = yaml.safe_load((B/'configs/private_data_inferred_v7_safe_plus_layer.yaml').read_text(encoding='utf-8'))
    raw = Path(cfg['data']['input_dir']); values = set()
    for sub in ['data/train_data', 'data/test_data']:
        for p in (raw/sub).glob('*.csv'):
            with p.open(encoding='utf-8-sig', newline='') as f:
                values.update(row['WELL_ID'] for row in csv.DictReader(f))
    values.update(str(v) for v in cfg['anchors']['eligible_event_values'])
    need(len(values) == 100, 'MARKER_COVERAGE')
    return values

def fetch(url):
    need(url.startswith(('https://api.github.com/', 'https://raw.githubusercontent.com/')), 'HOST_NOT_ALLOWED')
    request = urllib.request.Request(url, headers={'User-Agent':'Account-A-readonly-audit'})
    with urllib.request.urlopen(request, timeout=40) as response: return response.read()

def main():
    dest = HERE/'received'; extracted = HERE/'bundle'
    need(not dest.exists() and not extracted.exists(), 'DESTINATION_EXISTS')
    # Directory metadata came from the authenticated GitHub read-only connector.
    entries = json.loads((HERE/'PINNED_DIRECTORY.json').read_text(encoding='utf-8'))
    need(len(entries) == 17 and all(e['type']=='file' for e in entries), 'DIRECTORY_CHANGED')
    content = {}
    for e in entries:
        need('/' not in e['name'] and '\\' not in e['name'], 'UNSAFE_NAME')
        data = fetch(e['download_url'])
        need(len(data)==e['size'], 'DOWNLOAD_SIZE')
        need(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==e['sha'], 'GIT_BLOB_MISMATCH')
        content[e['name']] = data
    manifest = json.loads(content['PUBLICATION_MANIFEST.json'].decode('utf-8-sig'))
    m = manifest['files']
    need(set(m)==set(content)-{'PUBLICATION_MANIFEST.json'}, 'PUBLICATION_COVERAGE')
    for n, v in m.items(): need(len(content[n])==v['bytes'] and sha(content[n])==v['sha256'], 'PUBLICATION_HASH')
    archive = content['A2B021_READONLY_REVIEW_BUNDLE_v2.zip']
    need(sha(archive)=='94ce5a9c3f3fc0e18b0fec7fcdf8c21dc094cad967cf59b480ba842abffcb7ef', 'ARCHIVE_HASH')
    import io
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        need(z.testzip() is None, 'ZIP_CRC')
        infos=z.infolist(); need(sum(i.file_size for i in infos)<15_000_000,'ZIP_TOO_LARGE')
        need(len(infos)==len(set(i.filename.casefold() for i in infos)), 'DUPLICATE_PATH')
        inner={}
        for i in infos:
            p=PurePosixPath(i.filename)
            need(not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename and ':' not in i.filename, 'UNSAFE_PATH')
            need(not stat.S_ISLNK(i.external_attr>>16), 'SYMLINK')
            if i.is_dir(): continue
            need(p.suffix.lower() in {'.md','.json','.py','.txt','.toml','.diff','.yaml','.yml','.log','.sha256'}, 'UNEXPECTED_TYPE_'+p.suffix.lower())
            inner[i.filename]=z.read(i.filename)
    markers=private_markers()
    checked=[d for n,d in content.items() if not n.endswith('.zip')] + list(inner.values())
    need(not any(v.encode() in d for v in markers for d in checked), 'PRIVATE_MARKER_HIT')
    for root, files in [(dest,content),(extracted,inner)]:
        root.mkdir()
        for n,d in files.items():
            p=(root/n).resolve(); need(p.is_relative_to(root.resolve()),'PATH_ESCAPE')
            p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(d)
    result={'status':'PASS','B_commit':COMMIT,'public_files':len(content),'archive_files':len(inner),
            'archive_sha256':sha(archive),'private_markers_checked':len(markers),'privacy_hits':0,
            'fits':0,'original_data_copied':False,'Git_blob_and_publication_hashes_match':True}
    with (HERE/'RECEIPT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))

if __name__=='__main__':main()
