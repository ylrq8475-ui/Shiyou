"""Replay A arithmetic and pure synthetic tests from the self-contained audit package."""
import argparse, hashlib, json, pathlib, subprocess, sys, tempfile, zipfile

def main(out):
    root=pathlib.Path(__file__).resolve().parent
    for name,record in json.loads((root/'INNER_SHA256SUMS.json').read_bytes()).items():
        data=(root/name).read_bytes()
        assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256'],name
    source=root/'inputs/B_ANONYMOUS_EVIDENCE.zip'
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='c26a1c87c0fdb4d96b4a3251aa13702ab7aeb258517edd2614029cf0d2393d50'
    out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='a24_readonly_') as tmp:
        bundle=pathlib.Path(tmp)/'bundle';bundle.mkdir()
        with zipfile.ZipFile(source) as z:
            assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))
            for item in z.infolist():
                p=pathlib.PurePosixPath(item.filename)
                assert not p.is_absolute() and '..' not in p.parts and '\\' not in item.filename and ':' not in item.filename
                assert (item.external_attr >> 16) & 0o170000 != 0o120000
                target=bundle/p
                if item.is_dir():target.mkdir(parents=True,exist_ok=True)
                else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
        commands=[['independent_audit.py','--bundle',str(bundle),'--out',str(out/'INDEPENDENT_RESULT_A.json')],['synthetic_checks_a.py','--bundle',str(bundle),'--out',str(out/'synthetic')]]
        for args in commands:
            proc=subprocess.run([sys.executable,'-B',str(root/args[0]),*args[1:]],capture_output=True,text=True)
            (out/(pathlib.Path(args[0]).stem+'.log')).write_text(proc.stdout+proc.stderr,encoding='utf-8')
            if proc.returncode:raise RuntimeError('readonly check failed: '+args[0])
    result=json.loads((out/'INDEPENDENT_RESULT_A.json').read_bytes())
    assert result==json.loads((root/'INDEPENDENT_RESULT_A.json').read_bytes())
    print(json.dumps(dict(status='PASS',arithmetic_checks=result['checks'],same_arithmetic_result=True,real_model_fits=0,real_preprocessor_fits=0,private_data_read=False)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);main(p.parse_args().out.resolve())
