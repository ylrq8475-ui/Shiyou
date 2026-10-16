import importlib.util,io,json,sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parent;sys.path[:0]=[str(root/'sources'/'B028029'),str(root)]
suite=unittest.TestSuite()
for name,path in [('B_synthetic',root/'sources'/'B028029'/'test_experiment.py'),('A_independent',root/'test_independent_r5.py')]:
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
stream=io.StringIO();out=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
result={'tests':out.testsRun,'passed':out.wasSuccessful(),'failures':len(out.failures),'errors':len(out.errors),'exact_B_tests':14,'independent_A_tests':out.testsRun-14,'model_fits':0,'preprocessor_fits':0,'real_data_read':False,'pretrained_model_loaded_or_inferred':False,'worker_alignment_tested_with_fake_tensors_only':True}
for name,text in [('SYNTHETIC_CODEX_R2.json',json.dumps(result,ensure_ascii=False,indent=2)+'\n'),('SYNTHETIC_CODEX_LOG_R2.txt',stream.getvalue())]:
    with (root/name).open('x',encoding='utf-8') as f:f.write(text)
print(json.dumps(result));sys.exit(0 if out.wasSuccessful() else 1)
