"""Synthetic review of pinned R5 code; no real fitting or pretrained execution."""
import ast
import contextlib
import io
import json
import math
import sys
import types
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
B=ROOT/'sources'/'B028029'
sys.path.insert(0,str(B))
import experiment_core as core
import diagnostic_core as diag

def manual(y,p,n=12):
    return sum(100*(1-sum(2**(-t)*abs(float(a)-float(b))/(abs(float(a))+abs(float(b))+1e-6) for t,(a,b) in enumerate(zip(yy[:n],pp[:n]),1))) for yy,pp in zip(y,p))/len(y)

def history_fixture():
    anchor=pd.Period('2048-01',freq='M');rows=[];anchors=[]
    for i in range(88):
        well='SYNTH_W%02d'%i
        if i<81:anchors.append({'WELL_ID':well,'anchor_period':anchor})
        for h in range(-25,13):
            if i>=81 and h>0 and (i==87 or h>(6 if i==81 else 5)):continue
            event=h==0 or (i<26 and h==-20)
            rows.append({'WELL_ID':well,'NY':str(anchor+h),'CSLB':'SYNTH_EVT' if event else 'SYNTH_NONE','RCYL':2.,'RCYL1':10.,'YY':3.,'TY':1.,'PL':10.,'BX':50.,'SXDL':2.,'XXDL':1.,'SCTS':10.})
    history=pd.DataFrame(rows)
    class Safe:
        _periods=staticmethod(lambda frame,col:pd.to_datetime(frame[col]).dt.to_period('M'))
        @staticmethod
        def segment_end_anchors(frame,cfg):
            p=Safe._periods(frame,'NY');records=[]
            for w,g in frame.groupby('WELL_ID'):
                candidates=p.loc[g.index][g.CSLB=='SYNTH_EVT'];records.append({'WELL_ID':w,'anchor_period':candidates.max()})
            return pd.DataFrame(records),{}
        @staticmethod
        def _safe_history_values(frame,well,m,cfg):
            p=Safe._periods(frame,'NY');g=frame.loc[(frame.WELL_ID==well)&(p<m)].copy();g['_period']=p.loc[g.index]
            return {'history__RCYL__last':float(g.sort_values('_period').RCYL.iloc[-1]),'history_month_count':len(g)}
        _same_feature_value=staticmethod(lambda a,b:(pd.isna(a) and pd.isna(b)) or a==b)
    cfg={'anchors':{'well_column':'WELL_ID','date_column':'NY','event_column':'CSLB','eligible_event_values':['SYNTH_EVT']}}
    return history,pd.DataFrame(anchors),cfg,Safe

class Tensor:
    def __init__(self,a):self.a=np.asarray(a)
    @property
    def shape(self):return self.a.shape
    def __getitem__(self,key):return Tensor(self.a[key])
    def clamp(self,min=0):return Tensor(np.maximum(self.a,min))
    def tolist(self):return self.a.tolist()

def worker_infer(negative=False):
    tree=ast.parse((B/'fm_worker.py').read_bytes());main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main');fn=next(x for x in main.body if isinstance(x,ast.FunctionDef) and x.name=='infer')
    class Pipeline:
        def __init__(self):self.calls=[]
        def predict(self,inputs,prediction_length):
            self.calls.append((len(inputs),prediction_length));a=np.stack([np.arange(13)+100*q for q in range(9)])
            return Tensor(np.tile(a[None,:,:],(len(inputs),1,1)) if not negative else np.full((len(inputs),9,13),-1.))
    pipeline=Pipeline();ns={'pipeline':pipeline,'torch':types.SimpleNamespace(inference_mode=contextlib.nullcontext,isfinite=lambda tensor:np.isfinite(tensor.a)),'median':4}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'frozen_worker_infer','exec'),ns)
    return ns['infer'],pipeline

