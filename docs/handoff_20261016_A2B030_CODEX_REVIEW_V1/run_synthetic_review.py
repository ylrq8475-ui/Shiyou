"""Run exact B tests and independent synthetic checks; no real execution entry."""
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'sources'/'B030')]
suite=unittest.TestSuite()
for name,path in [('B030_synthetic',ROOT/'sources'/'B030'/'test_030.py'),('independent_030',ROOT/'test_independent_030.py')]:
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
record={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'model_fits':0,'preprocessor_fits':0,'real_data_read':False,'exact_B_tests':7,'independent_tests':result.testsRun-7}
for name,content in [('SYNTHETIC_CODEX.json',json.dumps(record,ensure_ascii=False,indent=2)+'\n'),('SYNTHETIC_CODEX_LOG.txt',stream.getvalue())]:
    with (ROOT/name).open('x',encoding='utf-8') as file:file.write(content)
print(json.dumps(record));sys.exit(0 if result.wasSuccessful() else 1)
