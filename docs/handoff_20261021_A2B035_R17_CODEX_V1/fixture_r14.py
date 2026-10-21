"""Run exact selected B function ASTs using stdlib synthetic vector/table spies.

No ML libraries, raw competition data, actual estimator/preprocessing fits.
These tests exercise source dataflow, not NumPy/Pandas binary compatibility.
"""
import ast,copy,math,statistics,types,unittest,json,re,calendar,sys,hashlib,contextlib
from pathlib import Path
R=Path(__file__).resolve().parent;SRC=R/'bundle/source';OBS={}
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
class A(list):
 def op(self,o,fn):return A(fn(a,b) for a,b in zip(self,o)) if isinstance(o,list) else A(fn(a,o) for a in self)
 def __add__(self,o):return self.op(o,lambda a,b:a+b)
 def __iadd__(self,o):return self.__add__(o)
 def __sub__(self,o):return self.op(o,lambda a,b:a-b)
 def __mul__(self,o):return self.op(o,lambda a,b:a*b)
 def __truediv__(self,o):return self.op(o,lambda a,b:a/b)
 def __rpow__(self,o):return A(o**a for a in self)
 def __neg__(self):return A(-a for a in self)
 def __eq__(self,o):return self.op(o,lambda a,b:a==b)
 def __lt__(self,o):return self.op(o,lambda a,b:a<b)
 def __le__(self,o):return self.op(o,lambda a,b:a<=b)
 def __gt__(self,o):return self.op(o,lambda a,b:a>b)
 def __ge__(self,o):return self.op(o,lambda a,b:a>=b)
 def __and__(self,o):return self.op(o,lambda a,b:bool(a and b))
 def __invert__(self):return A(not a for a in self)
 def __getitem__(self,k):
  if isinstance(k,list):return A(a for a,b in zip(self,k) if b) if all(type(x)is bool for x in k) else A(list.__getitem__(self,i) for i in k)
  x=list.__getitem__(self,k);return A(x) if isinstance(k,slice) else x
 def __setitem__(self,k,v):
  if isinstance(k,list):
   ids=[i for i,b in enumerate(k) if b] if all(type(x)is bool for x in k) else k
   for i,x in zip(ids,v if isinstance(v,list) else [v]*len(ids)):list.__setitem__(self,i,x)
  else:list.__setitem__(self,k,v)
 def all(self):return all(self)
 def any(self):return any(self)
 def sum(self):return sum(self)
 def mean(self):return statistics.mean(self)
 def copy(self):return A(self)
 def equals(self,o):return list(self)==list(o)
 def to_numpy(self,dtype=None):return A(dtype(x) if dtype else x for x in self)
 def tolist(self):return list(self)
 def isin(self,x):return A(a in x for a in self)
 def nunique(self):return len(set(self))
 def drop_duplicates(self):return A(dict.fromkeys(self))
 def duplicated(self):
  seen=set();out=A()
  for x in self:out.append(x in seen);seen.add(x)
  return out
 def notna(self):return A(not isinstance(x,float) or not math.isnan(x) for x in self)
 def map(self,f):return A(f(x) for x in self)
 @property
 def iloc(self):return self
 @property
 def is_unique(self):return len(set(self))==len(self)
class IX:
 def __init__(self,f,loc=False):self.f=f;self.loc=loc
 def ids(self,k):
  if isinstance(k,slice):return list(range(len(self.f)))[k]
  if isinstance(k,list):return [i for i,b in enumerate(k) if b] if all(type(x)is bool for x in k) else [self.f.index.index(x) for x in k] if self.loc else k
  return [self.f.index.index(k)] if self.loc else [k]
 def __getitem__(self,k):
  col=None
  if isinstance(k,tuple):k,col=k
  ids=self.ids(k);q=F([self.f.rows[i] for i in ids],[self.f.index[i] for i in ids])
  if col is not None:return q[col]
  if self.loc and not isinstance(k,(slice,list)):return types.SimpleNamespace(**q.rows[0])
  return q
 def __setitem__(self,k,v):
  rows,col=k;ids=self.ids(rows)
  for i,x in zip(ids,v if isinstance(v,list) else [v]*len(ids)):self.f.rows[i][col]=x
