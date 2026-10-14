"""No-fit fault probes on actual runner AST/functions, not a full mock training.

No competition data, forests, or preprocessors are fitted. Counts manipulated
here are dummy budget state and are never merged into actual experiment counts.
"""
import ast,hashlib,json,sys,time,unittest
from pathlib import Path
from unittest.mock import Mock
import numpy as np
import pandas as pd
import run_b2 as runner
from route_b_core import FitBudget,GateError,require,TOLERANCE

SOURCE=Path(runner.__file__).read_bytes();TREE=ast.parse(SOURCE.decode('utf-8-sig'))
NODE=next(n for n in ast.walk(TREE) if isinstance(n,ast.FunctionDef) and n.name=='fit_call')
def fit_function(budget):
    namespace={'budget':budget,'unchanged':lambda:None,'event':Mock(),'time':time}
    exec(compile(ast.Module(body=[NODE],type_ignores=[]),'runner_actual_fit_call','exec'),namespace)
    return namespace['fit_call'],namespace['event']

class FaultPaths(unittest.TestCase):
    def test_baseline_mismatch_stops_before_following_callback(self):
        assignment=next(n for n in ast.walk(TREE) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Subscript) and isinstance(x.slice,ast.Constant) and x.slice.value=='baseline_gate_passed' for x in n.targets))
        statement=next(n for n in ast.walk(TREE) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and any(isinstance(x,ast.Constant) and x.value=='BASELINE_REPRODUCTION_FAILED_STOP_BEFORE_ROUTE_B' for x in n.value.args))
        callback=Mock();env={'result':{'baseline_difference':1e-6},'TOLERANCE':TOLERANCE,'require':require}
        with self.assertRaisesRegex(GateError,'BASELINE_REPRODUCTION_FAILED'):
            exec(compile(ast.Module(body=[assignment,statement],type_ignores=[]),'runner_actual_baseline_guard','exec'),env);callback()
        callback.assert_not_called()
    def test_well_overlap_blocks_partition_even_without_row_overlap(self):
        frame=pd.DataFrame({'WELL_ID':['synthetic_a','synthetic_a','synthetic_b','synthetic_b']})
        with self.assertRaisesRegex(GateError,'WELL_ISOLATION_FAILED'):runner.validate_splits(frame,[(np.array([0,2]),np.array([1,3]))])
    def test_actual_model_fit_call_cap_blocks_callback(self):
        b=FitBudget();b.counts['model_entered']=25;fn,event=fit_function(b);callback=Mock()
        with self.assertRaisesRegex(GateError,'LOCKED_FIT_BUDGET_EXHAUSTED'):fn('model','inner_regressor',1,callback)
        callback.assert_not_called();event.assert_not_called()
    def test_actual_preprocessing_cap_blocks_callback(self):
        b=FitBudget();b.counts['preprocessor_entered']=20;fn,event=fit_function(b);callback=Mock()
        with self.assertRaisesRegex(GateError,'LOCKED_FIT_BUDGET_EXHAUSTED'):fn('preprocessor','inner_regressor',1,callback)
        callback.assert_not_called();event.assert_not_called()
    def test_actual_failed_callback_is_not_retried(self):
        b=FitBudget();fn,event=fit_function(b);callback=Mock(side_effect=RuntimeError('synthetic_fault'))
        with self.assertRaisesRegex(RuntimeError,'synthetic_fault'):fn('model','inner_regressor',1,callback)
        self.assertEqual(callback.call_count,1);self.assertEqual(b.counts['model_failed'],1);self.assertEqual(b.counts['model_completed'],0);self.assertEqual(b.counts['retries'],0)

if __name__=='__main__':unittest.main()
