"""A2 synthetic oracles: no real data, fitted models or model deserialization."""
import hashlib,json,math,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;S=HERE/'deploy_bundle/source'
sys.dont_write_bytecode=True;sys.path.insert(0,str(S));sys.path.insert(0,str(S/'src'))
import numpy as np,pandas as pd
from deployment_core import DeploymentError,inverse_prediction,predict_system
from predict import canonical_reference
from test_deployment import frame,artifact
from oil_uplift import a2b013_safe as safe
from oil_uplift.multistep import MultiSourceTables
from oil_uplift.scoring import official_twelve_month_score
from oil_uplift.exceptions import DataContractError,ConfigurationError
def oracle(truth,prediction):
    return 100*(1-sum(2**(-t)*abs(p-y)/(abs(p)+abs(y)+1e-6) for t,(y,p) in enumerate(zip(truth,prediction),1)))
def score_frame(y,p):return pd.DataFrame({'WELL_ID':['SYNTH_A2']*12,'horizon':range(1,13),'y':y,'p':p})
def config():return {'anchors':{'well_column':'WELL_ID','date_column':'NY','event_column':'CSLB','eligible_event_values':['SYNTHETIC_EVENT'],'first_forecast_month_offset':1},'schema':{'mapping':{'target':'RCYL'}},'features':{'target_lags':[1,2],'rolling_windows':[3],'trend_windows':[3]}}
def history():
    periods=pd.period_range('2023-11','2025-03',freq='M')
    return pd.DataFrame({'WELL_ID':['SYNTH_A2']*len(periods),'NY':[p.strftime('%Y/%m/01') for p in periods],
                        'RCYL':np.arange(1,len(periods)+1,dtype=float),'CSLB':['SYNTHETIC_EVENT' if str(p) in {'2023-12','2024-01','2024-02'} else '' for p in periods]})
