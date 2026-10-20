"""Exact selected B AST bodies + synthetic stdlib spies, NOT real ML fits."""
import ast,json,sys,types,math,statistics,copy,contextlib,tempfile,unittest,hashlib
from datetime import datetime,timezone
from pathlib import Path
R=Path(__file__).resolve().parent;SRC=R/'first/bundle/source'
fixture=R/'fixture_r14.py'
if not fixture.exists():fixture=R.parent/'CODEX_A2B035_R14_REVIEW_20261020/test_increment_source.py'
ns={'statistics':statistics,'math':math,'types':types,'calendar':__import__('calendar')}
tree=ast.parse(fixture.read_bytes());nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))and n.name in ['require','A','IX','GC','GB','F','Series','N','Month','P']]
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(fixture),'exec'),ns)
A,F,N,require=[ns[n] for n in ['A','F','N','require']]
A.__rmul__=A.__mul__
N.concatenate=lambda xs:A(v for x in xs for v in x)
def load(file,names,env):
 tree=ast.parse(file.read_bytes());nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name in names];assert {n.name for n in nodes}==set(names)
 exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(file),'exec'),env);return env
class XX(list):
 @property
 def shape(self):return len(self),len(self[0])
class Prep:
 def __init__(self):self.calls=[]
 def fit_transform(self,x,y):self.calls.append(('fit',list(x.index),list(y)));return self.transform(x)
 def transform(self,x):self.calls.append(('transform',list(x.index)));return XX([[r['f']] for r in x.rows])
class Ledger:
 def __init__(self):self.calls=[]
 def run(self,k,s,f):self.calls.append((k,s));return f()
