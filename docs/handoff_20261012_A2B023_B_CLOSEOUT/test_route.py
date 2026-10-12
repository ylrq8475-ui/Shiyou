"""Synthetic tests only. Never imports a model, project loader or training entry."""
import json
import inspect
import unittest
from pathlib import Path
import numpy as np
from route_core import fallback_mask, route_predictions

class RouterTests(unittest.TestCase):
    def setUp(self):
        self.raw = np.array([0., -1., np.nan, np.inf, -np.inf, 1., .2, 5.])
        self.b = np.arange(96., dtype=float).reshape(8,12)
        self.c = self.b + 500.
    def test_raw_states(self):
        np.testing.assert_array_equal(fallback_mask(self.raw), [1,1,1,1,1,0,0,0])
    def test_positive_one_is_b0(self):
        np.testing.assert_array_equal(route_predictions(self.raw,self.b,self.c)[5],self.b[5])
    def test_positive_all_months_equal_b0(self):
        np.testing.assert_array_equal(route_predictions(self.raw,self.b,self.c)[5:],self.b[5:])
    def test_fallback_all_months_equal_c1(self):
        np.testing.assert_array_equal(route_predictions(self.raw,self.b,self.c)[:5],self.c[:5])
    def test_no_mutation(self):
        b,c,r=self.b.copy(),self.c.copy(),self.raw.copy()
        out=route_predictions(self.raw,self.b,self.c);out[:]=0
        np.testing.assert_array_equal(self.b,b);np.testing.assert_array_equal(self.c,c)
        np.testing.assert_array_equal(self.raw,r)
    def test_joint_permutation(self):
        p=np.array([7,0,5,2,4,3,6,1])
        np.testing.assert_array_equal(route_predictions(self.raw[p],self.b[p],self.c[p]),route_predictions(self.raw,self.b,self.c)[p])
    def test_no_label_argument(self):
        self.assertEqual(list(inspect.signature(route_predictions).parameters),['raw_last','scaled_log_predictions','absolute_log_predictions'])
        with self.assertRaises(TypeError):route_predictions(self.raw,self.b,self.c,labels=np.zeros_like(self.b))
    def test_label_changes_cannot_enter_router(self):
        # Invented labels exist outside the API; changing them supplies no new input.
        y=np.zeros_like(self.b);a=route_predictions(self.raw,self.b,self.c);y[:]=99999
        np.testing.assert_array_equal(a,route_predictions(self.raw,self.b,self.c))
    def test_b0_perturbation_only_affects_positive(self):
        out=route_predictions(self.raw,self.b+1,self.c)-route_predictions(self.raw,self.b,self.c)
        np.testing.assert_array_equal(out[:5],np.zeros((5,12)));np.testing.assert_array_equal(out[5:],np.ones((3,12)))
    def test_c1_perturbation_only_affects_fallback(self):
        out=route_predictions(self.raw,self.b,self.c+1)-route_predictions(self.raw,self.b,self.c)
        np.testing.assert_array_equal(out[:5],np.ones((5,12)));np.testing.assert_array_equal(out[5:],np.zeros((3,12)))
    def test_reject_wrong_month_count(self):
        with self.assertRaises(ValueError):route_predictions(self.raw,self.b[:,:2],self.c[:,:2])
    def test_reject_misaligned_shape(self):
        with self.assertRaises(ValueError):route_predictions(self.raw,self.b,self.c[:-1])
    def test_reject_raw_matrix(self):
        with self.assertRaises(ValueError):fallback_mask(self.raw[:,None])
    def test_reject_empty(self):
        with self.assertRaises(ValueError):route_predictions([],np.empty((0,12)),np.empty((0,12)))
    def test_reject_nonfinite_prediction(self):
        for value in [np.nan,np.inf,-np.inf]:
            x=self.b.copy();x[0,0]=value
            with self.assertRaises(ValueError):route_predictions(self.raw,x,self.c)
    def test_reject_negative_prediction(self):
        x=self.c.copy();x[0,0]=-1
        with self.assertRaises(ValueError):route_predictions(self.raw,self.b,x)
    def test_same_arms_identity(self):
        np.testing.assert_array_equal(route_predictions(self.raw,self.b,self.b),self.b)
    def test_official_whole_well_contribution_identity(self):
        y=np.full((8,12),100.);weights=2.**-np.arange(1,13)
        loss=lambda p:np.abs(p-y)/(np.abs(p)+np.abs(y)+1e-6)*weights
        routed=route_predictions(self.raw,self.b,self.c)
        monthly=loss(routed).mean(axis=0)-loss(self.b).mean(axis=0)
        expected=(loss(self.c)[:5]-loss(self.b)[:5]).sum(axis=0)/8
        np.testing.assert_allclose(monthly,expected,atol=1e-15)
        for end in [1,2,4,12]:
            self.assertAlmostEqual(float(monthly[:end].sum()),float(expected[:end].sum()),places=14)
    def test_official_denominator_and_unscaled_weights(self):
        truth=np.full(12,100.);pred=np.full(12,200.)
        loss=np.sum(2.**-np.arange(1,13)*np.abs(pred-truth)/(np.abs(pred)+np.abs(truth)+1e-6))
        self.assertAlmostEqual(float(loss),(1-2.**-12)*100/(300+1e-6),places=14)
        self.assertLess(float(loss),1/3)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(RouterTests))
    output={'scope':'invented numbers, pure inference router only; no fitted arm or real-data route tested',
            'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'all_passed':result.wasSuccessful(),'model_fits':0,'preprocessor_fits':0,'private_data_read':False}
    path=Path(__file__).with_name('ROUTE_SYNTHETIC_RESULTS.json')
    if not path.exists():path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:assert json.loads(path.read_text(encoding='utf-8'))==output
    raise SystemExit(not result.wasSuccessful())