class IndependentTests(unittest.TestCase):
    def test_first_month_epsilon_hand_calculation(self):
        y=[0.]*12;p=[1.]+[0.]*11
        self.assertAlmostEqual(official_twelve_month_score(score_frame(y,p),truth_column='y',prediction_column='p').total,100*(1-.5/(1+1e-6)),places=12)
    def test_unnormalized_constant_ratio(self):
        y=[2.]*12;p=[4.]*12
        self.assertAlmostEqual(oracle(y,p),100*(1-(1-2**-12)*2/(6+1e-6)),places=12)
        self.assertAlmostEqual(official_twelve_month_score(score_frame(y,p),truth_column='y',prediction_column='p').total,oracle(y,p),places=12)
    def test_zero_zero(self):self.assertEqual(oracle([0.]*12,[0.]*12),100)
    def test_well_equal_aggregation_and_row_shuffle(self):
        a=score_frame([1.]*12,[1.]*12);b=score_frame([2.]*12,[4.]*12);b.WELL_ID='SYNTH_B2'
        f=pd.concat([a,b]).iloc[::-1]
        self.assertAlmostEqual(official_twelve_month_score(f,truth_column='y',prediction_column='p').total,(100+oracle([2.]*12,[4.]*12))/2,places=12)
    def test_nan_inf_rejected(self):
        for v in [float('nan'),float('inf')]:
            with self.assertRaises(DataContractError):official_twelve_month_score(score_frame([1.]*12,[v]+[1.]*11),truth_column='y',prediction_column='p')
    def test_wrong_epsilon_rejected(self):
        with self.assertRaises(ConfigurationError):official_twelve_month_score(score_frame([1.]*12,[1.]*12),truth_column='y',prediction_column='p',epsilon=1e-5)
    def test_positive_arms_route_all_months(self):
        for raw in [1.,.25,10.]:
            routed,arms=predict_system(artifact(),frame(raw))
            np.testing.assert_array_equal(routed,arms['B0']);np.testing.assert_allclose(routed,2*raw)
    def test_invalid_raw_arms_route_all_months(self):
        for raw in [0.,-1.,float('nan'),float('inf')]:
            routed,arms=predict_system(artifact(),frame(raw));np.testing.assert_array_equal(routed,arms['C1']);np.testing.assert_allclose(routed,5.)
    def test_inverse_fallback_labels_same_given_z(self):
        z=np.log1p([2.,3.,4.]);raw=np.array([0.,np.nan,-1.])
        np.testing.assert_array_equal(inverse_prediction(z,raw,'B0'),inverse_prediction(z,raw,'C1'))
    def test_mixed_groups_score_contribution_identity(self):
        y=[2.]*12;b=[4.]*12;c=[1.]*12
        total_delta=((oracle(y,c)+oracle(y,b))/2)-oracle(y,b)
        self.assertAlmostEqual(total_delta,(oracle(y,c)-oracle(y,b))/2,places=12)
    def test_segment_end_across_year_and_leap_month(self):
        h=history();h.loc[h.NY=='2024/02/01','NY']='2024/02/29'
        anchors,audit=safe.segment_end_anchors(h,config());self.assertEqual(str(anchors.anchor_period.iloc[0]),'2024-02');self.assertEqual(audit['merged_event_segments'],1)
    def test_anchor_and_future_values_excluded(self):
        h=history();a=pd.Period('2024-02','M');before=safe._safe_history_values(h,'SYNTH_A2',a,config())
        changed=h.copy();changed.loc[pd.to_datetime(changed.NY).dt.to_period('M')>=a,'RCYL']=99999.
        after=safe._safe_history_values(changed,'SYNTH_A2',a,config())
        self.assertEqual(before,after);self.assertEqual(before['history__RCYL__last'],3.)
    def test_train_window_next_12_natural_months(self):
        h=history();panel,audit,anchors=safe._build_train_panel(MultiSourceTables(h,pd.DataFrame(),pd.DataFrame(),None),config())
        self.assertEqual(panel.horizon.tolist(),list(range(1,13)))
        np.testing.assert_array_equal(panel.RCYL.to_numpy(),np.arange(5.,17.))
    def test_duplicate_well_month_rejected(self):
        h=history();h=pd.concat([h,h.iloc[:1]],ignore_index=True)
        with self.assertRaises(DataContractError):safe.segment_end_anchors(h,config())
    def test_date_padding_semantics_and_collision(self):
        f=pd.DataFrame({'WELL_ID':['SYNTH_A2']*2,'NY':['2024/2/29','2025/1/1']});normalized,n=canonical_reference(f)
        self.assertEqual(n,2);self.assertEqual(normalized.NY.tolist(),['2024/02/29','2025/01/01'])
        duplicate=pd.DataFrame({'WELL_ID':['SYNTH_A2']*2,'NY':['2024/2/29','2024/02/29']})
        with self.assertRaises(DeploymentError):canonical_reference(duplicate)
if __name__=='__main__':
    import io,contextlib,joblib
    stream=io.StringIO();fit_calls=[];loads=[]
    def reject(*a,**k):loads.append(True);raise AssertionError('MODEL_LOAD_FORBIDDEN')
    joblib.load=reject
    def guard(f,e,a):
        if e=='call' and 'sklearn' in f.f_code.co_filename.lower() and f.f_code.co_name in {'fit','fit_transform','partial_fit','_fit'}:fit_calls.append(True);raise AssertionError('REAL_FIT_FORBIDDEN')
    sys.setprofile(guard)
    try:
        with contextlib.redirect_stderr(stream),contextlib.redirect_stdout(stream):r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentTests))
    finally:sys.setprofile(None)
    result={'tests':r.testsRun,'passed':r.wasSuccessful(),'failures':len(r.failures),'errors':len(r.errors),'real_fits':len(fit_calls),'real_model_loads':len(loads),'only_synthetic_values_used':True}
    with (HERE/'A2_INDEPENDENT_SYNTHETIC_RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    with (HERE/'A2_INDEPENDENT_SYNTHETIC_LOG.txt').open('x',encoding='utf-8') as f:f.write(stream.getvalue())
    print(json.dumps(result));raise SystemExit(not r.wasSuccessful())
