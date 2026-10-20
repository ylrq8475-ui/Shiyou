"""Stdlib AST execution of R15 increments; no real data, ML fit or weights."""
import importlib.util,sys,json,ast,types,copy,math,unittest,tempfile
from pathlib import Path
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prior_r14_audit',R.parent/'CODEX_A2B035_R14_REVIEW_20261020/test_increment_source.py');t=importlib.util.module_from_spec(spec);sys.modules[spec.name]=t;spec.loader.exec_module(t)
def load(file,names,ns):
 tree=ast.parse(file.read_bytes());nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name in names];assert {n.name for n in nodes}==set(names);exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(file),'exec'),ns);return ns
SRC=R/'first/bundle/source';BD=dict(t.BD);load(SRC/'error_budget.py',['weights','group_labels','budget','pairs'],BD)
t.F.drop=lambda self,columns,errors=None:t.F([{k:v for k,v in r.items() if k not in columns} for r in self.rows],self.index)
t.F.assign=lambda self,**cols:t.F([dict(r,**{k:v[i] for k,v in cols.items()}) for i,r in enumerate(self.rows)],self.index)
t.Month.ordinal=property(lambda self:self.n)
t.P.notna=lambda x:not(x is None or isinstance(x,float)and math.isnan(x))
class Vectorizer:
 def __init__(self,**kw):self.names=[];self.fit_calls=[]
 def fit_transform(self,items):self.fit_calls.append(items);self.names=sorted({k for d in items for k in d});return self.transform(items)
 def transform(self,items):return [[d.get(k,0.) for k in self.names] for d in items]
def concatenate(items,axis=0):return [list(a)+list(b) for a,b in zip(items[0],items[1])] if axis==1 else sum(items,[])
t.N.concatenate=concatenate
base=json.loads((SRC/'base/configs/B0.json').read_bytes());h=types.SimpleNamespace(normalized=t.NS['normalized'],original_b0prime=lambda:copy.deepcopy(t.BASE),validate=t.NS['validate'],proxy=t.NS['proxy'],specialist_rows=t.NS['specialist_rows'],splice=t.NS['splice'],fold_hash=lambda a,b:'synthetic')
NS={'h':h,'old':t.O,'np':t.N,'pd':t.P,'require':t.require,'copy':copy,'fingerprint':t.NS['fingerprint'],'DictVectorizer':Vectorizer,'b0':lambda:copy.deepcopy(base)}
load(SRC/'routes15.py',['route','valid','fit_model','predict_model','evaluate','HXPreprocessor','hx_values'],NS)
class Prep:
 def __init__(self):self.rows=[]
 def fit_transform(self,x,y):self.rows.append(list(x.index));return [[float(r.get('f1',0.))] for r in x.rows]
 def transform(self,x):return [[float(r.get('f1',0.))] for r in x.rows]
class Ledger:
 def run(self,k,s,f):return f()
