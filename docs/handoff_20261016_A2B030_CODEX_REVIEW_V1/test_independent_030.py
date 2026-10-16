"""Independent, competition-data-free tests of the exact B030 implementation."""
import ast
import hashlib
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pandas as pd

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
B=ROOT/'sources'/'B030'
spec=importlib.util.spec_from_file_location('audit_B030',B/'diagnose_030.py')
impl=importlib.util.module_from_spec(spec);spec.loader.exec_module(impl)

def manual(y,p,n=12):
    return [sum((2.0**(-t))*abs(float(pp)-float(yy))/(abs(float(pp))+abs(float(yy))+1e-6)
                for t,(yy,pp) in enumerate(zip(row[:n],prediction[:n]),1)) for row,prediction in zip(y,p)]

class FakeZip:
    def __init__(self,blobs): self.blobs=blobs
    def read(self,name): return self.blobs[name]

def fixture(multiple=False,consecutive=False,late_plan=False,change_test=False):
    m=pd.Period('2044-02',freq='M');records=[];anchors=[]
    train=['SYNTH_T%03d'%i for i in range(81)];test=['SYNTH_X%02d'%i for i in range(10)]
    for i,well in enumerate(train):
        anchors.append({'WELL_ID':well,'anchor_period':m})
        for offset in (-5,-3,-2,-1,0,1):
            event='EVT_SYNTH' if offset==0 or (i==0 and multiple and offset==-3) or (i==0 and consecutive and offset==-1) else 'NONE_SYNTH'
            records.append({'WELL_ID':well,'NY':str(m+offset),'CSLB':event,
                            'CCJHWND':float(offset+7) if offset<0 else 9999.,'CCJND':np.nan,
                            'CCBHJND':np.nan,'CCYND':float(offset+11) if offset<0 else 9999.})
    fields=json.loads((B/'FIELD_DICTIONARY_N1.json').read_bytes())
    planrows=[];layerrows=[]
    for well in train+test:
        row={v['field']:1 for v in fields['plan']};row['井号']=well
        row['完工日期']=str((m+(1 if late_plan and well==train[0] else -1)).start_time.date())
        if change_test and well in test: row['完工日期']=str((m+30).start_time.date())
        planrows.append(row)
        layer={v['field']:1 for v in fields['layer']};layer['WELL_ID']=well;layerrows.append(layer)
    blobs={'plan.csv':pd.DataFrame(planrows).to_csv(index=False).encode('utf-8'),
           'layer.csv':pd.DataFrame(layerrows).to_csv(index=False).encode('utf-8')}
    for i,well in enumerate(test):
        rows=[{'WELL_ID':well,'NY':str(m+k),'CSLB':'EVT_SYNTH' if k==0 else 'NONE_SYNTH'} for k in (-1,0,1)]
        blobs['test%d.csv'%i]=pd.DataFrame(rows).to_csv(index=False).encode()
    store=SimpleNamespace(before={'archive':'SYNTHETIC','manifest':'SYNTHETIC'},declared={k:k for k in blobs},members={k:k for k in blobs},zip=FakeZip(blobs))
    cfg={'anchors':{'well_column':'WELL_ID','date_column':'NY','event_column':'CSLB','eligible_event_values':['EVT_SYNTH']},'data':{'csv':{'encoding':'utf-8','delimiter':','},'sources':{'train':{'plan':['plan.csv'],'layer':['layer.csv']},'test':{'plan':['plan.csv'],'layer':['layer.csv'],'history':['test%d.csv'%i for i in range(10)]}}}}
    safe=SimpleNamespace(_periods=lambda frame,column:pd.to_datetime(frame[column]).dt.to_period('M'))
    return store,pd.DataFrame(records),pd.DataFrame(anchors),cfg,safe

def run_prepare(**kwargs):
    args=fixture(**kwargs);original=impl.digest;observed=[];reader=pd.read_csv
    def digest(p):
        if Path(p).name=='INSTRUCTION_ORIGINAL_R6.md':return hashlib.sha256((ROOT/'sources'/'instructions'/'R6.md').read_bytes()).hexdigest()
        return original(p)
    def tracked(*a,**k):
        observed.append(k.get('usecols'));return reader(*a,**k)
    folder=ROOT/'synthetic_runtime';folder.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='synthetic-',dir=folder) as parent:
        with patch.object(impl,'digest',digest),patch.object(impl.pd,'read_csv',tracked):
            result=impl.prepare(Path(parent)/'new_output',*args)
    return result,observed

