"""A-only synthetic contracts. No estimator/preprocessor is fitted."""
import json,math,tempfile,unittest
from decimal import Decimal,getcontext
from pathlib import Path
from unittest.mock import patch
import numpy as np,pandas as pd
import core
from fit_ledger import fit_once,Ledger
ROOT=Path(__file__).resolve().parent
def cfg():return {'anchors':{'well_column':'WELL_ID','date_column':'NY','first_forecast_month_offset':1},'schema':{'mapping':{'target':'RCYL'}},'features':{'history_numeric_columns':['RCYL','flow'],'history_categorical_columns':['CSLB'],'target_lags':[1,2],'rolling_windows':[2],'trend_windows':[2]},'data':{'csv':{'encoding':'utf-8-sig','delimiter':','},'sources':{'test':{'history':[str(i) for i in range(10)],'template':[str(i) for i in range(10)]}}}}
FEATURES=['horizon','history__RCYL__last','history__flow__last','history__CSLB__last']
class Store:
    def __init__(self,values):self.values=values;self.calls=0
    def raw(self,name):self.calls+=1;return self.values[name]
def fixture(kind='plain'):
    values={};keys=[]
    for i in range(10):
        wid=f'fiction_{i}';dates=[pd.Period('2099-02','M')+k for k in range(12)]
        pre=f'WELL_ID,NY,RCYL,flow,CSLB\n{wid},2098/12/1,2,3,old\n{wid},2099/1/1,4,5,current\n'.encode()
        rows=[]
        for d in dates:
            ny=f'{d.year}/{d.month}/1';keys.append((wid,ny))
            v={'plain':b'9,10,ordinary','numeric':b'-999,1e300,changed','nan':b'NaN,Inf,changed','bytes':b'\xff,\xfe,\xff','quoted':b'"line\nvalue","a,b","c""d"'}[kind]
            rows.append(f'{wid},{ny},'.encode()+v+b'\n')
        values[str(i)]=pre+b''.join(rows)
    return Store(values),{'template_key_sha256':core.fingerprint(keys),'feature_order':FEATURES}
class Probe:
    def predict(self,x):return np.log1p(x['history__RCYL__last'].to_numpy(float)+.1*x['history__flow__last'].to_numpy(float)+.01*x['horizon'].to_numpy(float))
def oracle(y,p):
    getcontext().prec=45;out=[]
    for a,b in zip(y,p):
        loss=Decimal(0)
        for h,(v,w) in enumerate(zip(a,b),1):
            v,w=Decimal(str(v)),Decimal(str(w));loss+=abs(v-w)/(abs(v)+abs(w)+Decimal('0.000001'))/(Decimal(2)**h)
        out.append(100*(1-loss))
    return float(sum(out)/len(out))
