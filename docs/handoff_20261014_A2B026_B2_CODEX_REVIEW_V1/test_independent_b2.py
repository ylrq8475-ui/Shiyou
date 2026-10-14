"""Account A's synthetic invariants; independent arithmetic and no estimators fit."""
import ast, io, json, math, tempfile, unittest, zipfile, hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
import pandas as pd
import route_b_core as core
import run_b2 as runner
import privacy_check as scanner
from oil_uplift import a2b013_safe as safe, multistep
from oil_uplift.scoring import official_twelve_month_score
from oil_uplift.exceptions import DataContractError

ROOT=Path(__file__).resolve().parent
EPS=1e-6
def independent_score(frame,pred):
    values=[]
    for well in dict.fromkeys(frame.WELL_ID.tolist()):
        indices=[i for i,w in enumerate(frame.WELL_ID.tolist()) if w==well]
        if sorted(int(frame.horizon.iloc[i]) for i in indices)!=list(range(1,13)):raise ValueError('invalid synthetic horizons')
        loss=math.fsum((2**(-int(frame.horizon.iloc[i])))*abs(float(pred[i])-float(frame.RCYL.iloc[i]))/(abs(float(pred[i]))+abs(float(frame.RCYL.iloc[i]))+EPS) for i in indices)
        values.append(100*(1-loss))
    return math.fsum(values)/len(values)
def synthetic_panel():
    return pd.DataFrame({'WELL_ID':np.repeat(['SYNTHETIC_ALPHA','SYNTHETIC_BETA','SYNTHETIC_GAMMA'],12),'horizon':list(range(1,13))*3,'RCYL':[0.,1.,3.,0.,5.,10.,1e-15,2.,1.,1.,1.,1.]*3})
def fake_history(event_index=10):
    months=pd.period_range('2099-07',periods=24,freq='M')
    frame=pd.DataFrame({'WELL_ID':['SYNTHETIC_WELL']*24,'NY':[str(p.to_timestamp().date()) for p in months],'CSLB':['SYNTHETIC_EVENT' if i==event_index else '' for i in range(24)],'RCYL':np.arange(1.,25.)})
    config={'anchors':{'well_column':'WELL_ID','date_column':'NY','event_column':'CSLB','eligible_event_values':['SYNTHETIC_EVENT'],'first_forecast_month_offset':1},'schema':{'mapping':{'target':'RCYL'}},'features':{'history_numeric_columns':['RCYL'],'target_lags':[1,2],'rolling_windows':[3],'trend_windows':[3]}}
    return frame,config,months

class IndependentNumeric(unittest.TestCase):
    def test_official_two_implementations_against_independent_arithmetic(self):
        frame=synthetic_panel();pred=np.arange(len(frame),dtype=float)/7
        own=independent_score(frame,pred)
        self.assertAlmostEqual(core.numeric_summary(frame,pred)['official_score'],own,places=12)
        work=frame.copy();work['pred']=pred
        self.assertAlmostEqual(official_twelve_month_score(work,truth_column='RCYL',prediction_column='pred').total,own,places=12)
    def test_first_vs_last_weight_no_reversal(self):
        f=synthetic_panel().iloc[:12].copy();f.RCYL=0.
        a=np.zeros(12);a[0]=1;b=np.zeros(12);b[-1]=1
        self.assertAlmostEqual(core.numeric_summary(f,a)['official_weighted_loss']/core.numeric_summary(f,b)['official_weighted_loss'],2048.)
    def test_unnormalized_total_weight(self):
        f=synthetic_panel().iloc[:12].copy();f.RCYL=0.
        self.assertAlmostEqual(core.numeric_summary(f,np.ones(12))['official_weighted_loss'],(1-2**-12)/(1+EPS))
    def test_shuffled_rows_keep_well_score(self):
        f=synthetic_panel();p=np.arange(36,dtype=float);order=np.arange(36)[::-1]
        self.assertAlmostEqual(core.numeric_summary(f.iloc[order],p[order])['official_score'],independent_score(f,p),places=12)
    def test_missing_or_duplicate_horizon_rejected(self):
        f=synthetic_panel().iloc[:12].copy();f.loc[f.index[-1],'horizon']=11
        with self.assertRaises(core.GateError):core.numeric_summary(f,np.ones(12))
    def test_epsilon_fixed(self):
        f=synthetic_panel().iloc[:12].copy();f.RCYL=1e-7
        self.assertAlmostEqual(core.numeric_summary(f,np.zeros(12))['official_weighted_loss'],(1-2**-12)*1e-7/(1e-7+EPS))
    def test_equal_wells_not_row_mean_loss(self):
        f=synthetic_panel();p=np.zeros(36)
        self.assertAlmostEqual(core.numeric_summary(f,p)['official_score'],math.fsum(independent_score(f.iloc[s:s+12],p[s:s+12]) for s in (0,12,24))/3)
    def test_positive_well_conditional_weights(self):
        f=synthetic_panel().iloc[:24].copy();f.loc[f.index[:12],'RCYL']=0.;f.loc[f.index[0],'RCYL']=1.;f.loc[f.index[12:],'RCYL']=2.
        p=np.ones(24);loss1=0.;loss2=1/(3+EPS)
        self.assertAlmostEqual(core.positive_inner_loss(f,p)[0],(loss1+loss2)/2)
    def test_zero_only_inner_fold_stops(self):
        f=synthetic_panel().iloc[:12].copy();f.RCYL=0.
        with self.assertRaises(core.GateError):core.positive_inner_loss(f,np.ones(12))
    def test_tau_equal_three_fold_scalar_not_pooled(self):
        values=[.1,.2,.6];ell=math.fsum(values)/3
        self.assertAlmostEqual(core.tau_from_folds(values)[0],(1-ell)/(2-ell))
    def test_strict_threshold_keep_equal_B0(self):
        p,mask=core.route_prediction([5.,6.,7.],[.4,.41,.3],.4)
        np.testing.assert_array_equal(p,[5.,0.,7.]);np.testing.assert_array_equal(mask,[False,True,False])
    def test_invalid_probability_and_prediction_stop(self):
        for p,q in [([np.inf],[.1]),([1.],[np.nan]),([-1.],[.2]),([1.],[1.1])]:
            with self.subTest(p=p,q=q),self.assertRaises(core.GateError):core.route_prediction(p,q,.4)
    def test_exact_zero_label_not_near_zero(self):
        np.testing.assert_array_equal(core.zero_labels([0.,-0.,1e-20]),[1,1,0])
    def test_no_outer_labels_in_inner_tau_callsite(self):
        text=(ROOT/'sources/B/run_b2.py').read_text(encoding='utf-8-sig');tree=ast.parse(text)
        calls=[ast.unparse(n) for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='positive_inner_loss']
        self.assertEqual(calls,['positive_inner_loss(train.iloc[iva], ip)'])

