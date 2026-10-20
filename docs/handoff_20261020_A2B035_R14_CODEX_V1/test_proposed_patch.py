"""Synthetic verification of A's optional patch, separate from current B audit."""
import ast,math,unittest,json
from pathlib import Path
import test_increment_source as t
R=Path(__file__).resolve().parent
ns=dict(t.BD);p=R/'patches/error_budget_R14_FIX01.py';tree=ast.parse(p.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)];exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(p),'exec'),ns)
class Tests(unittest.TestCase):
 def test_matches_official(self):
  panel=t.toy()
  for factor in [0.,.5,1.,2.,100.]:
   pred=t.A(factor*r['RCYL'] for r in panel.rows);result=ns['budget'](panel,pred,t.metadata(),t.folds(panel));expected=1-t.O.summary(panel,pred)['official_score']/100;self.assertAlmostEqual(result['total_weighted_loss'],expected)
 def test_zero_truth_and_zero_prediction(self):
  p=t.toy()
  for r in p.rows:r['RCYL']=0.
  for v in [0.,1.,100.]:
   out=ns['budget'](p,t.A([v]*len(p)),t.metadata(),t.folds(p));self.assertAlmostEqual(out['total_weighted_loss'],1-t.O.summary(p,t.A([v]*len(p)))['official_score']/100)
 def test_finite_nonnegative_rejection(self):
  p=t.toy()
  for v in [-1.,float('nan'),float('inf')]:
   pred=t.A([1.]*len(p));pred[0]=v
   with self.assertRaisesRegex(RuntimeError,'FINITE_NONNEGATIVE'):ns['weights'](p,pred)
 def test_small_group_complement_suppression(self):
  p=t.toy();out=ns['budget'](p,t.A([2.]*len(p)),t.metadata(),t.folds(p));g=out['groups']['scale_fallback'];self.assertEqual(g,[{'status':'SUPPRESSED_FAMILY_LT5','reason':'prevent reconstruction of a small remainder from cohort totals'}])
 def test_large_groups_still_report(self):
  p=t.toy();m=t.metadata()
  for i,r in enumerate(m.rows):r['scale_fallback']=i>=5
  out=ns['budget'](p,t.A([2.]*len(p)),m,t.folds(p));self.assertTrue(all(g['status']=='REPORTED' and g['wells']==5 for g in out['groups']['scale_fallback']))
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(R/'PROPOSED_PATCH_TEST_RESULT.json').write_text(json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'A_model_fits':0,'A_preprocessor_fits':0,'patch_applied_to_B':False,'current_B_release_unchanged':True},indent=2),encoding='utf-8');raise SystemExit(not r.wasSuccessful())