GUARDS=[]
@contextlib.contextmanager
def guard(classes):GUARDS.append(classes);yield
old=types.SimpleNamespace(load_variant=lambda p:{'which':p.name},HERE=Path('synthetic_base'),transform_target=lambda p,c:A(math.log1p(r['RCYL']/r['__scale035']) for r in p.rows),inverse_target=lambda z,p:A(max(0,math.expm1(v)*r['__scale035']) for v,r in zip(z,p.rows)),joblib=types.SimpleNamespace(parallel_backend=lambda _:contextlib.nullcontext()),file_sha=lambda p:'2ab5a07d5c41dfe6db9aa7ae106fc6de898326c2765be66505a07e2868c10736')
S={'np':N,'pd':ns['P'],'require':require,'Path':Path,'old':old,'im':types.SimpleNamespace(version=lambda name:{'LightGBM':'4.6.0','CatBoost':'1.2.8','tabpfn':'2.2.1'}[name]),'inspect':__import__('inspect'),'NATIVE_THREADS':19,'datetime':datetime,'timezone':timezone,'json':json,'HERE':R/'synthetic_deadline/source','forbid_fits':guard,'copy':copy}
load(SRC/'study16.py',['proxy','valid','estimator','fit','predict','tab_deadline'],S)
def config(learner='LightGBM',W=False):return next(copy.deepcopy(x['config']) for x in json.loads((R/'first/sources/GRID16.json').read_bytes())['variants'] if x['config']['learner']==learner and x['config']['W']==W)
class Tests(unittest.TestCase):
 def test_01_all_locked_configs_valid(self):
  for v in json.loads((R/'first/sources/GRID16.json').read_bytes())['variants']:S['valid'](v['config'])
 def test_02_reject_unsafe_cutoff_and_unregistered_params(self):
  for key,value in [('cutoff','T0_plus_1'),('W',1),('params',{'num_leaves':31})]:
   c=config();c[key]=value
   with self.assertRaises(RuntimeError):S['valid'](c)
 def test_03_Tab_weighted_not_silently_approximated(self):
  c=config('TabPFN');c['W']=True
  with self.assertRaisesRegex(RuntimeError,'NO_SAMPLE_WEIGHT_API'):S['valid'](c)
 def test_04_constructor_exact_grid_and_seed(self):
  calls=[];saved={}
  class Model:
   def __init__(self,**kw):calls.append(kw)
  for learner,module,cls,seed in [('LightGBM','lightgbm','LGBMRegressor','random_state'),('CatBoost','catboost','CatBoostRegressor','random_seed')]:
   saved[module]=sys.modules.get(module);m=types.ModuleType(module);setattr(m,cls,Model);sys.modules[module]=m
   try:
    c=config(learner);S['estimator'](c,None,{},None);actual=calls[-1]
    for k,v in c['params'].items():self.assertEqual(actual[k],v)
    self.assertEqual(actual[seed],20260916);self.assertEqual(actual.get('n_jobs',actual.get('thread_count')),19)
   finally:
    if saved[module] is None:sys.modules.pop(module,None)
    else:sys.modules[module]=saved[module]
 def test_05_estimator_version_mismatch_blocks(self):
  im=S['im'];S['im']=types.SimpleNamespace(version=lambda name:'WRONG')
  try:
   with self.assertRaisesRegex(RuntimeError,'LGB_VERSION'):S['estimator'](config(),None,{},None)
  finally:S['im']=im
 def test_06_actual_fit_weight_and_fold_scope(self):
  panel=F([{'WELL_ID':'SYNTH_'+str(i),'horizon':h,'RCYL':2.,'__scale035':1.,'f':i+h} for i in range(4) for h in range(1,13)]);train=panel.iloc[list(range(24,48))];calls=[]
  class Model:
   def fit(self,x,y,**kwargs):calls.append(kwargs)
  saved=S['estimator'];prep=Prep();old.training=types.SimpleNamespace(_preprocessor=lambda x:prep);S['estimator']=lambda *a:Model()
  try:
   for w in [False,True]:
    ledger=Ledger();S['fit'](config(W=w),train,['f'],{},ledger,'synthetic',None);self.assertEqual(ledger.calls,[('preprocessor','synthetic'),('model','synthetic')])
   self.assertEqual(calls[0],{});self.assertEqual(list(calls[1]['sample_weight']),[2.**-r['horizon'] for r in train.rows]);self.assertEqual([c[1] for c in prep.calls if c[0]=='fit'],[list(train.index)]*2)
  finally:S['estimator']=saved
 def test_07_predict_tab_underlying_single_row_and_every_query_deadline(self):
  c=config('TabPFN');prep=Prep();sizes=[];ticks=[]
  class M:
   def predict(self,x):sizes.append(len(x));return [math.log1p(sum(row)) for row in x]
  p=F([{'f':2.,'__scale035':1.},{'f':3.,'__scale035':2.},{'f':4.,'__scale035':1.}]);a={'model':M(),'prep':prep,'features':['f'],'config':c};saved=S['tab_deadline'];S['tab_deadline']=lambda:ticks.append(1)
  try:
   result=S['predict'](a,p);rev=S['predict'](a,p.iloc[::-1])[::-1];self.assertEqual(list(result),list(rev));self.assertEqual(sizes,[1]*6);self.assertEqual(len(ticks),6);self.assertTrue(all(x[0]=='transform' for x in prep.calls))
  finally:S['tab_deadline']=saved
 def test_08_predict_native_batch_single_reverse(self):
  class M:
   def predict(self,x):return [math.log1p(sum(row)) for row in x]
  p=F([{'f':2.,'__scale035':1.},{'f':3.,'__scale035':2.},{'f':4.,'__scale035':1.}]);a={'model':M(),'prep':Prep(),'features':['f'],'config':config()}
  out=S['predict'](a,p);self.assertEqual(list(out),list(S['predict'](a,p.iloc[::-1])[::-1]));self.assertEqual(list(out),list(N.concatenate([S['predict'](a,p.iloc[[i]]) for i in range(3)])));self.assertTrue(GUARDS)
 def test_09_deadline_missing_approval_blocks(self):
  original=S['datetime']
  class Future(datetime):
   @classmethod
   def now(cls,tz):return datetime(2026,10,23,tzinfo=timezone.utc)
  S['datetime']=Future
  try:
   with self.assertRaisesRegex(RuntimeError,'TAB_DEADLINE_NO_CODEX'):S['tab_deadline']()
  finally:S['datetime']=original
 def test_10_deadline_predeadline_continues(self):
  original=S['datetime']
  class Before(datetime):
   @classmethod
   def now(cls,tz):return datetime(2026,10,20,tzinfo=timezone.utc)
  S['datetime']=Before
  try:S['tab_deadline']()
  finally:S['datetime']=original
 def test_11_fusion_grid_uses_only_supplied_inner_labels(self):
  tree=ast.parse((SRC/'run16.py').read_bytes());loop=next(n for n in ast.walk(tree) if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='units')
  calls=[];env={'best':None,'member':[A([1.,2.]),A([3.,4.])],'train':'SYNTHETIC_INNER_ONLY','old':types.SimpleNamespace(summary=lambda train,p:(calls.append(train) or {'official_score':1.}))}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[loop],type_ignores=[])),str(SRC/'run16.py'),'exec'),env);self.assertEqual(calls,['SYNTHETIC_INNER_ONLY']*11);self.assertEqual(env['best'],(1.,0.))
 def test_12_source_well_disjoint_and_test_never_loaded_for_search(self):
  run=(SRC/'run16.py').read_text();self.assertIn("not set(p.iloc[tr].WELL_ID)&set(p.iloc[va].WELL_ID)",run);self.assertIn("not set(gtr)&set(va) and not set(gva)&set(va)",run);self.assertNotIn('load_test(',run);self.assertIn("with old.offline_only():",run);self.assertIn("splits['fixed'][0]",run)
 def test_13_integration_covers_both_boundaries_and_all_nonkeys(self):
  source=(SRC/'study16.py').read_text();self.assertIn("for cut in ('M_minus_1','T0_minus_1'):",source);self.assertIn("if c not in ('WELL_ID','NY')",source);self.assertIn("Store(columns,True)",source);self.assertIn("fs+['__scale035']",source)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(R/'SOURCE_TEST_RESULT.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'A_model_fits':0,'A_preprocessor_fits':0,'method':'selected original AST plus synthetic stdlib/fit spies; source assertions explicitly distinguished; no native ML/binary replay'},indent=2),encoding='utf-8');raise SystemExit(not result.wasSuccessful())
