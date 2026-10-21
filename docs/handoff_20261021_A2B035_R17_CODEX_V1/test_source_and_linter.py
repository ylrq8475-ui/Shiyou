"""Selected exact original AST; synthetic-only, stdlib vector/table/fit spies, no ML."""
import ast,json,math,types,statistics,contextlib,unittest,tempfile,zipfile,io,csv,hashlib,copy
from pathlib import Path
R=Path(__file__).resolve().parent;SRC=R/'fusion/bundle/source';FIX=R/'fixture_r14.py'
if not FIX.exists():FIX=R.parent/'CODEX_A2B035_R14_REVIEW_20261020/test_increment_source.py'
ns={'statistics':statistics,'math':math,'types':types,'calendar':__import__('calendar')};nodes=[n for n in ast.parse(FIX.read_bytes()).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))and n.name in ['require','A','IX','GC','GB','F','Series','N','Month','P']]
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(FIX),'exec'),ns)
A,F,N,require=[ns[x] for x in ['A','F','N','require']]
A.__rmul__=A.__mul__;A.__rsub__=lambda self,x:A(x-a for a in self);A.shape=property(lambda self:(len(self),));A.ndim=1;A.isna=lambda self:A(x is None or isinstance(x,float)and math.isnan(x) for x in self)
F.columns=property(lambda self:list(self.rows[0]) if self.rows else []);F.itertuples=lambda self,index=False,name=None:(tuple(r.values()) for r in self.rows);F.assign=lambda self,**kw:F([dict(r,**{k:v[i] for k,v in kw.items()}) for i,r in enumerate(self.rows)],self.index)
N.clip=lambda a,low,high:A(max(low,x) if high is None else min(high,max(low,x)) for x in a);N.power=lambda a,b:A(a**x for x in b);N.sum=lambda x:sum(x);N.mean=lambda x:statistics.mean(x);N.flatnonzero=lambda x:A(i for i,b in enumerate(x) if b)
def load(file,names,env):
 nodes=[n for n in ast.parse(file.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name in names];assert {n.name for n in nodes}==set(names)
 code=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[]);exec(compile(ast.fix_missing_locations(code),str(file),'exec'),env);return env
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
S={'np':N,'require':require,'R17':'7f44d70aa53410a2d072d69874003f3a8946adbb','Path':Path,'json':json,'HERE':SRC,'encode':lambda x:(json.dumps(x,indent=2)+'\n').encode()}
load(SRC/'fusion17.py',['spec','members','mix','fit_pair','load_pair','predict_pair'],S)
PD=types.SimpleNamespace(to_numeric=lambda x,errors=None:A(float(v) if v is not None else math.nan for v in x))
M={'pd':PD,'np':N,'DataContractError':RuntimeError,'ConfigurationError':ValueError,'ScoreResult':lambda **kw:types.SimpleNamespace(**kw)}
load(SRC/'base/src/oil_uplift/scoring.py',['official_twelve_month_score'],M)
L={'Path':Path,'np':N,'require':require,'zipfile':zipfile,'io':io,'csv':csv,'sha':lambda b:hashlib.sha256(b).hexdigest(),'file_sha':sha}
load(SRC/'base/core.py',['write_result','lint_result'],L)
def panel(n=10):return F([{'WELL_ID':'SYNTH_'+str(i),'NY':f'2040-{h}-1','horizon':h,'RCYL':float(i+1),'__scale035':1.} for i in range(n) for h in range(1,13)])
class Ledger:
 def __init__(self,path):self.value={'models_completed':0,'preprocessors_completed':0,'events':[]}
