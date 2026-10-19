"""Independent stdlib-only source/receipt and command routing checks. No ML."""
import ast,base64,difflib,hashlib,io,json,re,subprocess,sys,unittest,venv,zipfile,copy
from pathlib import Path
R=Path(__file__).resolve().parent;B=R/'sources/B';checks=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(name):return json.loads((B/name).read_bytes())
def record(name,ok):checks.append({'check':name,'pass':bool(ok)})
extra={};source_rows=[]
for row in json.loads((R/'EXTRA_PUBLIC_SOURCE_PRIVATE.json').read_bytes()):
    raw=base64.b64decode(row['result']['content']);blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert blob==row['result']['sha'];extra[row['name']]=raw
    source_rows.append({'name':row['name'],'commit':row['commit'],'path':row['path'],'sha256':sha(raw),'git_blob':blob,'bytes':len(raw)})
ep=R/'EXTRA_SOURCE_IDENTITY_CODEX.json'
if ep.exists():assert json.loads(ep.read_bytes())==source_rows
else:
    with ep.open('x',encoding='utf-8') as f:json.dump(source_rows,f,ensure_ascii=False,indent=2)
old=json.loads(extra['old_manifest']);new=load('NEW_CODE_PACKAGE_MANIFEST.json');cmp=load('MEMBER_SHA256_COMPARISON.json');result=load('RESULT_FIX01.json')
manifest=load('SHA256SUMS.json');files={p.name:p for p in B.iterdir() if p.is_file()}
record('20 public files',len(files)==20)
record('all other 19 files in checksum list',{Path(x['path']).name for x in manifest['files']}==set(files)-{'SHA256SUMS.json'})
for row in manifest['files']:
    p=files[Path(row['path']).name];record('manifest '+p.name,sha(p.read_bytes())==row['sha256'] and p.stat().st_size==row['bytes'])
privacy=load('PRIVACY_SCAN_RAW.json');record('one unique scan per public file',len(privacy['records'])==20 and {Path(x['path']).name for x in privacy['records']}==set(files) and len({x['record_id'] for x in privacy['records']})==20)
for row in privacy['records']:
    name=Path(row['path']).name;p=files[name]
    record('B scan result '+name,row['result']=='PASS' and sum(row['private_marker_hits'].values())==row['credential_or_private_path_hits']==0)
    if row['sha256'] is None:record('metadata final scan identity exception '+name,name in {'PRIVACY_SCAN_RAW.json','SHA256SUMS.json'})
    else:record('B scan original bytes '+name,sha(p.read_bytes())==row['sha256'] and p.stat().st_size==row['bytes'])
records=cmp['records'];record('25 unique members',len(records)==len({x['path'] for x in records})==25 and {x['path'] for x in records}==set(old['members_sha256'])==set(new['members_sha256']))
for row in records:
    n=row['path'];record('prior member binding '+n,row['old_sha256']==old['members_sha256'][n]);record('new member binding '+n,row['new_sha256']==new['members_sha256'][n])
    record('changed status '+n,row['unchanged']==(row['old_sha256']==row['new_sha256']) and (not row['unchanged'] or row['old_bytes']==row['new_bytes']))
record('exactly README changed',[x['path'] for x in records if not x['unchanged']]==['README.md'] and sum(x['unchanged'] for x in records)==24)
record('new ZIP identity size CRC',new['sha256']==result['new_code_ZIP']['sha256']=='7767b7ca28bfbf0ad9e427942c8416be35053e1e9a32b8a1eed50478fff72c6b' and new['bytes']==2455821 and new['bytes']<5_000_000_000 and new['CRC']=='PASS')
record('old code ZIP preserved identity',result['old_code_ZIP']['sha256']==old['sha256'] and result['old_code_ZIP']['preserved'])
old_readme=(B/'README_PREVIOUS.md').read_bytes();new_readme=(B/'README.md').read_bytes();record('old README exact prior public bytes',old_readme==extra['old_readme'])
record('new README exact declared ZIP member',sha(new_readme)==new['members_sha256']['README.md'])
before=old_readme.decode();after=new_readme.decode()
replacements=[('python train.py ','.venv\\Scripts\\python.exe train.py ',1),('python predict.py ','.venv\\Scripts\\python.exe predict.py ',2),('`python -m unittest -v test_033`','`.venv\\Scripts\\python.exe -m unittest -v test_033`',1)]
old_note='Linux等环境使用`.venv/bin/python`。精确复现验收在Windows Python 3.13.7进行；其他操作系统的二进制一致性未签署。'
new_note='首行`python -m venv .venv`仅用于创建环境，创建时使用Python 3.13.7；此后所有Windows命令均显式使用`.venv\\Scripts\\python.exe`，无需激活环境。Linux等环境将该解释器路径统一替换为`.venv/bin/python`。精确复现验收在Windows Python 3.13.7进行；其他操作系统的二进制一致性未签署。'
def rewrite(t):
    for a,b,count in replacements:
        assert t.count(a)==count;t=t.replace(a,b)
    assert t.count(old_note)==1;return t.replace(old_note,new_note)