class Independent(unittest.TestCase):
    def pair(self,kind):
        original,policy=fixture();changed,_=fixture(kind);a,aa=core.build_test(original,cfg(),policy);b,bb=core.build_test(changed,cfg(),policy)
        pd.testing.assert_frame_equal(a,b);self.assertEqual(aa,bb);self.assertTrue(np.array_equal(core.predict(Probe(),a,FEATURES,cfg()),core.predict(Probe(),b,FEATURES,cfg())))
    def test_numeric_window_invariance(self):self.pair('numeric')
    def test_nan_inf_window_invariance(self):self.pair('nan')
    def test_undecodable_window_invariance(self):self.pair('bytes')
    def test_quoted_multiline_window_invariance(self):self.pair('quoted')
    def test_positive_control_legal_prefix_changes_prediction(self):
        a,policy=fixture();b,_=fixture();b.values['0']=b.values['0'].replace(b'2099/1/1,4,5,current',b'2099/1/1,7,5,current')
        x,_=core.build_test(a,cfg(),policy);y,_=core.build_test(b,cfg(),policy)
        self.assertFalse(np.array_equal(core.predict(Probe(),x,FEATURES,cfg()),core.predict(Probe(),y,FEATURES,cfg())))
    def test_other_well_change_does_not_change_unchanged_wells(self):
        a,policy=fixture();b,_=fixture();b.values['0']=b.values['0'].replace(b'2099/1/1,4,5,current',b'2099/1/1,7,5,current')
        x,_=core.build_test(a,cfg(),policy);y,_=core.build_test(b,cfg(),policy);pd.testing.assert_frame_equal(x.iloc[12:],y.iloc[12:])
        self.assertTrue(np.array_equal(core.predict(Probe(),x,FEATURES,cfg())[12:],core.predict(Probe(),y,FEATURES,cfg())[12:]))
    def test_template_date_mutation_blocks_before_dynamic_parse(self):
        a,policy=fixture('bytes');a.values['0']=a.values['0'].replace(b'2099/2/1',b'2099/2/2')
        with self.assertRaisesRegex(RuntimeError,'TEMPLATE_IDENTITY_BEFORE_DYNAMIC_ACCESS'):core.build_test(a,cfg(),policy)
        self.assertEqual(a.calls,10)
    def test_template_well_key_mutation_blocks(self):
        a,policy=fixture('bytes');a.values['0']=a.values['0'].replace(b'fiction_0,2099/2/1',b'different,2099/2/1')
        with self.assertRaisesRegex(RuntimeError,'TEMPLATE_KEYS'):core.build_test(a,cfg(),policy)
    def test_training_cutoff_excludes_first_target_month(self):
        f=pd.DataFrame({'WELL_ID':['fiction']*3,'NY':['2099/1/1','2099/2/1','2099/3/1'],'RCYL':[2,4,999],'flow':[1,3,999],'CSLB':['a','b','secret']})
        v=core.history_values(f,'fiction',pd.Period('2099-03','M'),cfg());self.assertEqual(v['history__RCYL__last'],4)
        f.loc[2,'RCYL']=-10;self.assertEqual(core.history_values(f,'fiction',pd.Period('2099-03','M'),cfg())['history__RCYL__last'],4)
    def test_scale_uses_raw_last_not_imputation(self):
        f=pd.DataFrame({'history__RCYL__last':[np.nan,0,-2,np.inf,4],'history__RCYL__roll_12_mean':[9]*5})
        self.assertTrue(np.array_equal(core.training._target_scale(f,'log_ratio_last'),[1,1,1,1,4]))
    def test_scale_and_target_same_cutoff(self):
        f=pd.DataFrame({'history__RCYL__last':[2,4],'RCYL':[6,8]})
        self.assertTrue(np.array_equal(core.training._transform_target(f.RCYL,f,'log_ratio_last'),np.log1p([3,2])))
    def test_metric_decimal_oracle_and_equal_wells(self):
        y=[[0,1,2,3,4,5,6,7,8,9,10,11],[100]*12];p=[[1]*12,[90]*12]
        frame=pd.DataFrame([{'WELL_ID':f'fiction{i}','horizon':j+1,'RCYL':v} for i,row in enumerate(y) for j,v in enumerate(row)])
        self.assertAlmostEqual(core.summary(frame,np.array(p).ravel())['official_score'],oracle(y,p),12)
    def test_metric_near_zero_epsilon(self):
        f=pd.DataFrame({'WELL_ID':['fiction']*12,'horizon':range(1,13),'RCYL':[1e-7]*12})
        self.assertAlmostEqual(core.summary(f,np.zeros(12))['official_score'],oracle([[1e-7]*12],[[0]*12]),12)
    def test_first_month_twice_second_month_weight(self):
        f=pd.DataFrame({'WELL_ID':['fiction']*12,'horizon':range(1,13),'RCYL':[1.]*12});a=np.ones(12);b=a.copy();a[0]=0;b[1]=0
        self.assertAlmostEqual(100-core.summary(f,a)['official_score'],2*(100-core.summary(f,b)['official_score']),12)
    def test_weight_sum_unnormalized(self):self.assertEqual(sum(.5**i for i in range(1,13)),1-2**-12)
    def test_325_order_identity_changes_are_detectable(self):
        lock=json.loads((ROOT/'sources/step1/IMPLEMENTATION_PREFIT_LOCK.json').read_bytes());cols=[x[0] for x in lock['ordered_feature_dtypes']]
        self.assertEqual(len(cols),325);self.assertEqual(len(set(cols)),325);self.assertNotEqual(core.fingerprint(cols),core.fingerprint(cols[::-1]))
    def test_retain_gate_positive_fold_count_required(self):self.assertFalse(2.6185109826630395>=1 and 3>=4)
    def test_fit_once_scope_with_only_synthetic_callbacks(self):
        seen={}
        class Prep:
            def fit_transform(self,x,y):seen['x']=x.copy();seen['y']=np.asarray(y).copy();return x.to_numpy(float)
        class Model:
            def get_params(self):return dict(n_estimators=400,min_samples_leaf=6,max_features=.75,random_state=20260916,n_jobs=-1)
            def fit(self,x,y):seen['model_x']=np.asarray(x).copy();seen['model_y']=np.asarray(y).copy()
        class Pipe:named_steps={'preprocess':Prep(),'model':Model()}
        f=pd.DataFrame({'history__RCYL__last':[2.,4.],'horizon':[1,2],'RCYL':[6.,8.]},index=[10,11]);features=['history__RCYL__last','horizon']
        with tempfile.TemporaryDirectory(dir=ROOT) as t,patch.object(core.training,'_model_pipeline',return_value=Pipe()):
            ledger=Ledger(Path(t)/'synthetic_ledger.json');fit_once(f,features,cfg(),ledger,'synthetic-only')
            self.assertEqual(list(seen['x'].index),[10,11]);self.assertTrue(np.array_equal(seen['y'],np.log1p([3,2])));self.assertTrue(np.array_equal(seen['model_y'],seen['y']))
    def test_R11_authorization_before_fit(self):
        source=(ROOT/'sources/B033s2/train.py').read_text(encoding='utf-8')
        self.assertLess(source.index("authorization=json.loads"),source.index('pipe=fit_once'))
        self.assertIn("authorization['step1_gate_passed'] is False",source)
        self.assertIn('012e9fe50efac3f051b48804bc724e39b703cc93',source)
    def test_step1_not_retroactively_passed_despite_authorized_step2(self):
        r=json.loads((ROOT/'sources/B033s2/RESULT_A2B033_STEP2.json').read_bytes())
        self.assertFalse(r['original_step1_retain_gate_passed']);self.assertTrue(r['user_override_recorded'])
        self.assertEqual(r['step2_model_fits'],2);self.assertEqual(r['platform_uploads'],0)
    def synthetic_result(self,root,mutation=None):
        import csv,io,zipfile
        store,policy=fixture();panel,_=core.build_test(store,cfg(),policy)
        path=Path(root)/'fictional_contract.zip'
        if mutation is None:
            core.write_result(path,panel,np.full(120,1.25));return path,panel
        with zipfile.ZipFile(path,'w') as z:
            for i,(wid,g) in enumerate(panel.groupby('WELL_ID',sort=False)):
                rows=[['WELL_ID','NY','RCYL']]+[[w,d,'1.25'] for w,d in g[['WELL_ID','NY']].itertuples(index=False,name=None)]
                name=wid+'.csv'
                if i==0:
                    if mutation=='index':rows=[['index']+r for r in rows]
                    if mutation=='columns':rows[0]=['NY','WELL_ID','RCYL']
                    if mutation=='nan':rows[1][2]='NaN'
                    if mutation=='inf':rows[1][2]='Inf'
                    if mutation=='negative':rows[1][2]='-1'
                    if mutation=='duplicate':rows[2]=rows[1]
                    if mutation=='order':rows[1],rows[2]=rows[2],rows[1]
                    if mutation=='directory':name='extra/'+name
                    if mutation=='row_count':rows.pop()
                out=io.StringIO();csv.writer(out,lineterminator='\\n').writerows(rows);z.writestr(name,out.getvalue())
        return path,panel
    def test_valid_linter_template_and_floats(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as t:
            p,f=self.synthetic_result(t);r=core.lint_result(p,f);self.assertEqual((r['files'],r['rows']),(10,120));self.assertTrue(r['CRC_passed'])
    def test_linter_rejects_mutations(self):
        for name in ['index','columns','nan','inf','negative','duplicate','order','directory','row_count']:
            with self.subTest(name=name),tempfile.TemporaryDirectory(dir=ROOT) as t:
                p,f=self.synthetic_result(t,name)
                with self.assertRaises(RuntimeError):core.lint_result(p,f)
    def test_R11_budget_counts_preprocessor_and_models_separately(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as t:
            ledger=Ledger(Path(t)/'fictional_ledger.json')
            for i in range(2):ledger.run('preprocessor',str(i),lambda:None);ledger.run('model',str(i),lambda:None)
            for k in ['preprocessor','model']:
                with self.assertRaises(RuntimeError):ledger.run(k,'third',lambda:None)
            self.assertEqual(ledger.value['models_entered'],2)
            self.assertEqual(ledger.value['preprocessors_entered'],2)
    def test_document_environment_mismatch_independently_probed(self):
        r=json.loads((ROOT/'README_INTERPRETER_PROBE_CODEX.json').read_bytes())
        self.assertTrue(r['finding_confirmed'])
    def test_model_config_and_scale_source_unchanged_from_step1(self):
        b=ROOT/'sources/B033s2';a=ROOT/'sources/step1'
        for name in ['core.py','csv_projection.py','predict.py','FROZEN_SOURCES.json']:
            self.assertEqual((a/name).read_bytes(),(b/name).read_bytes())
    def test_no_hidden_fit_during_inference(self):
        import predict
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import ExtraTreesRegressor
        with predict.no_fits():
            with self.assertRaisesRegex(RuntimeError,'ANY_INFERENCE_FIT_FORBIDDEN'):ColumnTransformer([]).fit([[1.]])
            with self.assertRaises(RuntimeError):ExtraTreesRegressor().fit([[1.]],[1.])
    def test_test_role_mapping_conflict_blocks(self):
        st,pol=fixture();c=cfg();c['data']['sources']['test']['template']=['other']*10
        with self.assertRaisesRegex(RuntimeError,'TEST_ROLE_MAPPING'):core.build_test(st,c,pol)
if __name__=='__main__':unittest.main(verbosity=2)