class IndependentWindows(unittest.TestCase):
    def test_anchor_month_and_future_do_not_change_features(self):
        frame,cfg,months=fake_history();base=safe._safe_history_values(frame,'SYNTHETIC_WELL',months[10],cfg)
        changed=frame.copy();changed.loc[changed.index[10:],'RCYL']=9999.
        new=safe._safe_history_values(changed,'SYNTHETIC_WELL',months[10],cfg)
        self.assertEqual(base,new);self.assertEqual(base['history__RCYL__last'],10.)
    def test_natural_months_across_year_and_twelve_targets(self):
        frame,cfg,months=fake_history(5);tables=multistep.MultiSourceTables(frame,pd.DataFrame(),pd.DataFrame(),None)
        panel,audit,anchors=safe._build_train_panel(tables,cfg)
        self.assertEqual(panel.horizon.tolist(),list(range(1,13)))
        self.assertEqual(panel.RCYL.tolist(),list(np.arange(7.,19.)))
        self.assertEqual(anchors.anchor_period.iloc[0],pd.Period('2099-12','M'))
    def test_consecutive_months_segment_last_and_no_first_plan(self):
        frame,cfg,months=fake_history();frame.loc[9,'CSLB']='SYNTHETIC_EVENT'
        anchors,audit=safe.segment_end_anchors(frame,cfg)
        self.assertEqual(audit['merged_event_segments'],1);self.assertEqual(anchors.anchor_period.iloc[0],months[10])
    def test_duplicate_well_month_stops(self):
        frame,cfg,_=fake_history();frame=pd.concat([frame,frame.iloc[[4]]],ignore_index=True)
        with self.assertRaises(DataContractError):safe.segment_end_anchors(frame,cfg)
    def test_missing_target_month_excluded(self):
        frame,cfg,months=fake_history();frame=frame.drop(index=13)
        targets,reason=multistep._training_window_targets(frame,'SYNTHETIC_WELL',[months[10]+i for i in range(1,13)],cfg)
        self.assertIsNone(targets);self.assertEqual(reason,'missing_month')
    def test_nonfinite_target_excluded(self):
        frame,cfg,months=fake_history();frame.loc[13,'RCYL']=np.inf
        targets,reason=multistep._training_window_targets(frame,'SYNTHETIC_WELL',[months[10]+i for i in range(1,13)],cfg)
        self.assertIsNone(targets);self.assertEqual(reason,'nonfinite_target')

class IndependentPrivacy(unittest.TestCase):
    def test_clean_document_passes(self):
        tokens={'well':{'SYNTHETIC_PRIVATE_WELL'},'date':{'2099-01-01'},'month':{'2099-01'},'candidate':{'SYNTHETIC_PRIVATE_CODE'}}
        self.assertEqual(scanner.scan(b'{"anonymous_count": 12}',tokens)['result'],'PASS')
    def test_each_marker_type_blocks(self):
        tokens={'well':{'SYNTHETIC_PRIVATE_WELL'},'date':{'2099-01-01'},'month':{'2099-01'},'candidate':{'SYNTHETIC_PRIVATE_CODE'}}
        for group,values in tokens.items():
            with self.subTest(group=group),self.assertRaises(AssertionError):scanner.scan(('"'+next(iter(values))+'"').encode(),tokens)
    def test_credential_or_private_path_blocks(self):
        for text in ['ghp_'+'A'*25,r'C:\Users\FAKE_ACCOUNT\file']:
            with self.subTest(text=text),self.assertRaises(AssertionError):scanner.scan(text.encode(),{'well':set(),'date':set(),'month':set(),'candidate':set()})

if __name__=='__main__':unittest.main()