record('minimal deterministic README rewrite',rewrite(before)==after)
diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='previous/README.md',tofile='FIX01/README.md'))
record('published diff equals complete original-byte text diff',diff.encode()==(B/'README_ONLY.diff').read_bytes())
def commands_good(t):
    code='\n'.join(re.findall(r'```text\s*\n(.*?)```',t,re.S));commands=[line for line in code.splitlines() if line.strip()]
    expected=['python -m venv .venv','.venv\\Scripts\\python.exe -m pip install -r requirements.txt','.venv\\Scripts\\python.exe train.py --data_dir "D:/official_data" --output "./trained"','.venv\\Scripts\\python.exe predict.py --data_dir "D:/official_data" --model "./trained/B0_prime.joblib" --output "./result.zip"','.venv\\Scripts\\python.exe predict.py --data_dir "D:/official_data" --output "./result.zip"']
    return commands==expected and '`.venv\\Scripts\\python.exe -m unittest -v test_033`' in t and '.venv/bin/python' in t and '3.13.7' in t
record('all runtime commands use one explicit interpreter',commands_good(after))
counts=load('FIT_COUNTS.json');record('B zero fits inference retry entries',all(counts[k]==0 for k in ['model_fits','preprocessor_fits','fit_entries','fit_failures','fit_retries','inference_runs','new_result_ZIPs']) and counts['training_entry_points_invoked'] is False)
record('cumulative fit counts unchanged',counts['cumulative_A2B033_model_fits_unchanged']==counts['cumulative_A2B033_preprocessor_pipeline_fits_unchanged']==7)
preserve=load('PRESERVATION_CHECK.json');record('B 81 protected files preserved',preserve['checked_existing_files']==81 and preserve['all_existing_files_unchanged'])
record('result/model/private policy identity preserved',preserve['result_ZIP_sha256']==result['result_ZIP']['sha256']=='9670e0d0bbea8e2720e53d032883f91900df65abe49b0da5c4642f755f3084de' and preserve['model_sha256']==new['members_sha256']['models/B0_prime.joblib']=='92534c2bd5f2f0d5e5167740b2a66e42c877a834dc22f1471a375c7a0e3e3ac1' and preserve['private_policy_sha256']==new['members_sha256']['runtime_policy.json']==old['members_sha256']['runtime_policy.json'])
record('prior Codex result byte identity',(B/'RECEIVED_REVIEW_CODEX.json').read_bytes()==extra['prior_review'])
record('B not self-closing or allowing upload',result['upload_approval_ready'] is False and result['platform_uploads']==0 and result['CODEX-033-S2-01']=='P1 OPEN_PENDING_A2_CODEX_READONLY_RECHECK')
record('R11 original SHA',sha(extra['r11'])=='407d536923bbbb6c6b03a2da6f686cf7e0321db6143ec63ffbc1cb64c332d414')
tree=ast.parse((B/'build_fix.py').read_bytes());imports=set()
for node in ast.walk(tree):
    if isinstance(node,ast.Import):imports.update(x.name.split('.')[0] for x in node.names)
    elif isinstance(node,ast.ImportFrom):imports.add((node.module or '').split('.')[0])