class Tests(unittest.TestCase):
 def test_01_exact_raw_value_blends_and_clipping(self):
  for n,w,z in [('F70',.7,.3),('F50',.5,.5)]:
   a=A([2.,4.,-8.]);b=A([4.,8.,2.]);c=S['spec'](n);expected=[max(0,w*x+z*y) for x,y in zip(a,b)]
   self.assertEqual(list(S['mix'](a,b,c)),expected);self.assertEqual(list(S['mix'](a[::-1],b[::-1],c)[::-1]),expected)
 def test_02_forbid_alternative_weights_and_bad_values(self):
  c=S['spec']('F70');c['B0_weight']=.6
  with self.assertRaisesRegex(RuntimeError,'NO_ALTERNATIVE'):S['mix']([1.],[2.],c)
  for bad in [math.nan,math.inf,-math.inf]:
   with self.assertRaisesRegex(RuntimeError,'PREDICTION_VALIDITY'):S['mix']([bad],[2.],S['spec']('F70'))
  with self.assertRaises(RuntimeError):S['mix']([1.,2.],[2.],S['spec']('F50'))
 def test_03_no_geology_or_changed_member_config(self):
  configs=[json.loads((SRC/'base/configs'/n).read_bytes()) for n in ['B0.json','B0_prime.json']];b=types.SimpleNamespace(load_variant=lambda path:copy.deepcopy(configs[0 if path.name=='B0.json' else 1]),require_release=lambda *a,**kw:None);S['b']=b;S['members']()
  configs[1]['cutoff']='M_minus_1'
  with self.assertRaisesRegex(RuntimeError,'MEMBER_CUTOFFS'):S['members']()
  configs[1]['cutoff']='T0_minus_1';configs[1]['features']='base325_G'
  with self.assertRaisesRegex(RuntimeError,'MEMBER_REPRESENTATION'):S['members']()
 def test_04_train_pair_loads_train_only_and_fits_two_members(self):
  calls=[];p=panel(2);configs=['SYNTH_B0','SYNTH_B0P'];original=S['members'];S['members']=lambda:configs;S['runtime']=lambda:{'synthetic':True};S['Ledger']=Ledger
  class Store:
   def __init__(self,data):calls.append('open')
   def close(self):calls.append('close')
  class Provider:
   def __init__(self,*a):pass
   def get(self,c):return p,['horizon'],{}
  def fit(c,provider,indices,ledger,stage):calls.append((c,list(indices)));ledger.value['models_completed']+=1;ledger.value['preprocessors_completed']+=1;return {'synthetic':c}
  def dump(obj,path,**kw):Path(path).write_bytes(b'SYNTHETIC_NO_MODEL')
  b=types.SimpleNamespace(verify_source_lock=lambda:None,load_locked_policy=lambda path:({'feature_order':['horizon']},{}),Inputs=Store,load_train=lambda store,legacy:(calls.append('train_only') or None),Panels=Provider,fit_members_full=fit,joblib=types.SimpleNamespace(dump=dump),file_sha=lambda p:'SYNTHETIC_SHA',identity=lambda p,fs:{'synthetic':True});S['b']=b
  try:
   with tempfile.TemporaryDirectory(dir=R,prefix='synthetic_train_') as tmp:receipt=S['fit_pair']('SYNTHETIC_INPUT','SYNTHETIC_POLICY',Path(tmp)/'new');self.assertFalse(receipt['cached_or_packaged_weights_loaded_for_training']);self.assertEqual(receipt['fit_counts']['models_completed'],2)
   self.assertEqual(calls[:3],['open','train_only','close']);self.assertEqual([x[0] for x in calls if isinstance(x,tuple)],configs)
  finally:S['members']=original
 def test_05_predict_pair_is_separate_per_well_and_checks_keys(self):
  p=panel(2);calls=[];original=S['members'];S['members']=lambda:['SYNTH_B0','SYNTH_B0P'];S['load_pair']=lambda *a:{'members':['A','B']};S['forbid_fits']=contextlib.nullcontext
  class Store:
   def __init__(self,*a):pass
   def close(self):pass
  def pred(artifact,provider):q=provider(None);calls.append((artifact,set(q.WELL_ID)));self.assertEqual(len(set(q.WELL_ID)),1);return A(r['RCYL'] for r in q.rows)
  b=types.SimpleNamespace(verify_source_lock=lambda:None,load_locked_policy=lambda path:({},{}),Inputs=Store,build_variant_test=lambda *a:(p,['horizon'],{}),predict_fitted=pred);S['b']=b
  try:
   out,preds,audits=S['predict_pair']('SYNTH','SYNTH','SYNTH');self.assertEqual(len(calls),4);self.assertEqual(list(preds[0]),list(preds[1]))
   bad=p.copy();bad.rows[0]['NY']='2041-1-1';b.build_variant_test=lambda store,pol,legacy,c:(p if c=='SYNTH_B0' else bad,['horizon'],{})
   with self.assertRaisesRegex(RuntimeError,'TEMPLATE_MEMBER_ALIGNMENT'):S['predict_pair']('SYNTH','SYNTH','SYNTH')
  finally:S['members']=original
 def test_06_official_metric_matches_independent_unequal_scale_wells(self):
  p=panel(2);rows=[]
  for r in p.rows:rows.append(dict(r,RCYL=1e3 if r['WELL_ID']=='SYNTH_1' else 1e-3,prediction=0. if r['WELL_ID']=='SYNTH_1' else 1e-3))
  expected=statistics.mean(100*(1-sum(2.**(-r['horizon'])*abs(r['prediction']-r['RCYL'])/(abs(r['prediction'])+abs(r['RCYL'])+1e-6) for r in rows if r['WELL_ID']==w)) for w in ['SYNTH_0','SYNTH_1']);got=M['official_twelve_month_score'](F(rows),truth_column='RCYL',prediction_column='prediction');self.assertAlmostEqual(got.total,expected)
 def test_07_official_t_starts_1_and_not_normalized(self):
  rows=[dict(r,RCYL=1.,prediction=0.) for r in panel(1).rows];got=M['official_twelve_month_score'](F(rows),truth_column='RCYL',prediction_column='prediction').total;self.assertAlmostEqual(got,100*(1-(1-2**-12)/(1+1e-6)))
  for h,weight in [(1,.5),(2,.25),(4,.0625),(12,2**-12)]:
   r=[dict(x,prediction=0. if x['horizon']==h else 1.) for x in rows];self.assertAlmostEqual(M['official_twelve_month_score'](F(r),truth_column='RCYL',prediction_column='prediction').total,100*(1-weight/(1+1e-6)))
 def test_08_metric_epsilon_duplicate_nonfinite_and_zero(self):
  rows=[dict(r,RCYL=0.,prediction=0.) for r in panel(1).rows];self.assertEqual(M['official_twelve_month_score'](F(rows),truth_column='RCYL',prediction_column='prediction').total,100.)
  with self.assertRaises(ValueError):M['official_twelve_month_score'](F(rows),truth_column='RCYL',prediction_column='prediction',epsilon=1e-5)
  rows[0]['horizon']=2
  with self.assertRaises(RuntimeError):M['official_twelve_month_score'](F(rows),truth_column='RCYL',prediction_column='prediction')
  rows=panel(1).rows
  for v in [math.nan,math.inf]:
   bad=[dict(r,prediction=v) for r in rows]
   with self.assertRaises(RuntimeError):M['official_twelve_month_score'](F(bad),truth_column='RCYL',prediction_column='prediction')
 def test_09_exact_linter_template_dates_and_flat_zip(self):
  p=panel();pred=A([2.]*120)
  with tempfile.TemporaryDirectory(dir=R,prefix='synthetic_zip_') as tmp:
   path=Path(tmp)/'synthetic_valid.zip';lint=L['write_result'](path,p,pred);self.assertEqual(lint['status'],'PASS');self.assertEqual(lint['rows'],120)
   with zipfile.ZipFile(path) as z:
    raw={n:z.read(n) for n in z.namelist()};self.assertIn(b'2040-1-1',raw['SYNTH_0.csv']);self.assertFalse(any('/' in n for n in raw))
 def test_10_linter_negative_nan_wrong_columns_date_or_extra_dir(self):
  p=panel()
  with tempfile.TemporaryDirectory(dir=R,prefix='synthetic_bad_zip_') as tmp:
   valid=Path(tmp)/'valid.zip';L['write_result'](valid,p,A([2.]*120))
   with zipfile.ZipFile(valid) as z:original={n:z.read(n) for n in z.namelist()}
   cases=[('negative',b',2\n',b',-1\n'),('nan',b',2\n',b',nan\n'),('inf',b',2\n',b',inf\n'),('columns',b'WELL_ID,NY,RCYL',b'index,WELL_ID,NY,RCYL'),('date',b'2040-1-1',b'2040-01-01')]
   for label,before,after in cases:
    changed=dict(original);changed['SYNTH_0.csv']=changed['SYNTH_0.csv'].replace(before,after,1);path=Path(tmp)/(label+'.zip')
    with zipfile.ZipFile(path,'w') as z:
     for n,raw in changed.items():z.writestr(n,raw)
    with self.assertRaises(RuntimeError):L['lint_result'](path,p)
   path=Path(tmp)/'directory.zip'
   with zipfile.ZipFile(path,'w') as z:
    for n,raw in original.items():z.writestr('extra/'+n,raw)
   with self.assertRaises(RuntimeError):L['lint_result'](path,p)
 def test_11_actual_entry_config_guards_and_no_learned_weight_path(self):
  text=(SRC/'fusion17.py').read_text();self.assertIn("json.loads(Path(a.config).read_bytes())==expected",text);self.assertIn("with b.offline_only():",text);self.assertNotIn('choose_weights',text);self.assertNotIn('TabPFN',text);self.assertIn("policy_sha256",text)
 def test_12_B0_exact_source_is_same_as_prior_approved(self):
  previous=R.parent/'CODEX_A2B035_R15_REVIEW_20261020/first/bundle/source/b0_entry.py';self.assertEqual((R/'b0/bundle/source/b0_entry.py').read_bytes(),previous.read_bytes())
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(R/'SOURCE_TEST_RESULT.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'A_model_fits':0,'A_preprocessor_fits':0,'A_competition_raw_reads':0,'scope':'selected original B function ASTs + stdlib synthetic spies and ZIP fixtures; no native ML/NumPy/Pandas runtime or real-data retraining'},indent=2),encoding='utf-8');raise SystemExit(not result.wasSuccessful())
