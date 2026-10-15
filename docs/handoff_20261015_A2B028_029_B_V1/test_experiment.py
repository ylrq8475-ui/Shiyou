import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np,pandas as pd
from experiment_core import *
class Synthetic(unittest.TestCase):
    def test_metric_zero(self):
        self.assertEqual(official_summary(np.zeros((2,12)),np.zeros((2,12)))['official_score'],100)
    def test_metric_weights(self):
        y=np.ones((3,12));p=np.zeros_like(y);self.assertAlmostEqual(official_summary(y,p)['official_score'],100*(1-(1-2**-12)/(1+1e-6)))
    def test_prefix_no_normalizing(self):
        s=official_summary(np.ones((2,12)),np.zeros((2,12)));self.assertAlmostEqual(s['weighted_losses']['m1_to_1'],.5/(1+1e-6))
    def test_negative_prediction_rejected(self):
        with self.assertRaises(Exception):official_summary(np.ones((2,12)),-np.ones((2,12)))
    def test_combo_valid(self):
        p=pd.Series(pd.period_range('2001-01',periods=2,freq='M'));h=pd.DataFrame({'RCYL1':[10,0],'RCYL':[2,0],'YY':[3,-1],'TY':[1,0],'PL':[10,0],'BX':[50,101],'SXDL':[2,0],'XXDL':[1,0],'SCTS':[31,29]})
        v=combinations(h,p);np.testing.assert_allclose(v[0],[.8,2,5,1/3,1]);self.assertTrue(np.isnan(v[1]).all())
    def test_calendar_gap_and_cutoff(self):
        class Safe:
            _periods=staticmethod(lambda h,d:pd.to_datetime(h[d]).dt.to_period('M'))
        c={'anchors':{'well_column':'WELL_ID','date_column':'NY'}}
        h=pd.DataFrame({'WELL_ID':['SYNTH']*3,'NY':['2001-01-01','2001-04-01','2001-05-01'],'RCYL1':[10,10,10],'RCYL':[2,4,9],'YY':[1]*3,'TY':[0]*3,'PL':[1]*3,'BX':[50]*3,'SXDL':[1]*3,'XXDL':[0]*3,'SCTS':[1]*3})
        v=f0_event(h,'SYNTH',pd.Period('2001-05'),c,Safe);self.assertEqual(v['f0_C01_last_valid'],.6);self.assertEqual(v['f0_C01_mean_calendar3'],.6)
    def test_all_missing(self):
        class Safe:_periods=staticmethod(lambda h,d:pd.to_datetime(h[d]).dt.to_period('M'))
        h=pd.DataFrame(columns=['WELL_ID','NY','RCYL1','RCYL','YY','TY','PL','BX','SXDL','XXDL','SCTS'])
        v=f0_event(h,'SYNTH',pd.Period('2001-05'),{'anchors':{'well_column':'WELL_ID','date_column':'NY'}},Safe);self.assertTrue(all(np.isnan(x) for x in v.values()))
    def test_segment_collapse(self):self.assertEqual(eligible_segment_ends([1,2,5,6,9]),[2,6,9])
    def test_alpha_own_fold_label_exclusion(self):
        y=np.arange(120).reshape(10,12)+1.;p=np.full_like(y,10.);f=np.repeat(np.arange(5),2)
        a,_=cross_residual_adjust(y,p,f);changed=y.copy();changed[f==0]*=1000;b,_=cross_residual_adjust(changed,p,f);np.testing.assert_array_equal(a[f==0],b[f==0])
    def test_blend_own_fold_label_exclusion(self):
        y=np.ones((10,12));p=y*2;q=y*.9;f=np.repeat(np.arange(5),2)
        a,r=cross_blend(y,p,q,f);changed=y.copy();changed[f==0]*=1000;b,s=cross_blend(changed,p,q,f);np.testing.assert_array_equal(a[f==0],b[f==0]);self.assertEqual(r[0]['baseline_weight'],s[0]['baseline_weight'])
    def test_blend_tie_baseline(self):
        y=np.ones((10,12));f=np.repeat(np.arange(5),2);_,r=cross_blend(y,y,y,f);self.assertTrue(all(v['baseline_weight']==1 for v in r))
    def test_bridge_alignment(self):
        p=np.arange(13)[None,:];np.testing.assert_array_equal(p[:,1:13],np.arange(1,13)[None,:])
    def test_complexity_tie(self):
        v={'B0_F0_ALPHA':{'meets_retention':True,'delta':1.4},'B0_F0':{'meets_retention':True,'delta':1.35}};self.assertEqual(select_retained(v),'B0_F0')
    def test_selection_failed(self):self.assertIsNone(select_retained({'B0_F0':{'meets_retention':False,'delta':.5}}))
if __name__=='__main__':unittest.main(verbosity=2)
