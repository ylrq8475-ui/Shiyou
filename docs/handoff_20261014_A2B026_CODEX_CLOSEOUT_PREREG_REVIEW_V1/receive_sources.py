"""Retrieve pinned PUBLIC review files only; validate Git blob identity."""
import concurrent.futures, hashlib, json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def fetch(task):
    label, commit, prefix, entry = task
    url = f"https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/{commit}/{entry['path']}"
    for attempt in range(3):
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'Codex-Public-Review'})
            with urllib.request.urlopen(request, timeout=25) as response:
                payload = response.read()
            break
        except Exception:
            if attempt==2: raise
    blob = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    if blob != entry['sha'] or len(payload) != entry['size']:
        raise RuntimeError('PUBLIC_SOURCE_IDENTITY_MISMATCH')
    relative = entry['path'][len(prefix)+1:]
    target = ROOT/'sources'/label/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != payload: raise RuntimeError('EXISTING_SOURCE_DIFFERS')
    else:
        with target.open('xb') as out: out.write(payload)
    return {'label':label,'commit':commit,'path':entry['path'],'bytes':len(payload),
            'git_blob':blob,'sha256':hashlib.sha256(payload).hexdigest()}

if __name__ == '__main__':
    specs = json.loads((ROOT/'SOURCE_SPEC.json').read_bytes())
    if (ROOT/'EXTRA_SOURCE_SPEC.json').exists():
        specs += json.loads((ROOT/'EXTRA_SOURCE_SPEC.json').read_bytes())
    tasks = [(s['label'],s['commit'],s['prefix'],e) for s in specs for e in s['files']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        receipt = sorted(pool.map(fetch,tasks),key=lambda x:(x['label'],x['path']))
    content = json.dumps({'public_files':len(receipt),'all_git_blob_and_size_verified':True,
                          'raw_competition_data_read':False,'files':receipt},indent=2).encode()
    output=ROOT/('SOURCE_RETRIEVAL_EXTENDED_CODEX.json' if (ROOT/'EXTRA_SOURCE_SPEC.json').exists() else 'SOURCE_RETRIEVAL_CODEX.json')
    if output.exists():
        if output.read_bytes()!=content:raise RuntimeError('RECEIPT_DIFFERS')
    else:
        with output.open('xb') as out: out.write(content)
    print(json.dumps({'public_files':len(receipt),'all_git_blob_and_size_verified':True}))
