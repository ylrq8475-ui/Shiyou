"""Execute selected original function bodies against synthetic dependency spies.

No numpy/pandas/sklearn installation, actual estimator, competition data or ML
fit is used. This tests source dataflow, not a replacement numerical runtime.
"""
import ast,calendar,contextlib,copy,csv,dataclasses,hashlib,io,json,math,os,re,struct,sys,tempfile,types,unittest
from decimal import Decimal
from pathlib import Path
R=Path(__file__).resolve().parent;B=R/'source_runtime'
def require(v,message):
    if not v:raise RuntimeError(message)
def fingerprint(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class V(list):
    def op(self,o,fn):return V(fn(a,b) for a,b in zip(self,o)) if isinstance(o,(V,list)) else V(fn(a,o) for a in self)
    def __eq__(self,o):return self.op(o,lambda a,b:a==b)
    def __ne__(self,o):return self.op(o,lambda a,b:a!=b)
    def __lt__(self,o):return self.op(o,lambda a,b:a<b)
    def __le__(self,o):return self.op(o,lambda a,b:a<=b)
    def __gt__(self,o):return self.op(o,lambda a,b:a>b)
    def __ge__(self,o):return self.op(o,lambda a,b:a>=b)
    def __and__(self,o):return self.op(o,lambda a,b:a and b)
    def __add__(self,o):return self.op(o,lambda a,b:a+b)
    def __sub__(self,o):return self.op(o,lambda a,b:a-b)
    def __mul__(self,o):return self.op(o,lambda a,b:a*b)
    def __truediv__(self,o):return self.op(o,lambda a,b:a/b)
    def __getitem__(self,k):
        if isinstance(k,tuple):return Column(self)
        if isinstance(k,(V,list)):
            return V(v for v,b in zip(self,k) if b) if all(type(x) is bool for x in k) else V(list.__getitem__(self,int(i)) for i in k)
        v=list.__getitem__(self,k);return V(v) if isinstance(k,slice) else v
    def __setitem__(self,k,v):
        if isinstance(k,(list,V)):
            for i,x in zip(k,v):list.__setitem__(self,int(i),x)
        else:list.__setitem__(self,k,v)
    def all(self):return all(self)
    def any(self):return any(self)
    def sum(self):return sum(self)
    def mean(self):return sum(self)/len(self)
    def isna(self):return V(x is None or isinstance(x,float) and math.isnan(x) for x in self)
    def notna(self):return V(not x for x in self.isna())
    def isin(self,values):return V(x in values for x in self)
    def duplicated(self):
        seen=set();out=V()
        for x in self:out.append(x in seen);seen.add(x)
        return out
    def to_numpy(self,dtype=None):return V(dtype(x) if dtype else x for x in self)
    def tolist(self):return list(self)
    def copy(self):return V(self)
    @property
    def iloc(self):return self
    @property
    def loc(self):return self
    def nunique(self):return len(set(self))
    def drop_duplicates(self):return V(dict.fromkeys(self))
class Column(V):pass
class Matrix(list):
    def __mul__(self,o):return Matrix(V(row)*w for row,w in zip(self,o))
class NP:
    nan=float('nan');inf=float('inf');int64=int
    @staticmethod
    def asarray(x,dtype=None):
        x=list(x)
        return Matrix(V(row) for row in x) if x and isinstance(x[0],(V,list)) else V(dtype(v) if dtype else v for v in x)
    @staticmethod
    def full(n,v):return V([v]*n)
    @staticmethod
    def arange(*args):return V(range(*args))
    @staticmethod
    def isfinite(x):return V(math.isfinite(v) for v in x) if isinstance(x,(list,V)) else math.isfinite(x)
    @staticmethod
    def power(a,b):return V(a**x for x in b)
    @staticmethod
    def abs(x):return V(abs(v) for v in x)
    @staticmethod
    def sum(x,axis=None):
        if axis==0:return V(sum(row[i] for row in x) for i in range(len(x[0])))
        return sum(x)
    @staticmethod
    def mean(x):return sum(x)/len(x)
    @staticmethod
    def log1p(x):return V(math.log1p(v) for v in x)
    @staticmethod
    def expm1(x):
        def exp(v):
            try:return math.expm1(v)
            except OverflowError:return float('inf')
        return V(exp(v) for v in x)
    @staticmethod
    def clip(x,minimum,maximum):return V(v if math.isnan(v) else max(v,minimum) for v in x)
class Indexer:
    def __init__(self,frame,loc=False):self.frame=frame;self.loc=loc
    def __getitem__(self,k):
        if isinstance(k,tuple):rows,columns=k;return self[rows][columns]
        if isinstance(k,slice):rows=self.frame.rows[k]
        elif isinstance(k,(V,list)) and all(type(x) is bool for x in k):rows=[r for r,b in zip(self.frame.rows,k) if b]
        elif isinstance(k,(V,list,range)):rows=[self.frame.rows[int(i)] for i in k]
        else:rows=[self.frame.rows[int(k)]]
        return F(rows)
class F:
    def __init__(self,rows):self.rows=[dict(r) for r in rows]
    def __len__(self):return len(self.rows)
    def __iter__(self):return iter(self.columns)
    @property
    def columns(self):return list(self.rows[0]) if self.rows else []
    @property
    def empty(self):return not self.rows
    @property
    def iloc(self):return Indexer(self)
    @property
    def loc(self):return Indexer(self,True)
    def __getitem__(self,k):return F([{n:r[n] for n in k} for r in self.rows]) if isinstance(k,list) else V(r[k] for r in self.rows)
    def __setitem__(self,k,v):
        for r,x in zip(self.rows,v):r[k]=x
    def __getattr__(self,k):
        if k in self.columns:return self[k]
        raise AttributeError(k)
    def copy(self):return F(self.rows)
    def sort_values(self,k,**kwargs):return F(sorted(self.rows,key=lambda r:r[k]))
    def assign(self,**kwargs):
        out=self.copy()
        for k,v in kwargs.items():out[k]=v
        return out
    def equals(self,o):return self.rows==o.rows
    def groupby(self,key,**kwargs):
        order=list(dict.fromkeys(self[key]));return [(w,F([r for r in self.rows if r[key]==w])) for w in order]
    def itertuples(self,index=False,name=None):return iter(tuple(r[k] for k in self.columns) for r in self.rows)
@dataclasses.dataclass(frozen=True,order=True)
class Month:
    serial:int
    def __add__(self,n):return Month(self.serial+n)
    def __sub__(self,n):return Month(self.serial-n)
    @property
    def days_in_month(self):return calendar.monthrange(self.serial//12,self.serial%12+1)[1]
class Dates:
    def __init__(self,values):self.values=V(values)
    @property
    def dt(self):return self
    def to_period(self,unit):return self.values
class PD:
    DataFrame=F
    @staticmethod
    def to_numeric(v,errors=None):
        def number(x):
            try:return float(x)
            except (ValueError,TypeError):return float('nan')
        return V(number(x) for x in v) if isinstance(v,(list,V)) else number(v)
    @staticmethod
    def to_datetime(v,errors=None):return Dates(PD.Timestamp(x).to_period('M') if not isinstance(x,Month) else x for x in v)
    @staticmethod
    def Timestamp(v):
        if isinstance(v,Month):m=v
        else:
            parts=re.findall(r'\d+',v);m=Month(int(parts[0])*12+int(parts[1])-1)
        return types.SimpleNamespace(to_period=lambda unit:m)
    @staticmethod
    def read_csv(stream,encoding='utf-8-sig',sep=','):
        raw=stream.read();text=raw.decode(encoding);rows=[]
        for row in csv.DictReader(io.StringIO(text),delimiter=sep):
            converted={}
            for key,v in row.items():
                if key in ('WELL_ID','NY','CSLB'):converted[key]=v
                else:
                    try:converted[key]=float(v)
                    except (ValueError,TypeError):converted[key]=float('nan')
            rows.append(converted)
        return F(rows)
def selected(filename,names,ns):
    tree=ast.parse((B/filename).read_bytes());nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    require({n.name for n in nodes}==set(names),'SOURCE_FUNCTION_NOT_FOUND');future=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0);mod=ast.Module(body=[future]+nodes,type_ignores=[]);ast.fix_missing_locations(mod);exec(compile(mod,str(B/filename),'exec'),ns);return ns
G={'__name__':__name__,'np':NP,'pd':PD,'Path':Path,'HERE':B,'json':json,'copy':copy,'re':re,'require':require,'file_sha':file_sha,'fingerprint':fingerprint,'contextlib':contextlib,'os':os}
G['SCHEMA']=ast.literal_eval(next(n.value for n in ast.parse((B/'guard035.py').read_bytes()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SCHEMA' for t in n.targets)))
selected('guard035.py',['validate_config','verify_source_lock','require_release','segment','legal_history','row_value','target_scale','response_features','history_features','transform_target','inverse_target'],G)
selected('models035.py',['simplex_weights','choose_weights_on_training_only','resource_gate'],G)
scoring={'__name__':__name__,'np':NP,'pd':PD,'dataclass':dataclasses.dataclass,'DataContractError':RuntimeError,'ConfigurationError':RuntimeError}
selected('src/oil_uplift/scoring.py',['ScoreResult','official_twelve_month_score'],scoring)
projector={'require':require};selected('csv_projection.py',['csv_spans','cell','header_and_rows','key_projection'],projector)
projection_module=types.ModuleType('csv_projection');projection_module.csv_spans=projector['csv_spans'];projection_module.cell=projector['cell']
P=dict(G,key_projection=projector['key_projection'],header_and_rows=projector['header_and_rows'],cell=projector['cell'],io=io)
selected('core.py',['test_keys_and_history'],P)
BASE=json.loads((B/'configs/B0_prime.json').read_bytes());CONFIG={'anchors':{'well_column':'WELL_ID','date_column':'NY','event_column':'CSLB','eligible_event_values':['SYNTH_EVENT']}}
def toy_history():
    rows=[]
    for i in range(18):rows.append({'WELL_ID':'SYNTH_ONLY','NY':Month(2099*12+i),'RCYL':float(i+1),'RCYL1':float(2*(i+1)),'SCTS':20.,'CCJHWND':4.,'CSLB':'SYNTH_EVENT' if i in (14,15) else 'NONE'})
    return F(rows)
def history_spy(frame,wid,t0,cfg):
    assert all(x<t0 for x in PD.to_datetime(frame.NY).to_period('M'));return {'history__RCYL__last':frame.RCYL[-1],'history_month_count':len(frame)}
G['history_values']=history_spy
P['history_values']=history_spy
selected('guard035.py',['history_features','build_variant_test'],P)
def test_fixture(poison=None,change_legal=False,change_key=False):
    c=copy.deepcopy(BASE);cfg=copy.deepcopy(CONFIG);names=[f'SYNTH_FILE_{i}' for i in range(10)];cfg['data']={'csv':{'encoding':'utf-8-sig','delimiter':','},'sources':{'test':{'history':names,'template':names}}};values={};keys=[]
    for i,name in enumerate(names):
        wid=f'SYNTH_{i}';head=b'WELL_ID,NY,RCYL,RCYL1,SCTS,CCJHWND,CSLB\n';prefix=[]
        for y,m in [(2098,9),(2098,10),(2098,11),(2098,12),(2099,1)]:
            oil=999 if change_legal and i==0 else m;event='SYNTH_EVENT' if m==1 else 'NONE';prefix.append(f'{wid},{y}/{m}/1,{oil},{oil*2},20,4,{event}\n'.encode())
        tail=[]
        for h in range(12):
            serial=2099*12+1+h;y,m=divmod(serial,12);date=f'{y}/{m+1}/1';keys.append((wid,date));output_date=date
            if change_key and i==0 and h==0:output_date=f'{y}/{m+1}/2'
            dynamic=b'1,2,20,4,NONE' if poison is None else poison
            tail.append(f'{wid},{output_date},'.encode()+dynamic+b'\n')
        values[name]=head+b''.join(prefix+tail)
    policy={'template_key_sha256':fingerprint(keys),'feature_order':['horizon','forecast_step','history_month_count','history__RCYL__last']}
    class Store:
        def __init__(self):self.calls=0
        def raw(self,name):self.calls+=1;return values[name]
    return Store(),policy,cfg,c
def build_synthetic_test(**kw):
    from unittest.mock import patch
    store,p,cfg,c=test_fixture(**kw)
    with patch.dict(sys.modules,{'csv_projection':projection_module}):return P['build_variant_test'](store,p,cfg,c)
def score_oracle(frame,pred):
    wells={}
    for row,p in zip(frame.rows,pred):wells.setdefault(row['WELL_ID'],[]).append((row['horizon'],row['RCYL'],p))
    scores=[]
    for values in wells.values():
        total=Decimal(0)
        for h,y,p in sorted(values):
            y,p=Decimal(str(y)),Decimal(str(p));total+=abs(p-y)/(abs(p)+abs(y)+Decimal('0.000001'))/(Decimal(2)**h)
        scores.append(100*(1-total))
    return {'official_score':float(sum(scores)/len(scores))}
G['summary']=score_oracle
class SyntheticGroupKFold:
    """Deterministic source-tracing splitter, not sklearn RNG reproduction."""
    def __init__(self,n_splits,**kw):self.n=n_splits
    def split(self,frame,groups):
        wells=list(dict.fromkeys(groups))
        for k in range(self.n):
            valid=set(wells[k::self.n]);yield V(i for i,w in enumerate(groups) if w not in valid),V(i for i,w in enumerate(groups) if w in valid)
G['GroupKFold']=SyntheticGroupKFold;calls=[]
def fit_spy(frame,features,c,cfg,ledger,stage):
    calls.append({'indices':list(frame.row_index),'stage':stage,'wells':set(frame.WELL_ID)});return {'training_indices':set(frame.row_index),'config':c}
def pred_spy(artifact,frame,c):
    require(not artifact['training_indices']&set(frame.row_index),'QUERY_WAS_FITTED');return V(row['RCYL'] if c['variant']=='MEMBER_A' else 0. for row in frame.rows)
G['fit_single']=fit_spy;G['predict_single']=pred_spy
selected('cv035.py',['fit_members_full'],G)
class Provider:
    def __init__(self,alter_validation=False):
        self.config={};self.frame=F([{'row_index':i,'WELL_ID':f'SYNTH_{i//12}','horizon':i%12+1,'RCYL':float(i+1) if not alter_validation or i<96 else 999999.} for i in range(120)])
    def get(self,c):return self.frame,['row_index'],{}
def ensemble():
    a=copy.deepcopy(BASE);a['variant']='MEMBER_A';b=copy.deepcopy(a);b['variant']='MEMBER_B';c=copy.deepcopy(BASE);c['variant']='SYNTH_ENSEMBLE';c['learner']={'name':'Ensemble'};c['fusion']={'method':'inner_grid_0.1','members':[a,b]};return c
class Contracts(unittest.TestCase):
    def test_fixed_source_lock(self):G['verify_source_lock']()
    def test_base_configs(self):
        for name in ['B0','B0_prime']:G['validate_config'](json.loads((B/'configs'/f'{name}.json').read_bytes()))
    def test_unknown_or_unsafe_config_blocked(self):
        mutations=[lambda x:x.update(cutoff='T0_plus_1'),lambda x:x.update(unexpected=True),lambda x:x['evaluation']['repeated'].update(seeds=[6,7,8,9,10]),lambda x:x['evaluation']['fixed'].update(shuffle=True),lambda x:x['learner'].update(random_state=9)]
        for change in mutations:
            c=copy.deepcopy(BASE);change(c)
            with self.subTest(change=change),self.assertRaises(RuntimeError):G['validate_config'](c)
    def test_legacy_cutoff_cannot_be_direct_search(self):
        c=copy.deepcopy(BASE);c.update(cutoff='M_minus_1',purpose='search')
        with self.assertRaisesRegex(RuntimeError,'OLD_CUTOFF_FUSION_ONLY'):G['validate_config'](c)
    def test_search_requires_actual_release_file(self):
        c=copy.deepcopy(BASE);c['purpose']='search'
        with self.assertRaisesRegex(RuntimeError,'CODEX_PIPELINE_RELEASE_REQUIRED'):G['require_release'](c)
    def test_benchmark_name_does_not_authorize_new_config(self):
        G['require_release'](BASE,True);c=copy.deepcopy(BASE);c['learner']['min_samples_leaf']=2
        with self.assertRaisesRegex(RuntimeError,'BENCHMARK_NAME_NOT_AUTHORIZATION'):G['require_release'](c,True)
    def test_all_external_models_currently_blocked(self):
        for name in ['LightGBM','CatBoost','TabPFN_v2','Chronos-2','chronos-bolt-base']:
            with self.subTest(name=name),self.assertRaisesRegex(RuntimeError,'EXTERNAL_MODEL_NOT_RELEASED'):G['resource_gate'](name)
    def test_actual_cutoff_function_excludes_future_and_duplicates(self):
        h=toy_history();t0=Month(2099*12+16);legal,end=G['legal_history'](h,'SYNTH_ONLY',t0,'T0_minus_1',CONFIG);self.assertEqual(end,t0-1);self.assertEqual(len(legal),16)
        bad=F(h.rows+[dict(h.rows[3])])
        with self.assertRaisesRegex(RuntimeError,'DUPLICATE_LEGAL_MONTH'):G['legal_history'](bad,'SYNTH_ONLY',t0,'T0_minus_1',CONFIG)
    def test_legacy_cutoff_uses_event_not_template_gap(self):
        h=toy_history();legal,end=G['legal_history'](h,'SYNTH_ONLY',Month(2099*12+18),'M_minus_1',CONFIG);self.assertEqual(end,Month(2099*12+14));self.assertEqual(len(legal),15)
    def test_future_poison_cannot_change_history_or_scales(self):
        h=toy_history();t0=Month(2099*12+16)
        for cutoff in ['T0_minus_1','M_minus_1']:
            for mode in ['last_legal','last3_valid_mean','presegment3_mean','none']:
                c=copy.deepcopy(BASE);c['cutoff']=cutoff;c['target']={'transform':'log1p' if mode=='none' else 'log_ratio','scale':mode};before=G['history_features'](h,'SYNTH_ONLY',t0,c,CONFIG);changed=h.copy()
                for row in changed.rows[16:]:row['RCYL']=1e15;row['CSLB']='SYNTH_EVENT'
                after=G['history_features'](changed,'SYNTH_ONLY',t0,c,CONFIG);self.assertEqual(before,after)
    def test_raw_last_nonfinite_zero_negative_falls_back(self):
        c=copy.deepcopy(BASE);h=toy_history()
        for v in [0.,-1.,float('nan'),float('inf')]:
            hh=h.copy();hh.rows[-1]['RCYL']=v;self.assertEqual(G['target_scale'](hh,hh.NY[-1],c,CONFIG),1.)
    def test_last_three_natural_months_not_last_three_observations(self):
        c=copy.deepcopy(BASE);c['target']['scale']='last3_valid_mean';h=F([r for i,r in enumerate(toy_history().rows) if i not in (15,16)]);self.assertEqual(G['target_scale'](h,Month(2099*12+17),c,CONFIG),18.)
    def test_presegment_missing_month_falls_back(self):
        c=copy.deepcopy(BASE);c['target']['scale']='presegment3_mean';h=F([r for i,r in enumerate(toy_history().rows) if i!=12]);self.assertEqual(G['target_scale'](h,h.NY[-1],c,CONFIG,(Month(2099*12+14),Month(2099*12+15))),1.)
    def test_consecutive_events_and_R_formulas(self):
        h=toy_history();self.assertEqual(G['segment'](h,CONFIG),(Month(2099*12+14),Month(2099*12+15)));r=G['response_features'](h,CONFIG);self.assertAlmostEqual(r['R1'],16/15);self.assertAlmostEqual(r['R2'],16/13);self.assertAlmostEqual(r['R3'],0);self.assertEqual(r['R4'],0);self.assertAlmostEqual(r['R5'],20/30)
    def test_G_disabled(self):
        c=copy.deepcopy(BASE);c['features']='base325_G'
        with self.assertRaisesRegex(RuntimeError,'GEOLOGY_DISABLED'):G['history_features'](toy_history(),'SYNTH_ONLY',Month(2099*12+16),c,CONFIG)
    def test_leap_year_R5_and_zero_ratio(self):
        m=Month(2104*12+1);h=F([{'NY':m-i,'RCYL':0.,'RCYL1':2.,'SCTS':29.,'CCJHWND':4.} for i in range(4,-1,-1)]);r=G['response_features'](h,CONFIG,(m,m));self.assertEqual(r['R5'],1.);self.assertTrue(math.isnan(r['R1']));self.assertTrue(math.isnan(r['R2']))
    def test_target_scale_transform_and_inverse(self):
        p=F([{'RCYL':6.,'__scale035':2.},{'RCYL':8.,'__scale035':4.}]);z=G['transform_target'](p,BASE);restored=G['inverse_target'](z,p)
        for a,b in zip(restored,p.RCYL):self.assertAlmostEqual(a,b,12)
    def test_inverse_clips_negative_and_rejects_nonfinite(self):
        p=F([{'__scale035':2.}]);self.assertEqual(G['inverse_target'](V([-1.]),p),[0.])
        for x in [float('inf'),float('nan')]:
            with self.assertRaisesRegex(RuntimeError,'PREDICTION_VALIDITY'):G['inverse_target'](V([x]),p)
    def test_negative_target_or_scale_blocks(self):
        for row in [{'RCYL':-1.,'__scale035':1.},{'RCYL':1.,'__scale035':0.}]:
            with self.assertRaisesRegex(RuntimeError,'TARGET_SCALE_VALIDITY'):G['transform_target'](F([row]),BASE)
    def test_projection_never_decodes_bad_dynamic_bytes(self):
        raw=b'WELL_ID,NY,RCYL,flow\r\nSYNTH,2099/02/01,\xff,\xfe\r\n';keys,head=projector['key_projection'](raw,'WELL_ID','NY','utf-8-sig',',');self.assertEqual(keys,[('SYNTH','2099/02/01')])
    def test_projection_quoted_newlines(self):
        raw=b'WELL_ID,NY,RCYL,flow\nSYNTH,2099/02/01,"two\nlines","a,b"\n';self.assertEqual(projector['key_projection'](raw,'WELL_ID','NY','utf-8-sig',',')[0],[('SYNTH','2099/02/01')])
    def test_actual_test_builder_invalid_dynamic_window_invariance(self):
        a,af,aa=build_synthetic_test();b,bf,bb=build_synthetic_test(poison=b'\xff,\xfe,\xff,\xfe,\xff');self.assertEqual(a.rows,b.rows);self.assertEqual(af,bf);self.assertEqual(aa,bb);self.assertEqual(bb['test_window_dynamic_values_decoded'],0);self.assertEqual(len(a),120)
    def test_actual_test_builder_numeric_dynamic_window_invariance(self):
        a,_,_=build_synthetic_test();b,_,_=build_synthetic_test(poison=b'-999,1e300,NaN,Inf,CHANGED');self.assertEqual(a.rows,b.rows)
    def test_actual_test_builder_legal_positive_control_and_other_wells(self):
        a,_,_=build_synthetic_test();b,_,_=build_synthetic_test(change_legal=True);self.assertNotEqual(a.rows[:12],b.rows[:12]);self.assertEqual(a.rows[12:],b.rows[12:])
    def test_actual_test_builder_key_identity_mutation_blocks(self):
        with self.assertRaisesRegex(RuntimeError,'TEMPLATE_IDENTITY_BEFORE_DYNAMIC_ACCESS'):build_synthetic_test(change_key=True)
    def test_official_function_decimal_oracle_and_row_order(self):
        rows=[{'WELL_ID':f'SYNTH_{w}','horizon':h,'truth':float(h+w),'prediction':float((h+w)//2)} for w in range(3) for h in range(1,13)];f=F(rows[::-1]);actual=scoring['official_twelve_month_score'](f,truth_column='truth',prediction_column='prediction').total;oracle=score_oracle(F([{'WELL_ID':r['WELL_ID'],'horizon':r['horizon'],'RCYL':r['truth']} for r in f.rows]),f.prediction)['official_score'];self.assertAlmostEqual(actual,oracle,12)
    def test_official_zero_epsilon_and_unnormalized_mass(self):
        rows=[{'WELL_ID':'SYNTH','horizon':h,'truth':1e-7,'prediction':0.} for h in range(1,13)];s=scoring['official_twelve_month_score'](F(rows),truth_column='truth',prediction_column='prediction').total;self.assertAlmostEqual(s,100*(1-(1-2**-12)/11),12)
        with self.assertRaises(RuntimeError):scoring['official_twelve_month_score'](F(rows),truth_column='truth',prediction_column='prediction',epsilon=1e-5)
    def test_official_nan_inf_and_incomplete_horizons_block(self):
        rows=[{'WELL_ID':'SYNTH','horizon':h,'truth':1.,'prediction':0.} for h in range(1,13)]
        for v in [float('nan'),float('inf')]:
            bad=copy.deepcopy(rows);bad[0]['prediction']=v
            with self.assertRaises(RuntimeError):scoring['official_twelve_month_score'](F(bad),truth_column='truth',prediction_column='prediction')
        with self.assertRaises(RuntimeError):scoring['official_twelve_month_score'](F(rows[:-1]),truth_column='truth',prediction_column='prediction')
    def test_weight_grid_and_training_overlap_block(self):
        grid=G['simplex_weights'](3);self.assertEqual(len(grid),66);self.assertTrue(all(abs(sum(w)-1)<1e-12 for w in grid));p=Provider().frame.iloc[:96]
        with self.assertRaisesRegex(RuntimeError,'OUTER_VALIDATION_ENTERED'):G['choose_weights_on_training_only'](p,[V([1.]*96)]*2,list(range(96)),[0])
    def test_nested_weight_learning_actual_source_scope(self):
        calls.clear();bundle=G['fit_members_full'](ensemble(),Provider(),V(range(96)),None,'SYNTH',V(range(96,120)));self.assertEqual(bundle['weights'],[1.,0.]);self.assertEqual(len(calls),12);self.assertTrue(all(set(x['indices'])<=set(range(96)) for x in calls));self.assertEqual(bundle['weight_evidence']['outer_validation_rows_used'],0)
    def test_outer_labels_do_not_change_weights(self):
        a=G['fit_members_full'](ensemble(),Provider(),V(range(96)),None,'SYNTH_A',V(range(96,120)));b=G['fit_members_full'](ensemble(),Provider(True),V(range(96)),None,'SYNTH_B',V(range(96,120)));self.assertEqual(a['weights'],b['weights'])
    def test_nested_illegal_outer_intersection_blocks_before_spy_fit(self):
        calls.clear()
        with self.assertRaisesRegex(RuntimeError,'INNER_SEES_OUTER_VALIDATION'):G['fit_members_full'](ensemble(),Provider(),V(range(96)),None,'SYNTH_BAD',[0])
        self.assertEqual(calls,[])
if __name__=='__main__':
    log=io.StringIO();run=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts));out={'tests_run':run.testsRun,'success':run.wasSuccessful(),'failures':len(run.failures),'errors':len(run.errors),'A_actual_model_fits':0,'A_actual_preprocessor_fits':0,'competition_data_read':False,'A_runtime':sys.version.split()[0],'scope':'Original selected function bodies with independent synthetic table/vector/splitter/fit spies; not pandas/sklearn runtime or real-data baseline reproduction'}
    with (R/'SYNTHETIC_LOG_CODEX_V4.txt').open('x',encoding='utf-8') as f:f.write(log.getvalue())
    with (R/'SYNTHETIC_RESULT_CODEX_V4.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
    print(json.dumps(out));print(log.getvalue() if not run.wasSuccessful() else 'all synthetic source contracts passed');assert run.wasSuccessful()
