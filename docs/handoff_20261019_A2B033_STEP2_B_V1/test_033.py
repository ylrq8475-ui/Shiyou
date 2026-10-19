"""Synthetic structural/poison/gate/budget tests: no real fit calls."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from core import *
from fit_ledger import Ledger
from predict import no_fits
def temporary():
    base=HERE.parent/'synthetic_records';base.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(dir=base,delete=False)
class Tests(unittest.TestCase):
    def test_original_source_hashes(self):ensure_sources()
    def test_features_exclude_and_poison_future(self):
        frame=pd.DataFrame({'WELL_ID':['synthetic']*4,'NY':['2099/01/01','2099/02/01','2099/03/01','2099/04/01'],'RCYL':[2.,4.,999.,999.],'field':[1.,2.,999.,999.],'CSLB':['a','b','secret','secret']});cfg={'anchors':{'well_column':'WELL_ID','date_column':'NY','first_forecast_month_offset':1},'schema':{'mapping':{'target':'RCYL'}},'features':{'history_numeric_columns':['RCYL','field'],'history_categorical_columns':['CSLB'],'target_lags':[1,2],'rolling_windows':[2],'trend_windows':[2]}};origin=pd.Period('2099-03','M');left=history_values(frame,'synthetic',origin,cfg);changed=frame.copy();changed.loc[2:,['RCYL','field']]=-999.;changed.loc[2:,'CSLB']='other';right=history_values(changed,'synthetic',origin,cfg);self.assertTrue(all(safe._same_feature_value(left[k],right[k]) for k in left));self.assertEqual(left['history__RCYL__last'],4.)
    def test_template_keys_do_not_decode_window_targets(self):
        raw=b'WELL_ID,NY,RCYL,other\na,2099/01/01,\xff,\xff\n';self.assertEqual(key_projection(raw,'WELL_ID','NY','utf-8-sig',',')[0],[('a','2099/01/01')])
    def test_full_test_reader_window_poison_invariance(self):
        rows=['WELL_ID,NY,RCYL,other']
        for i in range(1,14):rows.append(f'a,2099/{i if i<=12 else 1:02d}/01,1,1')
        # Build ten fictional files with 1 permitted month and 12 targets,
        # including a year boundary; dynamic target cells may be invalid UTF8.
        config={'anchors':{'well_column':'WELL_ID','date_column':'NY','first_forecast_month_offset':1},'schema':{'mapping':{'target':'RCYL'}},'features':{'history_numeric_columns':['RCYL','other'],'target_lags':[1],'rolling_windows':[1],'trend_windows':[1]},'data':{'csv':{'encoding':'utf-8-sig'},'sources':{'test':{'history':[str(i) for i in range(10)],'template':[str(i) for i in range(10)]}}}};keys=[];original={};mutated={}
        for i in range(10):
            dates=[pd.Period('2099-02','M')+j for j in range(12)];key=[(f'synthetic{i}',f'{p.year}/{p.month}/1') for p in dates];keys+=key;head=b'WELL_ID,NY,RCYL,other\n';pre=f'synthetic{i},2099/1/1,2,3\n'.encode();a=b''.join(f'{w},{d},1,1\n'.encode() for w,d in key);b=b''.join(f'{w},{d},'.encode()+b'\xff,\xff\n' for w,d in key);original[str(i)]=head+pre+a;mutated[str(i)]=head+pre+b
        class Store:
            def __init__(self,values):self.values=values
            def raw(self,name):return self.values[name]
        policy={'template_key_sha256':fingerprint(keys),'feature_order':['horizon','history__RCYL__last']};k,a,r=test_keys_and_history(Store(original),config,policy);l,b,s=test_keys_and_history(Store(mutated),config,policy);self.assertEqual(k,l);self.assertEqual(r,s);self.assertTrue(all(x[0].equals(y[0]) for x,y in zip(a,b)))
        left,_=build_test(Store(original),config,policy);right,_=build_test(Store(mutated),config,policy)
        class FrozenMock:
            def predict(self,x):return np.log1p(np.full(len(x),.5))
        self.assertTrue(np.array_equal(predict(FrozenMock(),left,policy['feature_order'],config),predict(FrozenMock(),right,policy['feature_order'],config)))
    def test_template_hash_failure_before_dynamic(self):
        class Store:
            def __init__(self):self.calls=0
            def raw(self,name):
                self.calls+=1
                if self.calls>10:raise ValueError('DYNAMIC_ACCESS_BEFORE_HASH_GUARD')
                return ('WELL_ID,NY\n'+''.join(f'synthetic{name},{(pd.Period("2099-01","M")+j).year}/{(pd.Period("2099-01","M")+j).month}/1\n' for j in range(13))).encode()
        roles={'history':[str(i) for i in range(10)],'template':[str(i) for i in range(10)]};config={'data':{'csv':{},'sources':{'test':roles}}};store=Store()
        with self.assertRaisesRegex(RuntimeError,'TEMPLATE_IDENTITY_BEFORE_DYNAMIC_ACCESS'):test_keys_and_history(store,config,{'template_key_sha256':'invalid'})
        self.assertEqual(store.calls,10)
    def test_ledger_failure_stops_no_retry(self):
        with temporary() as t:
            ledger=Ledger(Path(t)/'ledger.json')
            with self.assertRaises(ValueError):ledger.run('model','a',lambda:(_ for _ in ()).throw(ValueError()))
            with self.assertRaises(RuntimeError):ledger.run('model','b',lambda:None)
            self.assertEqual(ledger.value['models_entered'],1)
    def test_ledger_success_not_repeated(self):
        with temporary() as t:
            ledger=Ledger(Path(t)/'ledger.json');ledger.run('model','a',lambda:None)
            with self.assertRaises(RuntimeError):ledger.run('model','a',lambda:None)
    def test_two_model_budget(self):
        with temporary() as t:
            ledger=Ledger(Path(t)/'ledger.json')
            for i in range(2):ledger.run('model',str(i),lambda:None)
            with self.assertRaises(RuntimeError):ledger.run('model','third',lambda:None)
    def test_inference_fit_forbidden(self):
        from sklearn.ensemble import ExtraTreesRegressor
        with no_fits():
            with self.assertRaises(RuntimeError):ExtraTreesRegressor().fit(None,None)
    def test_official_score(self):
        p=pd.DataFrame({'WELL_ID':['synthetic']*12,'horizon':range(1,13),'RCYL':[1.]*12});v=summary(p,np.zeros(12));self.assertAlmostEqual(v['official_score'],100*(1-sum(.5**t for t in range(1,13))/(1+1e-6)))
if __name__=='__main__':unittest.main(verbosity=2)