class IndependentR5(unittest.TestCase):
    def test_manual_official_equal_wells(self):
        y=np.arange(36,dtype=float).reshape(3,12);p=y*.7+1
        self.assertAlmostEqual(core.official_summary(y,p)['official_score'],manual(y,p),places=12)
    def test_all_four_prefixes(self):
        y=np.ones((4,12));p=np.zeros_like(y);r=core.official_summary(y,p)
        for n in (1,2,4,12):self.assertAlmostEqual(r['weighted_losses']['m1_to_'+str(n)],1-manual(y,p,n)/100,places=14)
    def test_epsilon_exact(self):
        y=np.full((2,12),1e-8);p=np.zeros_like(y);self.assertAlmostEqual(core.official_summary(y,p)['official_score'],manual(y,p),places=13)
    def test_months_not_reversed(self):
        y=np.ones((1,12));a=y.copy();a[0,0]=0;b=y.copy();b[0,-1]=0
        la=core.official_summary(y,a)['weighted_losses']['m1_to_12'];lb=core.official_summary(y,b)['weighted_losses']['m1_to_12'];self.assertAlmostEqual(la/lb,2048.)
    def test_invalid_nan_inf_negative(self):
        for value in [np.nan,np.inf,-.1]:
            p=np.ones((2,12));p[0,0]=value
            with self.assertRaises(Exception):core.official_summary(np.ones((2,12)),p)
    def test_F0_formulas_independent(self):
        h=pd.DataFrame({'RCYL1':[20.],'RCYL':[5.],'YY':[7.],'TY':[3.],'PL':[40.],'BX':[25.],'SXDL':[6.],'XXDL':[2.],'SCTS':[14.]});p=pd.Series(pd.PeriodIndex(['2048-02'],freq='M'))
        np.testing.assert_allclose(core.combinations(h,p)[0],[.75,4.,10.,.5,14/29])
    def test_F0_zero_denominators(self):
        h=pd.DataFrame({'RCYL1':[0.],'RCYL':[0.],'YY':[0.],'TY':[0.],'PL':[0.],'BX':[0.],'SXDL':[0.],'XXDL':[0.],'SCTS':[0.]});v=core.combinations(h,pd.Series(pd.PeriodIndex(['2048-02'],freq='M')))[0]
        self.assertTrue(np.isnan(v[[0,2,3]]).all());self.assertEqual(v[4],0.)
    def test_F0_future_mutation_does_not_change(self):
        h,a,c,s=history_fixture();w=a.WELL_ID.iloc[0];m=a.anchor_period.iloc[0];before=core.f0_event(h,w,m,c,s)
        changed=h.copy();mask=(changed.WELL_ID==w)&(s._periods(changed,'NY')>=m);changed.loc[mask,'RCYL']=999.;self.assertEqual(before,core.f0_event(changed,w,m,c,s))
    def test_auxiliary_exact_cohort_counts_synthetic(self):
        h,a,c,s=history_fixture();panel,audit=core.auxiliary_panel(h,a,c,s)
        self.assertEqual(audit['events'],32);self.assertEqual(audit['rows'],343);self.assertEqual(audit['historical_rows'],312);self.assertEqual(audit['incomplete_rows'],31);self.assertEqual(audit['m1_labels'],32)
    def test_validation_well_all_events_excluded(self):
        h,a,c,s=history_fixture();panel,_=core.auxiliary_panel(h,a,c,s);validation=set(a.WELL_ID.iloc[:17]);train=panel.loc[~panel.WELL_ID.isin(validation)];self.assertFalse(set(train.WELL_ID)&validation)
    def test_aux_missing_label_blocks_locked_count(self):
        h,a,c,s=history_fixture();mask=(h.WELL_ID==a.WELL_ID.iloc[0])&(s._periods(h,'NY')==a.anchor_period.iloc[0]-15);h.loc[mask,'RCYL']=np.nan
        with self.assertRaises(Exception):core.auxiliary_panel(h,a,c,s)
    def test_aux_later_event_replaces_contaminated_window(self):
        h,a,c,s=history_fixture();mask=(h.WELL_ID==a.WELL_ID.iloc[0])&(s._periods(h,'NY')==a.anchor_period.iloc[0]-15);h.loc[mask,'CSLB']='SYNTH_EVT'
        panel,_=core.auxiliary_panel(h,a,c,s);events=set(pd.to_datetime(panel.loc[panel.WELL_ID==a.WELL_ID.iloc[0],'anchor_time']).dt.to_period('M'))
        self.assertNotIn(a.anchor_period.iloc[0]-20,events);self.assertIn(a.anchor_period.iloc[0]-15,events)
    def test_alpha_brute_force(self):
        y=np.arange(120,dtype=float).reshape(10,12)+1;p=np.full_like(y,8.);folds=np.repeat(np.arange(5),2);actual,_=core.cross_residual_adjust(y,p,folds)
        train=folds!=0;outcomes=[p[0,0]*math.exp(math.log((yy+1e-6)/(pp+1e-6))) for yy,pp in zip(y[train,0],p[train,0])];candidates=[0.]+outcomes
        values=[sum(abs(c-v)/(abs(c)+abs(v)+1e-6) for v in outcomes)/len(outcomes) for c in candidates]
        self.assertAlmostEqual(actual[0,0],candidates[min(range(len(values)),key=lambda i:values[i])],places=12)
    def test_alpha_same_horizon_only(self):
        y=np.arange(120,dtype=float).reshape(10,12)+1;p=np.ones_like(y)*8;f=np.repeat(np.arange(5),2);a,_=core.cross_residual_adjust(y,p,f);y[:,1:]*=100;b,_=core.cross_residual_adjust(y,p,f);np.testing.assert_array_equal(a[:,0],b[:,0])
    def test_alpha_zero_candidate(self):
        y=np.ones((10,12));p=np.zeros_like(y);f=np.repeat(np.arange(5),2);a,_=core.cross_residual_adjust(y,p,f);np.testing.assert_array_equal(a,p)
    def test_worker_bridge_and_median(self):
        fn,pipeline=worker_infer();out=np.asarray(fn([None]*2));np.testing.assert_array_equal(out,np.tile(np.arange(401,413),(2,1)));self.assertEqual(pipeline.calls,[(2,13)])
    def test_worker_batches_81_wells(self):
        fn,pipeline=worker_infer();out=fn([None]*81);self.assertEqual(len(out),81);self.assertEqual(pipeline.calls,[(16,13)]*5+[(1,13)])
    def test_worker_nonnegative(self):
        fn,_=worker_infer(negative=True);self.assertTrue((np.asarray(fn([None]*2))==0).all())
    def test_blend_grid_cross_source(self):
        y=np.ones((10,12));b0=y*2;fm=y*.5;f=np.repeat(np.arange(5),2);_,records=core.cross_blend(y,b0,fm,f)
        for r in records:self.assertEqual(len(r['selection_grid_scores']),11);self.assertEqual(r['selection_wells'],8);self.assertFalse(r['own_fold_labels_used'])
    def test_retention_requires_score_and_fold_count(self):
        self.assertIsNone(core.select_retained({'mock':{'meets_retention':False,'delta':1.1,'positive_folds':3}}))
    def test_preregistered_simplicity_tie(self):
        c={'B0_F0_AUG_ALPHA':{'meets_retention':True,'delta':1.4},'B0_F0':{'meets_retention':True,'delta':1.35}};self.assertEqual(core.select_retained(c),'B0_F0')
    def test_target_scale_fallback_uses_raw_last(self):
        tree=ast.parse((ROOT/'sources'/'project'/'oil_uplift'/'training.py').read_bytes());chosen=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['_target_scale','_transform_target']]
        ns={'np':np,'pd':pd,'DataContractError':RuntimeError};node=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+chosen,type_ignores=[]);ast.fix_missing_locations(node);exec(compile(node,'frozen_target_functions','exec'),ns)
        p=pd.DataFrame({'history__RCYL__last':[2.,0.,np.nan,-1.]});y=pd.Series([4.,4.,4.,4.]);np.testing.assert_array_equal(ns['_target_scale'](p,'log_ratio_last'),[2.,1.,1.,1.]);np.testing.assert_allclose(ns['_transform_target'](y,p,'log_ratio_last'),np.log1p([2.,4.,4.,4.]))

if __name__=='__main__':unittest.main(verbosity=2)
