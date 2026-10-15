"""Synthetic arithmetic and scope tests; no SVD, estimator or preprocessing fit."""
import unittest
from unittest.mock import patch
import numpy as np
import diagnostic_core as d

class DiagnosticTests(unittest.TestCase):
    def test_perfect_score(self):
        y=np.arange(24).reshape(2,12)
        self.assertEqual(d.official_summary(y,y)['official_score'],100)
    def test_zero_and_weights(self):
        y=np.zeros((1,12));p=np.ones((1,12))
        expected=100*(1-(4095/4096)/(1+1e-6))
        self.assertAlmostEqual(d.official_summary(y,p)['official_score'],expected)
    def test_first_month_half(self):
        y=np.zeros((1,12));p=y.copy();p[0,0]=1
        self.assertAlmostEqual(d.official_summary(y,p)['weighted_losses']['m1_to_1'],.5/(1+1e-6))
    def test_well_equal_not_fold_equal(self):
        y=np.ones((3,12));p=y.copy();p[0]=0
        a=d.official_summary(y,p)['official_score']
        self.assertAlmostEqual(a,(d.official_summary(y[:1],p[:1])['official_score']+2*100)/3)
    def test_shape_boundaries(self):
        y=np.ones((5,12));y[0,3:6]=1.1001;y[1,3:6]=.8999;y[2,3:6]=1.1;y[3,3:6]=.9;y[4]=0
        self.assertEqual(d.shape_counts(y),{'上升':1,'下降':1,'稳产':3,'含0值':1})
    def test_projection_fixed_basis(self):
        z=np.ones((2,12));z[:,0]=2
        p=d.project_oracle(z,np.zeros(12),np.eye(12),np.ones(2),1)
        self.assertTrue(np.array_equal(p[:,0],np.expm1(z[:,0])))
        self.assertTrue(np.array_equal(p[:,1:],np.zeros((2,11))))
    def test_projection_inverse_scale_clip(self):
        z=-np.ones((1,12));p=d.project_oracle(z,np.zeros(12),np.eye(12),np.array([2]),1)
        self.assertTrue((p==0).all())
    def test_alpha_does_not_use_own_fold_labels(self):
        p=np.ones((10,12));y=p*2;folds=np.repeat(np.arange(5),2)
        a,_=d.cross_residual_adjust(y,p,folds);y[:2]=100000
        b,_=d.cross_residual_adjust(y,p,folds)
        self.assertTrue(np.array_equal(a[:2],b[:2]))
    def test_alpha_zero_candidate(self):
        p=np.zeros((10,12));y=np.ones((10,12));folds=np.repeat(np.arange(5),2)
        a,records=d.cross_residual_adjust(y,p,folds)
        self.assertTrue((a==0).all());self.assertEqual(len(records),5)
    def test_contiguous_event_segment(self):
        self.assertEqual(d.eligible_segment_ends([1,2,3,20,21,40]),[3,21,40])
    def test_historical_event(self):
        hist={m:1 for m in range(1,51)}
        r=d.historical_event_counts(hist,[1,2,20,21,40],40)
        self.assertEqual(r['qualified_events'],2)
    def test_no_gap_or_refracture(self):
        hist={m:1 for m in range(1,51)};del hist[5]
        r=d.historical_event_counts(hist,[1,2,20,21,25,40],40)
        self.assertEqual(r['qualified_events'],1);self.assertEqual(r['rejected_refracture'],1)
    def test_gamma_min_five(self):
        hist=[{m:np.exp((m%3)*.2+i*.02) for m in range(1,9)} for i in range(5)]
        r=d.lagged_common_trend(hist)
        self.assertEqual(r['eligible_common_months'],7);self.assertEqual(r['adjacent_common_month_pairs'],6)
        with self.assertRaises(d.GateError):d.lagged_common_trend(hist[:4])
    def test_gamma_no_gap_bridging(self):
        hist=[{m:np.exp((m%3)*.2+i*.02) for m in [1,2,3,5,6,7,8]} for i in range(5)]
        r=d.lagged_common_trend(hist)
        self.assertEqual(r['valid_well_month_differences'],25);self.assertEqual(r['adjacent_common_month_pairs'],3)
    def test_locked_thresholds(self):
        r={'F0_combo_pass_count':1,**{f'F1_oracle_K{k}':90 for k in range(1,5)},'Dalpha_delta':1.,'Dbeta_increase_m1':.3,'Dbeta_increase_m2':0.,'Dgamma_share':.3,'Dgamma_lag1':.5}
        self.assertTrue(all(x['passed'] for x in d.decisions(r).values()))
    def test_unknown_not_zero(self):
        r={'F0_combo_pass_count':0,**{f'F1_oracle_K{k}':84 for k in range(1,5)},'Dalpha_delta':None,'Dbeta_increase_m1':0.,'Dbeta_increase_m2':0.,'Dgamma_share':.2,'Dgamma_lag1':.7}
        out=d.decisions(r);self.assertIsNone(out['D-α']['passed']);self.assertTrue(out['F1']['route_2_rejected'])

if __name__=='__main__':unittest.main(verbosity=2)