class GC:
 def __init__(self,g,col):self.g=g;self.col=col
 def agg(self,fn):return A(fn([r[self.col] for r in rows]) for _,rows in self.g.groups)
class GB:
 def __init__(self,f,key):self.groups=[(k,[r for r in f.rows if r[key]==k]) for k in dict.fromkeys(f[key])];self.f=f
 def __iter__(self):
  for k,rows in self.groups:
   ids=[i for i,r in enumerate(self.f.rows) if r in rows];yield k,F(rows,[self.f.index[i] for i in ids])
 def __getattr__(self,col):return GC(self,col)
class F:
 def __init__(self,rows,index=None):self.rows=[dict(r) for r in rows];self.index=A(range(len(rows))) if index is None else A(index)
 def __len__(self):return len(self.rows)
 def __iter__(self):return iter(self.rows[0] if self.rows else [])
 def __getitem__(self,k):return F([{n:r[n] for n in k} for r in self.rows],self.index) if isinstance(k,list) else A(r[k] for r in self.rows)
 def __getattr__(self,k):
  if self.rows and k in self.rows[0]:return self[k]
  raise AttributeError(k)
 def __setitem__(self,k,v):
  for r,x in zip(self.rows,v if isinstance(v,list) else [v]*len(self)):r[k]=x
 @property
 def iloc(self):return IX(self)
 @property
 def loc(self):return IX(self,True)
 @property
 def empty(self):return not self.rows
 def copy(self):return F(self.rows,self.index)
 def groupby(self,key,**kw):return GB(self,key)
 def equals(self,o):
  def eq(a,b):return a==b or isinstance(a,float)and isinstance(b,float)and math.isnan(a)and math.isnan(b)
  return len(self)==len(o) and all(a.keys()==b.keys() and all(eq(a[k],b[k]) for k in a) for a,b in zip(self.rows,o.rows))
 def sort_values(self,key,**kw):return F(sorted(self.rows,key=lambda r:r[key]))
 def set_index(self,key):return F(self.rows,self[key])
class Series(A):
 def groupby(self,keys,**kw):return types.SimpleNamespace(sum=lambda:A(sum(v for v,k in zip(self,keys) if k==u) for u in dict.fromkeys(keys)))
class N:
 nan=float('nan');inf=float('inf')
 @staticmethod
 def asarray(x,dtype=None):return A(dtype(v) if dtype else v for v in x)
 @staticmethod
 def full(n,v):return A([v]*n)
 @staticmethod
 def zeros(n,dtype=None):return A([0]*n)
 @staticmethod
 def arange(*a):return A(range(*a))
 @staticmethod
 def abs(x):return A(abs(v) for v in x)
 @staticmethod
 def isfinite(x):return A(math.isfinite(v) for v in x) if isinstance(x,list) else math.isfinite(x)
 @staticmethod
 def array_equal(a,b):return list(a)==list(b)
 @staticmethod
 def std(x):return statistics.pstdev(x)
 @staticmethod
 def sort(x):return A(sorted(x))
 @staticmethod
 def log1p(x):return A(math.log1p(v) for v in x)
 @staticmethod
 def quantile(x,qs):
  x=sorted(x);out=[]
  for q in qs:
   at=(len(x)-1)*q;i=math.floor(at);out.append(x[i]+(x[min(i+1,len(x)-1)]-x[i])*(at-i))
  return out
 @staticmethod
 def corrcoef(a,b):
  cor=statistics.correlation(a,b)
  class Matrix:
   def __getitem__(self,k):return 1. if k[0]==k[1] else cor
  return Matrix()