class Tests(unittest.TestCase):
 def test_R14_official_identity_and_zero(self):
  p=t.toy()
  for factor in [0.,.5,1.,2.,100.]:
   pred=t.A(r['RCYL']*factor for r in p.rows);out=BD['budget'](p,pred,t.metadata(),t.folds(p));self.assertAlmostEqual(out['total_weighted_loss'],1-t.O.summary(p,pred)['official_score']/100)
  for row in p.rows:row['RCYL']=0.
  for pred in [t.A([0.]*len(p)),t.A([1.]*len(p))]:BD['budget'](p,pred,t.metadata(),t.folds(p))
 def test_R14_reject_invalid(self):
  p=t.toy()
  for x in [-1.,math.inf,math.nan]:
   a=t.A([1.]*len(p));a[0]=x
   with self.assertRaisesRegex(RuntimeError,'BUDGET_NONFINITE_OR_NEGATIVE'):BD['weights'](p,a)
 def test_R14_complement_suppressed(self):
  p=t.toy();out=BD['budget'](p,t.A([2.]*len(p)),t.metadata(),t.folds(p));g=out['groups']['scale_fallback'];self.assertEqual(g['status'],'ENTIRE_DIMENSION_SUPPRESSED');self.assertFalse(any(k in g for k in ['wells','group_mean_weighted_loss','contribution_to_total_loss']))
 def test_R14_cutpoints_train_only(self):
  p=t.toy();m=t.metadata();captured=[];original=t.N.quantile
  def spy(v,q):captured.append(list(v));return original(v,q)
  t.N.quantile=spy
  try:BD['group_labels'](p,m,t.folds(p));a=captured[0];captured.clear();m.rows[0]['production_level']=1e30;m.rows[1]['production_level']=1e30;BD['group_labels'](p,m,t.folds(p));self.assertEqual(a,captured[0])
  finally:t.N.quantile=original
 def test_W_actual_fit_weights_by_row(self):
  p=t.toy();ids=t.folds(p)[0][0];calls=[];prep=Prep()
  class M:
   def fit(self,x,y,**kwargs):calls.append(kwargs)
  NS['estimator_for']=lambda *a:M();t.O.training=types.SimpleNamespace(_preprocessor=lambda x:prep)
  for flag in [False,True]:NS['fit_model'](p.iloc[ids],['f1'],NS['route']('SYNTH',base,flag),{},Ledger(),'synthetic')
  self.assertEqual(calls[0],{});self.assertEqual(list(calls[1]['sample_weight']),[2.**(-p.rows[i]['horizon']) for i in ids]);self.assertEqual(prep.rows,[list(ids),list(ids)]);self.assertAlmostEqual(sum(calls[1]['sample_weight'])/8,1-2**-12)
 def test_HX_vocab_train_only_and_unknown_query(self):
  p=t.F([{'f1':1.,'HX_CSLB_counts':{'SYNTH_A':2}},{'f1':2.,'HX_CSLB_counts':{'SYNTH_B':3}}]);q=t.F([{'f1':3.,'HX_CSLB_counts':{'SYNTH_NEW':99}}]);prep=Prep();t.O.training=types.SimpleNamespace(_preprocessor=lambda x:prep);obj=NS['HXPreprocessor']();x=obj.fit_transform(p,t.A([1.,2.]));y=obj.transform(q);self.assertEqual(obj.counts.names,['SYNTH_A','SYNTH_B']);self.assertEqual(y,[[3.,0.,0.]]);self.assertEqual(len(obj.counts.fit_calls),1)
 def test_HX_cutoff_and_no_cumulative_when_disabled(self):
  end=t.Month(2040*12+3);hist=t.F([{'WELL_ID':'SYNTH','NY':end-3,'RCYL':1.,'CSLB':'SYNTH_A','LJCYL':5.},{'WELL_ID':'SYNTH','NY':end,'RCYL':2.,'CSLB':'SYNTH_B','LJCYL':6.},{'WELL_ID':'SYNTH','NY':end+1,'RCYL':1e30,'CSLB':'SYNTH_NEW','LJCYL':1e30}]);legal,cut=t.O.legal_history(hist,'SYNTH',end+1,'T0_minus_1',t.CF);v=NS['hx_values'](legal,cut,t.CF,False);self.assertEqual(v['HX_production_months'],4);self.assertEqual(v['HX_measure_count'],2);self.assertNotIn('HX_LJCYL_last',v);self.assertNotIn('SYNTH_NEW',v['HX_CSLB_counts'])
 def test_T_new_evaluate_preserves_late(self):
  p=t.toy();c=NS['route']('SYNTH_T',t.BASE,T=True);savedfit=NS['fit_model'];savedpred=NS['predict_model'];calls=[]
  class Provider:
   legacy={}
   def get(self,c):return p,['f1'],{},t.metadata()
  def fit(q,*args):calls.append(list(q.index));self.assertEqual(set(q.horizon),{1,2});return None
  NS['fit_model']=fit;NS['predict_model']=lambda m,q,c:t.A([3.]*len(q));baseline=t.A(10.+i for i in range(len(p)))
  try:out,pr=NS['evaluate'](c,Provider(),t.folds(p),None,'synthetic',baseline)
  finally:NS['fit_model']=savedfit;NS['predict_model']=savedpred
  for row,a,b in zip(p.rows,pr,baseline):self.assertEqual(a,3. if row['horizon']<=2 else b)
  for ids,(_,va) in zip(calls,t.folds(p)):self.assertFalse(set(ids)&set(va))
 def test_config_interface_actual_prepare(self):
  file=R/'close/bundle/package_interfaces/B0_W/config_interface.py'
  with tempfile.TemporaryDirectory(dir=R,prefix='synthetic_config_') as d:
   root=Path(d);(root/'variant.json').write_text('{"synthetic":1}',encoding='utf-8');(root/'wrong.json').write_text('{"synthetic":2}',encoding='utf-8');s=types.SimpleNamespace(argv=['train.py','--config',str(root/'variant.json')]);ns={'sys':s,'json':json,'Path':Path,'__file__':str(root/'config_interface.py')};load(file,['prepare'],ns);ns['prepare']();self.assertEqual(s.argv,['train.py']);s.argv=['train.py','--config='+str(root/'wrong.json')]
   with self.assertRaisesRegex(AssertionError,'FROZEN_VERSION_CONFIG_MISMATCH'):ns['prepare']()
 def test_TabPFN_nested_adapter_always_single_query(self):
  file=R/'close/bundle/tabpfn_probe15.py';tree=ast.parse(file.read_bytes());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)and n.name=='rows');sizes=[]
  class Q(list):
   def __getitem__(self,k):return Q(list.__getitem__(self,i) for i in k) if isinstance(k,list) else Q(list.__getitem__(self,k)) if isinstance(k,slice) else list.__getitem__(self,k)
  model=types.SimpleNamespace(predict=lambda x:(sizes.append(len(x)) or [sum(x[0])]))
  ns={'np':t.N,'model':model,'prep':types.SimpleNamespace(transform=lambda x:x)};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(file),'exec'),ns);q=Q([[1.,2.],[3.,4.],[5.,6.]]);a=ns['rows'](q);b=ns['rows'](q[::-1])[::-1];self.assertEqual(list(a),list(b));self.assertEqual(sizes,[1]*6)
if __name__=='__main__':
 res=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(R/'SOURCE_TEST_RESULT.json').write_text(json.dumps({'tests':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'A_model_fits':0,'A_preprocessor_fits':0,'method':'selected original AST bodies and stdlib table/vector/fit spies; not actual NumPy/sklearn/foundation replay'},indent=2),encoding='utf-8');raise SystemExit(not res.wasSuccessful())
