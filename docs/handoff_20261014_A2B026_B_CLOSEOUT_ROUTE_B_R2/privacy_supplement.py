"""Scan immutable public files. No estimator or preprocessing imports/calls."""
from pathlib import Path, PurePosixPath
import argparse
import csv
import datetime
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile
import yaml

HERE = Path(__file__).resolve().parent
BASE = 'f482b55d403b8cd36e1a6e30d46a4c976b11baf4'
FOLDER = 'docs/handoff_20261014_A2B026_B_STAGE0_V1'
MISSED = {'PRIVACY_RECOVERY.json', 'PUBLICATION_PRIVACY_CHECK.json', 'SHA256SUMS.json'}

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(Path(p).read_bytes())
def dump(p,o):
    with Path(p).open('x',encoding='utf-8') as f: f.write(json.dumps(o,ensure_ascii=False,indent=2)+'\n')

def main(args):
    if (HERE/'PRIVACY_SUPPLEMENT_SCAN_RAW.json').exists():
        raise RuntimeError('SCAN_ALREADY_COMPLETED')
    repo=Path(args.repo)
    get=lambda *a:subprocess.check_output(['git',*a],cwd=repo)
    original=HERE/'received_stage0'
    original.mkdir(parents=True,exist_ok=False)
    files=get('ls-tree','-r','--name-only',BASE,'--',FOLDER).decode().splitlines()
    assert len(files)==24
    data={}
    for full in files:
        name=full[len(FOLDER)+1:]
        b=get('show',BASE+':'+full)
        (original/name).write_bytes(b)
        data[name]=b
    manifest=json.loads(data['SHA256SUMS.json'])
    assert len(manifest)==23
    for n,v in manifest.items():
        assert len(data[n])==v['bytes'] and sha_bytes(data[n])==v['sha256']
    old_scan=json.loads(data['PUBLICATION_PRIVACY_CHECK.json'])
    assert old_scan['allowlisted_files_scanned']==21
    # This list follows the unchanged builder's write/copy order, before its scan loop.
    historic=['ROLE_AND_AUTHORIZATION.md','SOURCE_RECEIPT.json','SYNTHETIC_RESULTS.json','SYNTHETIC_LOG.txt',
        'PRE_DIAGNOSTIC_LOCK.json','D0_STRUCTURE.json','D1_ZERO_MASS.json','D2_ANCHOR_COMPARISON.json',
        'D4_SMOOTH_ORACLE.json','RESULT_STAGE0.json','EVENTS.json','PRIVACY_SCAN.json','STOPPED.json','run_stage0.py',
        'diagnostics_reference.py','test_diagnostics_reference.py','PROMPT_CODEX_ORIGINAL.md',
        'THREE_ACCOUNT_ROLE_RULES_V2.md','README.md','HANDOFF_TO_CODEX.md','REPORT_B.md']
    assert len(historic)==21 and set(historic)==set(data)-MISSED
    builder=Path(args.builder)
    builder_src=builder.read_text(encoding='utf-8')
    assert builder_src.index('for p in out.iterdir():') < builder_src.index("dump(out/'PRIVACY_RECOVERY.json'") < builder_src.index("dump(out/'PUBLICATION_PRIVACY_CHECK.json'") < builder_src.index("dump(out/'SHA256SUMS.json'")
    old_lock=json.loads(data['PRE_DIAGNOSTIC_LOCK.json'])
    raw,cfg,raw_manifest=Path(args.archive),Path(args.config),Path(args.manifest)
    initial={n:sha_file(p) for n,p in [('raw_archive',raw),('private_config',cfg),('raw_manifest',raw_manifest)]}
    assert initial['raw_archive']==old_lock['raw_archive_sha256']
    assert initial['private_config']==old_lock['private_config_sha256']
    assert initial['raw_manifest']==old_lock['raw_manifest_sha256']
    c=yaml.safe_load(cfg.read_bytes())
    m=json.loads(raw_manifest.read_bytes())
    wells,months,dates=set(),set(),set()
    def decode_name(info):
        n=info.filename
        if not info.flag_bits & 0x800:
            try:n=n.encode('cp437').decode('gb18030')
            except UnicodeError:pass
        n=n.replace('\\','/')
        assert not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts
        return n
    with zipfile.ZipFile(raw) as z:
        infos={decode_name(v):v for v in z.infolist() if not v.is_dir()}
        assert len(infos)==100 and m['file_count']==len(m['files'])==100
        declared={}
        for row in m['files']:
            n=row['relative_path'].replace('\\','/')
            hits=[v for v in infos if v==n or v.endswith('/'+n)]
            assert len(hits)==1
            member=z.read(infos[hits[0]])
            assert len(member)==row['bytes'] and sha_bytes(member)==row['sha256']
            declared[n]=hits[0]
        encoding=c['data']['csv'].get('encoding','utf-8-sig')
        delimiter=c['data']['csv'].get('delimiter',',')
        chosen=[]
        for split in ('train','test'):
            chosen += [declared[n.replace('\\','/')] for n in c['data']['sources'][split]['history']]
        assert len(chosen)==len(set(chosen))==98
        well_col,date_col=c['anchors']['well_column'],c['anchors']['date_column']
        for n in chosen:
            for row in csv.DictReader(io.StringIO(z.read(infos[n]).decode(encoding)),delimiter=delimiter):
                wells.add(str(row[well_col]))
                date=str(row[date_col])
                dates.add(date)
                match=re.match(r'^(\d{4})[-/](\d{1,2})',date)
                assert match
                months.add(f'{match[1]}-{int(match[2]):02d}')
    candidates={str(x) for x in c['anchors']['eligible_event_values'] if isinstance(x,str) and len(x)>=2}
    token_groups={'real_well_identifiers':wells,'actual_calendar_months':months,
                  'actual_full_date_strings':dates,'private_candidate_strings':candidates}
    generic={
        'github_secret':r'(?i)(?:gh[pousr]_[a-z0-9]{20,}|github_'+'pat_'+r'[a-z0-9_]{20,})',
        'private_user_path':r'(?i)C:[\\/]Users[\\/][a-z0-9_. -]+',
        'private_messaging_identifier':'wx'+'id_'+r'[a-z0-9_]{5,}',
    }
    rows=[]
    started=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    for slot,n in enumerate(sorted(data),1):
        text=data[n].decode('utf-8-sig')
        hits={kind:sum(bool(re.search(r'(?<![\w])'+re.escape(t)+r'(?![\w])',text)) for t in tokens if t) for kind,tokens in token_groups.items()}
        gh={kind:int(bool(re.search(pat,text))) for kind,pat in generic.items()}
        entry={'scan_record_id':f'SUPPLEMENT-{slot:03d}','path':FOLDER+'/'+n,'bytes':len(data[n]),
               'sha256':sha_bytes(data[n]),'historic_selection_reconstructed':n in historic,
               'historic_per_file_log_existed':False,'previously_missing':n in MISSED,
               'private_token_hits':hits,'generic_sensitive_hits':gh,'result':'PASS' if sum(hits.values())+sum(gh.values())==0 else 'FAIL'}
        rows.append(entry)
        print(json.dumps(entry,ensure_ascii=True),flush=True)
    assert all(r['result']=='PASS' for r in rows)
    unchanged=initial=={n:sha_file(p) for n,p in [('raw_archive',raw),('private_config',cfg),('raw_manifest',raw_manifest)]}
    assert unchanged
    assert not any(n.startswith(('sklearn','numpy','pandas')) for n in sys.modules)
    output={'task':'A2B-026','phase':'stage0 privacy supplement','executor':'B',
        'base_commit':BASE,'old_scan_declared_count':21,'final_published_count':24,
        'original_scan_record_has_per_file_names':False,'historic_reconstruction_count':len(historic),
        'historic_builder_sha256':sha_file(builder),'missed_files':sorted(MISSED),
        'started':started,'finished':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        'raw_members_verified':100,'private_token_counts':{k:len(v) for k,v in token_groups.items()},
        'files':rows,'all_24_scanned_now':True,'all_passed':True,
        'original_publication_files_unchanged':True,'source_material_unchanged':unchanged,
        'machine_learning_modules_imported':False,'model_fit_calls':0,'preprocessor_fit_calls':0,
        'original_data_copied_or_extracted':False,'test_or_train_labels_used_for_scanning':False,
        'Codex_item_11_status':'EVIDENCE_SUPPLEMENTED_PENDING_CODEX_SIGNOFF'}
    dump(HERE/'PRIVACY_SUPPLEMENT_SCAN_RAW.json',output)
    dump(HERE/'HISTORIC_SCAN_SELECTION_RECONSTRUCTED.json',{'base_commit':BASE,'builder_sha256':sha_file(builder),
        'evidence_level':'reconstructed from local builder write order; not a recovered historic per-file log',
        'historic_21_files':historic,'missing_3_files':sorted(MISSED)})
    print(json.dumps({'summary':'24/24 PASS','fits':0,'Codex_item_11':'PENDING_SIGNOFF'}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('repo','builder','archive','config','manifest'):p.add_argument('--'+n,required=True)
    main(p.parse_args())