class Month:
 def __init__(self,n):self.n=n
 def __add__(self,k):return Month(self.n+k)
 def __sub__(self,k):return Month(self.n-k)
 def __eq__(self,o):return isinstance(o,Month)and self.n==o.n
 def __lt__(self,o):return self.n<o.n
 def __le__(self,o):return self.n<=o.n
 def __hash__(self):return hash(self.n)
 @property
 def days_in_month(self):return calendar.monthrange(self.n//12,self.n%12+1)[1]
class P:
 Series=Series
 @staticmethod
 def DataFrame(x):return F(x)
 @staticmethod
 def to_numeric(x,errors=None):return x
 @staticmethod
 def to_datetime(x,errors=None):return types.SimpleNamespace(dt=types.SimpleNamespace(to_period=lambda _:x))
 @staticmethod
 def Timestamp(x):return types.SimpleNamespace(to_period=lambda _:x)
def source(file,names,ns):
 tree=ast.parse((SRC/file).read_bytes());nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names];assert set(n.name for n in nodes)==set(names)
 exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(SRC/file),'exec'),ns);return ns
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE=json.loads((SRC/'base/configs/B0_prime.json').read_bytes());CF={'anchors':{'well_column':'WELL_ID','date_column':'NY'}}
old={'np':N,'pd':P,'require':require,'copy':copy,'re':re,'SCHEMA':'A2B035-v1'}
source('base/guard035.py',['legal_history','row_value','transform_target','validate_config'],old)
O=types.SimpleNamespace(**{n:old[n] for n in ['legal_history','row_value','transform_target','validate_config']},SCHEMA='A2B035-v1')
O.summary=lambda p,pr: {'official_score':100*(1-sum(sum(2**(-r['horizon'])*abs(float(a)-r['RCYL'])/(abs(float(a))+abs(r['RCYL'])+1e-6) for r,a in zip(p.rows,pr) if r['WELL_ID']==w) for w in set(p.WELL_ID))/p.WELL_ID.nunique()),'weighted_losses':{},'official_cross_check_difference':0.}
NS={'np':N,'pd':P,'old':O,'require':require,'copy':copy,'re':re,'json':json,'Path':Path,'ROOT':SRC,'file_sha':sha,'SCHEMA':'A2B035-R14-v1','M3':['M_RCYL','M_RCYL_ratio','M_SCTS_fraction'],'R5':['R1','R2','R3','R4','R5'],'fingerprint':lambda x:hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest(),'original_b0prime':lambda:copy.deepcopy(BASE),'fold_hash':lambda tr,va:'synthetic','predict_single':None}
source('r14.py',['normalized','validate','base_config','proxy','additions','augment','specialist_rows','splice','evaluate','fit','predict','full_fit','full_predict','require_increment_release'],NS)
NS['verify_increment']=lambda:None
BD={'np':N,'pd':P,'require':require,'math':math,'old':O,'itertools':__import__('itertools')}
source('error_budget.py',['weights','group_labels','budget','pairs'],BD)
def hconfig():return json.loads((R/'bundle/configs/H_base325_M3_R_original.json').read_bytes())
def toy():return F([{'WELL_ID':'SYNTH_'+str(i),'horizon':h,'RCYL':float(1+i),'__scale035':2.,'f1':float(i+h)} for i in range(10) for h in range(1,13)])
def metadata():return F([{'WELL_ID':'SYNTH_'+str(i),'production_level':float(i),'M_ratio':1.,'M_SCTS_fraction':.9,'scale_fallback':i==9} for i in range(10)])
def folds(p):return [(A(i for i,r in enumerate(p.rows) if int(r['WELL_ID'].split('_')[-1])//2!=k),A(i for i,r in enumerate(p.rows) if int(r['WELL_ID'].split('_')[-1])//2==k)) for k in range(5)]
class Tests(unittest.TestCase):
 def test_H_exact_calendar_fallback_and_future(self):
  t=Month(2040*12+3);hist=F([{'WELL_ID':'SYNTH','NY':t-3,'RCYL':9.,'SCTS':1.},{'WELL_ID':'SYNTH','NY':t-2,'RCYL':2.,'SCTS':1.},{'WELL_ID':'SYNTH','NY':t-1,'RCYL':6.,'SCTS':15.},{'WELL_ID':'SYNTH','NY':t,'RCYL':1e30,'SCTS':1e30}])
  v,s,_=NS['additions'](hist,'SYNTH',t,CF);self.assertEqual(s,2);self.assertEqual(v['M_RCYL'],6);self.assertEqual(v['M_RCYL_ratio'],3);self.assertEqual(v['M_SCTS_fraction'],15/(t-1).days_in_month)
  for bad in [0.,-1.,N.nan,N.inf,-N.inf]:
   q=hist.copy();q.rows[1]['RCYL']=bad;v,s,_=NS['additions'](q,'SYNTH',t,CF);self.assertEqual(s,1);self.assertTrue(math.isnan(v['M_RCYL_ratio']))
  q=F([hist.rows[i] for i in [0,2,3]]);v,s,_=NS['additions'](q,'SYNTH',t,CF);self.assertEqual(s,1)
 def test_H_augmented_order_and_separate_wells(self):
  t=Month(2040*12+3);rows=[];history=[]
  for w in ['SYNTH_A','SYNTH_B']:
   for h in range(1,13):rows.append({'WELL_ID':w,'horizon':h,'anchor_time':t-1,'RCYL':float(h),'__scale035':6.,'f1':1.})
   for m,v in [(t-2,2.),(t-1,6.),(t,1e30)]:history.append({'WELL_ID':w,'NY':m,'RCYL':v,'SCTS':15.})
  p=F(rows);out,features,meta=NS['augment'](p,['f1'],F(history),CF,hconfig());self.assertEqual(list(out['__scale035']),[2.]*24);self.assertEqual(features,['f1',*NS['M3'],*NS['R5']]);self.assertTrue(out[['WELL_ID','horizon']].equals(p[['WELL_ID','horizon']]))
  history[0]['RCYL']=3.;other,_,_=NS['augment'](p,['f1'],F(history),CF,hconfig());self.assertEqual(list(other['__scale035'])[12:],[2.]*12);self.assertEqual(list(other['__scale035'])[:12],[3.]*12)
 def test_H_new_fields_window_poison_and_legal_control(self):
  t=Month(2040*12+3);history=F([{'WELL_ID':'SYNTH','NY':t-2,'RCYL':2.,'SCTS':12.},{'WELL_ID':'SYNTH','NY':t-1,'RCYL':6.,'SCTS':15.},{'WELL_ID':'SYNTH','NY':t,'RCYL':20.,'SCTS':20.}]);v,s,m=NS['additions'](history,'SYNTH',t,CF)
  for col in ['RCYL','SCTS']:
   q=history.copy();q.rows[2][col]=b'\xff\xfe';vv,ss,mm=NS['additions'](q,'SYNTH',t,CF);self.assertEqual(vv,v);self.assertEqual(ss,s);self.assertEqual(mm,m)
  q=history.copy();q.rows[1]['RCYL']=12.;vv,_,_=NS['additions'](q,'SYNTH',t,CF);self.assertEqual(vv['M_RCYL_ratio'],6.)
 def test_T_actual_evaluate_fit_routing_and_splice(self):
  p=toy();fs=folds(p);c={'schema':NS['SCHEMA'],'variant':'SYNTH_T','kind':'T','base':hconfig(),'horizons':[1,2]};calls=[]
  class Provider:
   legacy=CF
   def get(self,c):return p,['f1'],{'identity':'synthetic'},metadata()
  saved={k:NS.get(k) for k in ['fit','predict']}
  def fit(q,*a):calls.append(list(q.index));self.assertEqual(set(q.horizon),{1,2});return None
  NS['fit']=fit;NS['predict']=lambda m,q,c:A([3.]*len(q))
  base=A(50.+i for i in range(120))
  try:result,pred=NS['evaluate'](c,Provider(),fs,None,'synthetic',base)
  finally:NS.update(saved)
  for ids,(tr,va) in zip(calls,fs):self.assertFalse(set(ids)&set(va));self.assertEqual(len(ids),16)
  for r,a,b in zip(p.rows,pred,base):self.assertEqual(a,3. if r['horizon']<=2 else b)
  with self.assertRaisesRegex(RuntimeError,'T_REQUIRES'):NS['evaluate'](c,Provider(),fs,None,'synthetic')
 def test_T_actual_fit_preprocessor_selected_rows_only(self):
  p=toy();sel=NS['specialist_rows'](p,folds(p)[0][0]);seen=[]
  class Prep:
   def fit_transform(self,x,y):seen.append(('prep',list(x.index),len(y)));return x
  class Model:
   def fit(self,x,y):seen.append(('model',list(x.index),len(y)))
  class Ledger:
   def run(self,k,s,f):return f()
  O.training=types.SimpleNamespace(_preprocessor=lambda x:Prep());module=types.ModuleType('models035');module.estimator_for=lambda *a:Model();prior=sys.modules.get('models035');sys.modules['models035']=module
  try:NS['fit'](p.iloc[sel],['f1'],hconfig(),CF,Ledger(),'synthetic')
  finally:
   if prior:sys.modules['models035']=prior
   else:sys.modules.pop('models035')
  self.assertEqual(seen,[('prep',list(sel),16),('model',list(sel),16)])
 def test_cutpoints_ignore_validation_values(self):
  p=toy();m=metadata();fs=folds(p);captured=[];real=N.quantile
  def spy(v,q):captured.append(list(v));return real(v,q)
  N.quantile=spy
  try:BD['group_labels'](p,m,fs);first=captured[0];captured.clear();m.rows[0]['production_level']=1e30;m.rows[1]['production_level']=1e30;BD['group_labels'](p,m,fs);self.assertEqual(first,captured[0])
  finally:N.quantile=real
 def test_detect_wrong_budget_denominator(self):
  p=toy();pred=A(2*r['RCYL'] for r in p.rows);w,e=BD['weights'](p,pred);official=sum(2**(-r['horizon'])*abs(a-r['RCYL'])/(abs(a)+abs(r['RCYL'])+1e-6) for r,a in zip(p.rows,pred))/10
  observed=w.sum()/10;self.assertNotAlmostEqual(observed,official);OBS['wrong_denominator']={'synthetic_budget_total':observed,'synthetic_official_total':official,'official_core_changed':False}
 def test_detect_small_group_complement_disclosure(self):
  p=toy();pred=A(2*r['RCYL'] for r in p.rows);out=BD['budget'](p,pred,metadata(),folds(p));field=out['groups']['scale_fallback'];large=next(x for x in field if x['status']=='REPORTED');small=next(x for x in field if x['status']!='REPORTED')
  restored=out['total_weighted_loss']*out['wells']-large['group_mean_weighted_loss']*large['wells'];w,_=BD['weights'](p,pred);actual=sum(v for v,r in zip(w,p.rows) if r['WELL_ID']=='SYNTH_9');self.assertAlmostEqual(restored,actual);self.assertEqual(small['wells'],'<5');self.assertEqual(out['wells']-large['wells'],1);OBS['complement_disclosure']={'suppressed_synthetic_wells':1,'exact_loss_reconstructible':True}
 def test_config_scope_and_unreleased_gate(self):
  c=hconfig();NS['validate'](c)
  for key,value in [('cutoff','T0_plus_1'),('target',{'transform':'log_ratio','scale':'last_legal'})]:
   q=copy.deepcopy(c);q[key]=value
   with self.assertRaises(RuntimeError):NS['validate'](q)
  with self.assertRaisesRegex(RuntimeError,'CODEX_R14_INCREMENT_REVIEW_REQUIRED'):NS['require_increment_release'](c)
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);res=unittest.TextTestRunner(verbosity=2).run(suite)
 (R/'SOURCE_SYNTHETIC_RESULT.json').write_text(json.dumps({'tests':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'observed_findings':OBS,'A_model_fits':0,'A_preprocessor_fits':0,'method':'exact selected B AST bodies plus stdlib vector/table/fit spies; not real numpy/pandas/sklearn or B 50-case rerun'},indent=2),encoding='utf-8');sys.exit(not res.wasSuccessful())
