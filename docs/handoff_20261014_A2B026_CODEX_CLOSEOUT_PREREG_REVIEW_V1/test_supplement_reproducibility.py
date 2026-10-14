"""Run the unchanged B scanner with invented data and synthetic Git snapshots."""
import argparse, contextlib, csv, hashlib, importlib.util, io, json, os
import subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True

def digest(b):return hashlib.sha256(b).hexdigest()
def put(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as out:out.write(payload)
def encoded(obj):return json.dumps(obj,ensure_ascii=False).encode()

class ScannerChecks(unittest.TestCase):
    def run_fixture(self,kind):
        parent=ROOT/'synthetic_fixtures';parent.mkdir(exist_ok=True)
        work=Path(tempfile.mkdtemp(prefix='scanner_',dir=parent))
        config={'data':{'csv':{'encoding':'utf-8','delimiter':','},'sources':{
                    'train':{'history':[f'history/{i:03d}.csv' for i in range(88)]},
                    'test':{'history':[f'history/{i:03d}.csv' for i in range(88,98)]}}},
                'anchors':{'well_column':'WELL_ID','date_column':'NY','eligible_event_values':['SYNTHETIC_EVENT']}}
        archive=work/'invented_fixture.zip';manifest_entries=[]
        with zipfile.ZipFile(archive,'x') as z:
            for i in range(100):
                name=f'history/{i:03d}.csv' if i<98 else f'metadata/{i:03d}.csv'
                # Invented identifiers/dates only; no production labels are supplied.
                payload=f'WELL_ID,NY\nSYNTHETIC_WELL_{i:03d},2001/02/01\n'.encode()
                z.writestr(name,payload)
                manifest_entries.append({'relative_path':name,'bytes':len(payload),'sha256':digest(payload)})
        cfg=work/'invented_config.yaml';put(cfg,yaml.safe_dump(config).encode())
        mf=work/'invented_manifest.json';put(mf,encoded({'file_count':100,'files':manifest_entries}))
        base_names=list(json.loads((ROOT/'sources/B/PRIVACY_SUPPLEMENT_SCAN_RAW.json').read_bytes())['files'])
        names=[Path(v['path']).name for v in base_names]
        data={n:b'Synthetic public review fixture.\n' for n in names if n!='SHA256SUMS.json'}
        data['PUBLICATION_PRIVACY_CHECK.json']=encoded({'allowlisted_files_scanned':21})
        data['PRE_DIAGNOSTIC_LOCK.json']=encoded({'raw_archive_sha256':digest(archive.read_bytes()),
                   'private_config_sha256':digest(cfg.read_bytes()),'raw_manifest_sha256':digest(mf.read_bytes())})
        if kind=='identifier':data['README.md']=b'SYNTHETIC_WELL_000\n'
        if kind=='credential':data['README.md']=('gh'+'p_'+'a'*24).encode()
        sums={n:{'bytes':len(p),'sha256':digest(p)} for n,p in data.items()}
        if kind=='hash_mismatch':sums['README.md']['sha256']='0'*64
        data['SHA256SUMS.json']=encoded(sums)
        repo=work/'repo';repo.mkdir()
        env=os.environ.copy();env.update(GIT_AUTHOR_NAME='Synthetic audit',GIT_AUTHOR_EMAIL='synthetic@example.invalid',
                    GIT_COMMITTER_NAME='Synthetic audit',GIT_COMMITTER_EMAIL='synthetic@example.invalid')
        def git(*args):
            r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,env=env,check=True)
            return r.stdout.decode().strip()
        git('init','--initial-branch=synthetic')
        folder='docs/handoff_20261014_A2B026_B_STAGE0_V1'
        for n,p in data.items():put(repo/folder/n,p)
        git('add','--',folder);git('commit','-m','Synthetic privacy scanner fixture')
        base=git('rev-parse','HEAD')
        builder=work/'invented_builder.py'
        put(builder,b"for p in out.iterdir():\n    pass\ndump(out/'PRIVACY_RECOVERY.json', {})\ndump(out/'PUBLICATION_PRIVACY_CHECK.json', {})\ndump(out/'SHA256SUMS.json', {})\n")
        code=ROOT/'sources/B/privacy_supplement.py'
        spec=importlib.util.spec_from_file_location('synthetic_scanner_'+kind,code)
        scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
        # Bind invented fixtures in memory; the B source file stays byte-identical.
        scanner.BASE=base;scanner.HERE=work/'output';scanner.HERE.mkdir()
        args=argparse.Namespace(repo=repo,builder=builder,archive=archive,config=cfg,manifest=mf)
        with contextlib.redirect_stdout(io.StringIO()):scanner.main(args)
        return json.loads((scanner.HERE/'PRIVACY_SUPPLEMENT_SCAN_RAW.json').read_bytes())

    def test_all_24_rows_bound_and_zero_fit(self):
        r=self.run_fixture('clean')
        self.assertEqual(len(r['files']),24)
        self.assertTrue(r['all_passed'])
        self.assertEqual(sum(v['previously_missing'] for v in r['files']),3)
        self.assertEqual(r['private_token_counts']['real_well_identifiers'],98)
        self.assertFalse(r['machine_learning_modules_imported'])
        self.assertEqual((r['model_fit_calls'],r['preprocessor_fit_calls']),(0,0))
    def test_private_identifier_rejected(self):
        with self.assertRaises(AssertionError):self.run_fixture('identifier')
    def test_credential_pattern_rejected(self):
        with self.assertRaises(AssertionError):self.run_fixture('credential')
    def test_changed_public_hash_rejected(self):
        with self.assertRaises(AssertionError):self.run_fixture('hash_mismatch')

if __name__=='__main__':
    log=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(ScannerChecks)
    out=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    result={'account':'Codex（账户A2）','unmodified_scanner_sha256':digest((ROOT/'sources/B/privacy_supplement.py').read_bytes()),
            'tests':out.testsRun,'passed':out.wasSuccessful(),'failures':len(out.failures),'errors':len(out.errors),
            'data':'invented fixtures only','real_competition_data_read':False,'real_fits':0,
            'B_source_modified':False,'synthetic_fixture_bindings_changed_in_memory_only':True}
    put(ROOT/'SCANNER_SYNTHETIC_REVIEW.json',encoded(result))
    put(ROOT/'SCANNER_SYNTHETIC_LOG.txt',log.getvalue().encode())
    print(json.dumps(result,ensure_ascii=True))
    if not out.wasSuccessful():print(log.getvalue());raise SystemExit(1)
