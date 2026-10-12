"""Restore a pinned anonymous audit bundle into a NEW directory; never train."""
import argparse
import hashlib
import json
import runpy
import sys
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode=True
COMMIT='65115714d49d17122989195910b119264bd93880'
URL='https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/'+COMMIT+'/docs/handoff_20261012_A2B024_B/A2B024_R2_B_ANONYMOUS_REVIEW_BUNDLE.zip'
EXPECTED='c26a1c87c0fdb4d96b4a3251aa13702ab7aeb258517edd2614029cf0d2393d50'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True,help='A new independent directory, must not exist')
    parser.add_argument('--archive',type=Path,help='Optional already-downloaded anonymous ZIP; same exact SHA required')
    args=parser.parse_args();out=args.out.resolve()
    if out.exists():raise SystemExit('Refusing to overwrite an existing directory')
    if args.archive:content=args.archive.read_bytes()
    else:
        request=urllib.request.Request(URL,headers={'User-Agent':'Shiyou-A-successor-readonly-recovery'})
        with urllib.request.urlopen(request,timeout=45) as response:content=response.read(3_000_001)
    if len(content)>3_000_000 or hashlib.sha256(content).hexdigest()!=EXPECTED:
        raise SystemExit('Anonymous archive size/hash mismatch; nothing extracted')
    with zipfile.ZipFile(BytesIO(content)) as z:
        entries=z.infolist();names=[i.filename for i in entries]
        if len(names)!=len(set(names)) or len({n.casefold() for n in names})!=len(names):raise ValueError('Duplicate archive paths')
        if len(names)>300 or sum(i.file_size for i in entries)>30_000_000 or z.testzip() is not None:raise ValueError('Archive limits/CRC failure')
        for item in entries:
            p=PurePosixPath(item.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in item.filename or ':' in item.filename or item.is_dir():raise ValueError('Unsafe archive member')
            if p.suffix.lower() not in {'.json','.md','.py','.txt'}:raise ValueError('Unexpected anonymous artifact type')
            if (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive symbolic link refused')
        manifest=json.loads(z.read('BUNDLE_SHA256SUMS.json'))
        if set(names)!=set(manifest)|{'BUNDLE_SHA256SUMS.json'}:raise ValueError('Archive inventory mismatch')
        for name,digest in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=digest:raise ValueError('Member hash mismatch')
        out.mkdir(parents=True,exist_ok=False);target=out/'A2B024_READONLY';target.mkdir()
        for item in entries:
            dest=target.joinpath(*PurePosixPath(item.filename).parts)
            if not dest.resolve().is_relative_to(target.resolve()):raise ValueError('Destination escapes independent directory')
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as file:file.write(z.read(item))
    # The exact pinned read-only entry uses only stdlib and AST, never a training import.
    namespace=runpy.run_path(str(target/'verify_evidence.py'),run_name='readonly_recovery')
    result=namespace['verify'](target)
    receipt={'source_commit':COMMIT,'archive_sha256':EXPECTED,'anonymous_members':len(names),
        'readonly_check':result,'model_and_preprocessor_fits':0,'private_data_read':False,
        'installed_packages':False,'uploaded_files':False,'account_A_review_status':'NOT_YET_PERFORMED',
        'note':'B evidence consistency check only; new A must independently review and rewrite key arithmetic'}
    with (out/'RECOVERY_RECEIPT.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
    print(json.dumps(receipt,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
