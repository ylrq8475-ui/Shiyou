import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
snippet="import importlib.util,json,sys;print(json.dumps({'is_venv':sys.prefix!=sys.base_prefix,'prefix':sys.prefix,'marker_visible':importlib.util.find_spec('a2b033_docs_only_probe') is not None}))"
def run(exe):
    p=subprocess.run([str(exe),'-B','-c',snippet],cwd=ROOT,capture_output=True,timeout=20);assert p.returncode==0;return json.loads(p.stdout)
bare=run('python');dedicated=run(ROOT/'readme_interpreter_probe_venv/Scripts/python.exe')
assert bare['prefix']!=dedicated['prefix'] and not bare['marker_visible'] and dedicated['marker_visible'] and dedicated['is_venv']
text=(ROOT/'sources/B033s2/README.md').read_text(encoding='utf-8')
assert 'python train.py' in text and 'python predict.py' in text and 'Activate.ps1' not in text and 'activate.bat' not in text and 'source .venv/bin/activate' not in text
out={'test':'README interpreter routing counterexample','A_model_fits':0,'A_preprocessor_fits':0,'competition_data_read':False,'pip_or_dependency_download':False,'synthetic_marker_only':True,'document_installs_dependencies_into_dot_venv':True,'document_later_uses_unqualified_python':True,'document_has_no_activation_step':True,'unqualified_python_is_different_from_created_venv':bare['prefix']!=dedicated['prefix'],'unqualified_python_can_import_venv_only_marker':bare['marker_visible'],'explicit_venv_python_can_import_venv_only_marker':dedicated['marker_visible'],'public_README_SHA256':hashlib.sha256(text.encode()).hexdigest(),'finding_confirmed':True,'scope':'Counterexample to complete fresh-environment README command chain, not evidence that B actual two training runs failed','official_reference':'https://docs.python.org/3.13/library/venv.html#how-venvs-work'}
with (ROOT/'README_INTERPRETER_PROBE_CODEX.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=False))