class Independent030(unittest.TestCase):
    def test_calendar_missing_middle(self): self.assertEqual(impl.trend_features([2,8],[10,12],13),(8.,3.))
    def test_future_and_anchor_excluded(self): self.assertEqual(impl.trend_features([2,4,900,999],[10,11,12,13],12),(4.,2.))
    def test_unsorted_last_is_temporal(self): self.assertEqual(impl.trend_features([8,2],[12,10],13),(8.,3.))
    def test_last_uses_all_legal_history(self):
        last,slope=impl.trend_features([7],[1],20);self.assertEqual(last,7);self.assertTrue(math.isnan(slope))
    def test_two_values_required(self): self.assertTrue(math.isnan(impl.trend_features([3,np.nan],[10,11],12)[1]))
    def test_nonfinite_excluded(self): self.assertEqual(impl.trend_features([2,np.inf,6,np.nan],[10,11,12,13],13),(6.,2.))
    def test_zero_not_missing(self): self.assertEqual(impl.trend_features([0,0],[10,11],12),(0.,0.))
    def test_no_interpolation(self): self.assertEqual(impl.trend_features([0,np.nan,6],[10,11,12],13),(6.,3.))
    def test_cross_year(self):
        x=[pd.Period('2043-12',freq='M').ordinal,pd.Period('2044-02',freq='M').ordinal]
        self.assertEqual(impl.trend_features([3,9],x,x[-1]+1),(9.,3.))
    def test_negative_value_not_silently_reinterpreted(self): self.assertEqual(impl.trend_features([-2,0],[10,11],12),(0.,2.))
    def test_all_invalid(self): self.assertTrue(all(math.isnan(x) for x in impl.trend_features([np.nan,np.inf],[10,11],12)))
    def test_lower_three_month_boundary(self): self.assertEqual(impl.trend_features([500,2,6],[9,10,12],13),(6.,2.))
    def test_metric_manual_all_groups_and_prefixes(self):
        y=np.ones((5,12));y[0,3:6]=2.;y[1,3:6]=.5;y[2,0]=0.;p=y*.7+.2
        actual=impl.loss_decomposition(y,p)
        a=y[:,:2].mean(1);b=y[:,3:6].mean(1)
        masks={'上升':b>1.1*a,'下降':b<.9*a,'稳产':~((b>1.1*a)|(b<.9*a)),'含0值':(y==0).any(1)}
        for n in (1,2,4,12):
            losses=np.array(manual(y,p,n));total=losses.sum()
            for key,mask in masks.items():
                r=actual['groups'][key]['m1_to_'+str(n)];chosen=losses[mask]
                self.assertEqual(r['well_count'],int(mask.sum()))
                if len(chosen):
                    self.assertAlmostEqual(r['mean_per_well_score'],100*(1-chosen.mean()),places=12)
                    self.assertAlmostEqual(r['total_loss_contribution_share'],chosen.sum()/total,places=12)
    def test_epsilon(self):
        y=np.full((1,12),1e-8);p=np.zeros_like(y);r=impl.loss_decomposition(y,p)['groups']['稳产']['m1_to_12']
        self.assertAlmostEqual(r['mean_per_well_weighted_loss'],sum(manual(y,p)),places=15)
    def test_weights_not_normalized(self):
        y=np.ones((1,12));p=np.zeros_like(y);r=impl.loss_decomposition(y,p)['groups']['稳产']['m1_to_1']
        self.assertAlmostEqual(r['mean_per_well_weighted_loss'],.5/(1+1e-6),places=15)
    def test_month_order(self):
        y=np.ones((1,12));p=y.copy();p[0,0]=0;a=impl.loss_decomposition(y,p)['groups']['稳产']['m1_to_12']['mean_per_well_weighted_loss'];p=y.copy();p[0,-1]=0;b=impl.loss_decomposition(y,p)['groups']['稳产']['m1_to_12']['mean_per_well_weighted_loss'];self.assertAlmostEqual(a/b,2048.)
    def test_zero_overlay_not_partition(self):
        y=np.ones((2,12));y[0,0]=0;p=np.ones_like(y)*.3;r=impl.loss_decomposition(y,p)['groups'];self.assertEqual(sum(r[k]['m1_to_12']['well_count'] for k in ('上升','下降','稳产')),2);self.assertEqual(r['含0值']['m1_to_12']['well_count'],1)
    def test_perfect_predictions_zero_total(self):
        r=impl.loss_decomposition(np.ones((2,12)),np.ones((2,12)))['groups']['稳产']['m1_to_12'];self.assertEqual(r['mean_per_well_score'],100.);self.assertEqual(r['total_loss_contribution_share'],0.)
    def test_thresholds_strict_and_exact_zero(self):
        y=np.ones((4,12));y[0,3:6]=1.1;y[1,3:6]=.9;y[2,3:6]=1.11;y[3,3:6]=.89
        # Boundary testing uses one constant value per comparison block.
        a=y[:,:2].mean(1);b=y[:,3:6].mean(1);r=impl.loss_decomposition(y,y)['groups']
        self.assertEqual(r['上升']['m1_to_12']['well_count'],int((b>1.1*a).sum()))
        self.assertEqual(r['下降']['m1_to_12']['well_count'],int((b<.9*a).sum()))
    def test_prepare_pipeline_no_fit(self):
        result,calls=run_prepare();self.assertEqual(result['N1_single_event_train'],81);self.assertEqual(result['N1_date_consistent_train'],81)
        self.assertEqual(result['N2_combo_pass_count'],2);self.assertTrue(all(x==0 for x in result['fit_counts'].values()))
        self.assertEqual(sum(c==['WELL_ID','NY','CSLB'] for c in calls),10);self.assertEqual(result['test_label_columns_read'],0)
    def test_consecutive_event_months_merge(self): self.assertEqual(run_prepare(consecutive=True)[0]['N1_single_event_train'],81)
    def test_gapped_event_months_do_not_merge(self): self.assertEqual(run_prepare(multiple=True)[0]['N1_single_event_train'],80)
    def test_late_completion_cannot_be_A(self): self.assertEqual(run_prepare(late_plan=True)[0]['N1_evidence_level'],'C')
    def test_test_plan_mutation_has_no_train_decision_effect(self):
        a,_=run_prepare();b,_=run_prepare(change_test=True)
        for key in ('N1_single_event_train','N1_date_consistent_train','N1_evidence_level','N2_combo_pass_count'):self.assertEqual(a[key],b[key])
    def test_no_fit_call_in_exact_diagnostic_source(self):
        tree=ast.parse((B/'diagnose_030.py').read_bytes())
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {'fit','fit_transform','partial_fit'} for n in ast.walk(tree)))

if __name__=='__main__':unittest.main(verbosity=2)