record('build imports only stdlib',imports<=sys.stdlib_module_names)
record('no fitted model loads or fitting calls in build AST',not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {'fit','fit_transform','partial_fit','predict','load'} for n in ast.walk(tree)))
authorization=(B/'AUTHORIZATION_FIX01.md').read_text(encoding='utf-8');record('B recorded exact numbered user authorization','批准执行 A2B-033-R11-FIX-01。' in authorization and '模型及预处理拟合次数均为0' in authorization)
class Synthetic(unittest.TestCase):
    def test_accept_corrected_commands(self):self.assertTrue(commands_good(after))
    def test_reject_old_commands(self):self.assertFalse(commands_good(before))
    def test_reject_bare_training_command(self):self.assertFalse(commands_good(after.replace('.venv\\Scripts\\python.exe train.py','python train.py')))
    def test_reject_one_bare_prediction(self):self.assertFalse(commands_good(after.replace('.venv\\Scripts\\python.exe predict.py','python predict.py',1)))
    def test_reject_system_pip(self):self.assertFalse(commands_good(after.replace('.venv\\Scripts\\python.exe -m pip','python -m pip')))
    def test_reject_test_interpreter_drift(self):self.assertFalse(commands_good(after.replace('`.venv\\Scripts\\python.exe -m unittest','`python -m unittest')))
    def test_reject_altered_training_arguments(self):self.assertFalse(commands_good(after.replace('--output "./trained"','--output "./different"')))
    def test_inverse_rewrite_exact(self):
        t=after.replace(new_note,old_note)
        for a,b,_ in replacements:t=t.replace(b,a)
        self.assertEqual(t,before)
    def test_fictional_zip_one_member_only(self):
        source={f'fictional_{i}.txt':f'fictional content {i}'.encode() for i in range(24)};source['README.md']=b'old fictional command';out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for n,b in source.items():z.writestr(n,b)
        out.seek(0);fixed=io.BytesIO()
        with zipfile.ZipFile(out) as a,zipfile.ZipFile(fixed,'w',zipfile.ZIP_DEFLATED) as b:
            for info in a.infolist():b.writestr(copy.copy(info),b'new fictional command' if info.filename=='README.md' else a.read(info))
        fixed.seek(0)
        with zipfile.ZipFile(fixed) as z:
            self.assertIsNone(z.testzip());self.assertEqual(z.namelist(),list(source));self.assertEqual([n for n,b in source.items() if z.read(n)!=b],['README.md'])
    def test_synthetic_checksum_detects_non_readme_change(self):
        a={'README.md':sha(b'old'),'fiction.py':sha(b'code')};b={**a,'README.md':sha(b'new'),'fiction.py':sha(b'changed code')}
        self.assertNotEqual([n for n in a if a[n]!=b[n]],['README.md'])
log=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Synthetic);run=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
with (R/'SYNTHETIC_LOG_CODEX_V2.txt').open('x',encoding='utf-8') as f:f.write(log.getvalue())
probe=R/'synthetic_command_probe_v2';probe.mkdir(exist_ok=False);venv.EnvBuilder(with_pip=False).create(probe/'.venv')
code="import json,sys;print(json.dumps(dict(prefix=sys.prefix,is_venv=(sys.prefix!=sys.base_prefix))))"
cmd="& .venv\\Scripts\\python.exe -B -c '"+code+"'"
p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],cwd=probe,capture_output=True,timeout=30);assert p.returncode==0,p.stderr.decode(errors='replace');answer=json.loads(p.stdout)
probe_ok=Path(answer['prefix']).resolve()==(probe/'.venv').resolve() and answer['is_venv'];record('actual PowerShell README relative interpreter route',probe_ok)
summary={'task':'A2B-033-R11-FIX-01','reviews_commit':'c357689ebbc7ba15b35cb9108ca867278bfdd066','source_and_receipt_checks':len(checks),'passed':sum(x['pass'] for x in checks),'failed':sum(not x['pass'] for x in checks),'checks':checks,'synthetic_tests':run.testsRun,'synthetic_successful':run.wasSuccessful(),'A_model_fits':0,'A_preprocessor_fits':0,'A_real_prediction_runs':0,'competition_data_read':False,'private_ZIPs_or_weights_read':False,'A_stdlib_check_python':sys.version.split()[0],'A_runtime_not_B_locked_training_runtime':True,'locked_interpreter_unavailable_no_model_reproduction_attempted':True,'PowerShell_explicit_README_interpreter_routing_verified':probe_ok,'probe_pip_installs':0,'scope':'Public bytes, independent static/receipt checks and pure synthetic command/ZIP tests; B private ZIP identities based on bound receipts, not A direct private extraction'}
with (R/'CHECKS_CODEX.json').open('x',encoding='utf-8') as f:json.dump(summary,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in summary.items() if k!='checks'}));assert summary['failed']==0 and run.wasSuccessful()
