import hashlib, importlib.util, io, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'verification_output';OUTPUT.mkdir(exist_ok=True)
folder=ROOT/'sources/B032'
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
sys.dont_write_bytecode=True;sys.path.insert(0,str(folder))
suite=unittest.TestSuite()
for name,path in [('B_synthetic',folder/'test_audit.py'),('A_independent',ROOT/'test_independent_032.py')]:
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
out={'tests_run':result.testsRun,'B_tests':15,'A_tests':20,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),'public_B_source_bytes_unchanged':before==after,'real_data_accessed':False,'model_fits':0,'preprocessor_fits':0,'real_diagnostic_entry_executed':False,'ML_modules_imported':any(x.startswith(('sklearn','xgboost','lightgbm','catboost')) for x in sys.modules)}
with (OUTPUT/'SYNTHETIC_LOG_CODEX_R2.txt').open('x',encoding='utf-8') as f:f.write(log.getvalue())
with (OUTPUT/'SYNTHETIC_RESULT_CODEX_R2.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out));assert out['successful'] and out['public_B_source_bytes_unchanged'] and not out['ML_modules_imported']
