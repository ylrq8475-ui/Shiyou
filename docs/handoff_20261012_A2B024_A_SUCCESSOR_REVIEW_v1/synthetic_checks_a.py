"""A-authored adversarial checks plus explicit B pure-suite reruns; no training imports."""
import argparse
from dataclasses import replace
import hashlib
import importlib
import io
import json
import math
from pathlib import Path
import platform
import sys
import unittest
from independent_audit import official_score

class IndependentSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.raw=tuple((f'INVENTED_{i}',v) for i,v in enumerate((0.,-2.,math.nan,math.inf,-math.inf,1.,.001,9.)))
        self.keys=tuple((w,(2026+(10+t)//12)*100+(10+t)%12+1) for w,_ in self.raw for t in range(12))
        self.ident={k:hashlib.sha256(k.encode()).hexdigest() for k in contracts.COMMON_FIELDS}
        self.ident['raw_state']=contracts.raw_digest(self.raw)
        self.b=contracts.Arm(self.keys,tuple(float(i+1) for i in range(96)),dict(self.ident))
        self.c=contracts.Arm(self.keys,tuple(float(150-i) for i in range(96)),dict(self.ident))
    def route(self): return contracts.ExecutionGuard().validate_and_route(self.b,self.c,self.raw,self.keys,self.ident)
    def reject(self, b=None,c=None,raw=None,keys=None,ident=None):
        g=contracts.ExecutionGuard()
        with self.assertRaises(contracts.ContractFailure):g.validate_and_route(b or self.b,c or self.c,self.raw if raw is None else raw,self.keys if keys is None else keys,self.ident if ident is None else ident)
        for stage in ('score','confirmation','fit','save'):
            with self.assertRaises(contracts.ContractFailure):g.assert_stage_allowed(stage)
    def test_official_perfect_and_zero(self):
        self.assertEqual(official_score([[0.]*12],[[0.]*12]),100.)
        self.assertEqual(official_score([[3.]*12],[[3.]*12]),100.)
    def test_official_unnormalized_mass_and_epsilon(self):
        self.assertEqual(sum(1/2**t for t in range(1,5)),.9375)
        self.assertEqual(sum(1/2**t for t in range(1,13)),4095/4096)
        self.assertAlmostEqual(official_score([[0.]*12],[[1.]*12]),100*(1-4095/4096/(1+1e-6)),places=12)
        self.assertAlmostEqual(official_score([[0.]*12],[[1e-6]+[0.]*11]),75.)
    def test_official_equal_well_not_fold_mean(self):
        y=[[0.]*12,[0.]*12,[4.]*12]; p=[[0.]*12,[0.]*12,[1.]*12]
        one=official_score(y[:2],p[:2]); two=official_score(y[2:],p[2:]); whole=official_score(y,p)
        self.assertAlmostEqual(whole,(2*one+two)/3)
        self.assertNotAlmostEqual(whole,(one+two)/2)
    def test_official_matches_public_formula_on_invented_rows(self):
        import pandas as pd
        core=importlib.import_module('experiment_core')
        y=[[float((w+t)%5) for t in range(12)] for w in range(3)]
        p=[[float((w*3+t)%7) for t in range(12)] for w in range(3)]
        frame=pd.DataFrame([(f'INVENTED_{w}',t+1,y[w][t]) for w in range(3) for t in range(12)],columns=['WELL_ID','horizon','RCYL'])
        self.assertAlmostEqual(official_score(y,p),core.score_summary(frame,[x for row in p for x in row])['official_score'],places=12)
    def test_official_missing_month_and_nonfinite_rejected(self):
        for y,p in [([[0.]*11],[[0.]*11]),([[math.nan]*12],[[1.]*12]),([[1.]*12],[[-1.]*12])]:
            with self.assertRaises(ValueError):official_score(y,p)
    def test_cross_year_route_independent_selection(self):
        expected=tuple(v for i,(_,raw) in enumerate(self.raw) for v in (self.b.predictions if math.isfinite(raw) and raw>0 else self.c.predictions)[12*i:12*i+12])
        self.assertEqual(self.route(),expected)
        self.assertEqual(self.route()[60:72],self.b.predictions[60:72])
    def test_route_score_net_contribution(self):
        y=[[float(t+1) for t in range(12)] for _ in self.raw]
        bb=[list(self.b.predictions[i:i+12]) for i in range(0,96,12)]
        rr=[list(self.route()[i:i+12]) for i in range(0,96,12)]
        delta=official_score(y,rr)-official_score(y,bb)
        expected=(official_score(y[:5],rr[:5])-official_score(y[:5],bb[:5]))*5/8
        self.assertAlmostEqual(delta,expected,places=12)
    def test_missing_month_blocks_following_stages(self):
        self.reject(b=replace(self.b,keys=self.keys[:-1],predictions=self.b.predictions[:-1]),c=replace(self.c,keys=self.keys[:-1],predictions=self.c.predictions[:-1]),keys=self.keys[:-1])
    def test_coherent_both_arm_month_gap_rejected(self):
        keys=list(self.keys);keys[1]=(keys[1][0],202702);keys=tuple(keys)
        self.reject(b=replace(self.b,keys=keys),c=replace(self.c,keys=keys),keys=keys)
    def test_each_identity_field_mismatch_blocks(self):
        for field in contracts.COMMON_FIELDS:
            with self.subTest(field=field):self.reject(c=replace(self.c,identity={**self.ident,field:'FAULT'}))
    def test_raw_plus_signed_zero_change_rejected(self):
        self.reject(raw=((self.raw[0][0],-0.),)+self.raw[1:])
    def test_fold_risk_counterexample_is_not_confirmation(self):
        b=[60.,80.,75.,72.,74.];r=[61.,75.,76.,73.,75.]
        risk=contracts.fold_risk(b,r)
        self.assertEqual(risk['difference_of_minima'],1.)
        self.assertEqual(risk['minimum_paired_fold_delta'],-5.)
        result=dict(structure_passed=True,delta_vs_B0=.3,first2_score_delta=.1,fold_risk=risk)
        self.assertTrue(control.fixed_gate(result)['passed']);self.assertFalse(control.fixed_gate(result,True)['passed'])
    def test_confirmation_failure_blocks_unused_budget(self):
        stages=control.Stages()
        for stage in ('fixed_replay','five_later_splits','conditional_confirmation'):
            for _ in range(stages.caps[stage]):stages.complete(stage)
            stages.release(stage,stage!='conditional_confirmation')
        for stage in stages.caps:
            with self.assertRaises(contracts.ContractFailure):stages.check(stage)
        self.assertEqual(sum(stages.completed.values()),70)
    def test_s1_target_algebra_does_not_establish_cause(self):
        for y in (0.,1e-9,1.,31.,1000.):
            self.assertEqual(math.log1p(y/1.),math.log1p(y))
            self.assertAlmostEqual(math.expm1(math.log1p(y))*1.,y)

def main(bundle,out):
    global contracts,control
    before={p.relative_to(bundle).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.rglob('*') if p.is_file()}
    sys.path[:0]=[str(bundle/'runtime'),str(bundle/'source_references')]
    contracts=importlib.import_module('pretrain_contracts');control=importlib.import_module('a24_control')
    stream=io.StringIO();results=[]
    for label,module in [('A_authored',None),('B_contract_rerun','test_pretrain_contracts'),('B_route_rerun','test_route')]:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(IndependentSyntheticTests) if module is None else unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(module))
        stream.write('\n'+label+'\n');r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        results.append(dict(suite=label,tests=r.testsRun,passed=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors)))
    after={p.relative_to(bundle).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.rglob('*') if p.is_file()}
    forbidden=[m for m in sys.modules if m=='a24_runner' or m=='bridge' or m.startswith('sklearn') or m.startswith('oil_uplift')]
    result=dict(signature='账户A（替代接手）独立审核与交付',suites=results,python=platform.python_version(),numpy=importlib.import_module('numpy').__version__,pandas=importlib.import_module('pandas').__version__,bundle_bytes_unchanged=before==after,training_modules_imported=forbidden,real_model_fits=0,real_preprocessor_fits=0,private_data_read=False,B_18_entry_tests='NOT_EXECUTED; B original D:/codex dependency chain absent from portable suite')
    out.mkdir(exist_ok=True)
    (out/'SYNTHETIC_RESULT_A.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'SYNTHETIC_LOG_A.txt').write_text(stream.getvalue(),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))
    if not all(r['passed'] for r in results) or before!=after or forbidden:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args();main(args.bundle.resolve(),args.out)
