import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from diagnose_030 import *
class Checks(unittest.TestCase):
    def test_natural_slope(self):
        last,slope=trend_features([1,5,100],[10,12,13],13);self.assertEqual(last,5);self.assertEqual(slope,2)
    def test_exclude_future(self):
        self.assertEqual(trend_features([1,2,999],[10,11,12],12),(2,1))
    def test_missing_slope(self):
        self.assertTrue(np.isnan(trend_features([1],[10],11)[1]))
    def test_old_value_not_slope(self):
        a,b=trend_features([3,4],[1,10],11);self.assertEqual(a,4);self.assertTrue(np.isnan(b))
    def test_zero_valid(self):
        self.assertEqual(trend_features([0,0],[10,11],12),(0,0))
    def test_n4_groups_partition(self):
        y=np.ones((3,12));y[0,3:6]=2;y[1,3:6]=.5;p=y*.8
        r=loss_decomposition(y,p);self.assertEqual(sum(r['groups'][k]['m1_to_12']['well_count'] for k in ('上升','下降','稳产')),3)
        self.assertAlmostEqual(sum(r['groups'][k]['m1_to_12']['total_loss_contribution_share'] for k in ('上升','下降','稳产')),1)
    def test_no_fit_calls(self):
        import ast
        t=ast.parse(Path(__file__).with_name('diagnose_030.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('fit','fit_transform','partial_fit') for n in ast.walk(t)))
if __name__=='__main__':unittest.main(verbosity=2)
