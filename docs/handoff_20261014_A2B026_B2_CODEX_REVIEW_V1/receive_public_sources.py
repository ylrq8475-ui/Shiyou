"""Receive pinned, public handoff artifacts only; no competition data requests."""
import concurrent.futures
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / 'CODEX026_B2_IMPLEMENTATION_REVIEW_20261014/publication_git'
B = '3926e2972da62c61eb318abaa670a5da776d62ec'
PREFIX = 'docs/handoff_20261014_A2B026_ROUTE_B_B2_B_V1'

def git(*args):
    result = subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError('PUBLIC_TREE_READ_FAILED')
    return result.stdout.decode().strip()

def receive(item):
    label, commit, path = item
    name = PurePosixPath(path).name
    if not name or name.endswith(('.joblib', '.pkl', '.csv', '.zip')) or len(commit) != 40:
        raise RuntimeError('PUBLIC_SOURCE_ALLOWLIST_VIOLATION')
    url = 'https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/' + commit + '/' + path
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Account-A2-pinned-public-review'}), timeout=25) as response:
                data = response.read()
            break
        except Exception:
            if attempt == 2:
                raise
    target = ROOT / 'sources' / label / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != data:
            raise RuntimeError('SOURCE_BYTES_CHANGED')
    else:
        with target.open('xb') as out:
            out.write(data)
    return {'label': label, 'commit': commit, 'path': path, 'local': target.relative_to(ROOT).as_posix(), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}

def main():
    paths = git('ls-tree', '-r', '--name-only', B, '--', PREFIX).splitlines()
    items = [('B', B, path) for path in paths]
    items += [('Claude', '088a71ae8760a57272f68cc2cb538b0a8eecc288', 'docs/handoff_20261014_A2B026_CLAUDE_INSTRUCTIONS_R3/' + n) for n in ['INSTRUCTION_ORIGINAL.md', 'SHA256SUMS.json']]
    items += [('R2', '213b1b465c61d799371e2b4326ebc71922c4f7ee', 'docs/handoff_20261014_A2B026_B_CLOSEOUT_ROUTE_B_R2/' + n) for n in ['PREREG_ROUTE_B.md', 'PREREG_PARAMETERS.json']]
    items += [('rules', '0536eafab45b71ffd5f8f0160ee7957f1edd661d', 'docs/handoff_20261014_THREE_ACCOUNT_PROMPTS_V3/' + n) for n in ['PROMPT_CODEX.md', 'DELIVERY_REGISTRATION_RULES.md', 'SHA256SUMS.json']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(receive, items))
    actual = {line.split('\t')[1]: line.split('\t')[0].split()[2] for line in git('ls-tree', '-r', B, '--', PREFIX).splitlines()}
    if any(actual[r['path']] != r['git_blob'] for r in rows if r['label'] == 'B'):
        raise RuntimeError('PUBLIC_B_SOURCE_GIT_IDENTITY_MISMATCH')
    receipt = {'B_commit': B, 'B_prefix': PREFIX, 'B_files': len(paths), 'all_public_sources': len(rows), 'B_git_blobs_match': True, 'original_data_read': False, 'files': rows}
    with (ROOT / 'SOURCE_RETRIEVAL_CODEX.json').open('x', encoding='utf-8') as out:
        json.dump(receipt, out, ensure_ascii=False, indent=2)
        out.write('\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'files'}))

if __name__ == '__main__':
    main()
