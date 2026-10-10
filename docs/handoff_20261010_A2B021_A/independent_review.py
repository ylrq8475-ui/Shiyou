"""Account A: independent aggregate arithmetic and synthetic checks, no real fit."""
from pathlib import Path
from datetime import datetime
import contextlib, hashlib, io, json, math, statistics, sys, unittest
from collections import Counter

HERE=Path(__file__).resolve().parent
ROOT=HERE/'bundle'; PAYLOAD=ROOT/'payload'; EX=PAYLOAD/'execution'
SEEDS=[None,20260917,20261031,20261219,20270107,20270303]
ARMS=['B0','C1','C2','C3','F12','F13','F23']
FUSIONS={'F12':('C1','C2'),'F13':('C1','C3'),'F23':('C2','C3')}

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def close(a,b):return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=0,abs_tol=1e-10)
CHECKS=[]
def check(ok,name):
    CHECKS.append({'check':name,'passed':bool(ok)})
    if not ok:raise AssertionError(name)
def same(a,b,name):check(close(float(a),float(b)),name)

def official(rows,pred):
    """Pure Python oracle; identifiers and all values here are synthetic only."""
    if len(rows)!=len(pred):raise ValueError('length')
    wells={}
    for (well,t,y),p in zip(rows,pred,strict=True):
        if isinstance(t,bool) or not isinstance(t,int) or not 1<=t<=12:raise ValueError('month')
        if not all(math.isfinite(float(v)) and v>=0 for v in [y,p]):raise ValueError('value')
        item=wells.setdefault(well,{})
        if t in item:raise ValueError('duplicate')
        item[t]=(abs(p-y)/(abs(p)+abs(y)+0.000001))/2**t
    if not wells or any(set(v)!=set(range(1,13)) for v in wells.values()):raise ValueError('window')
    return 100*(1-statistics.mean(math.fsum(v.values()) for v in wells.values()))

def aggregate_review():
    manifest=read(ROOT/'SHA256SUMS_REVIEW.json')
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
    check(set(manifest)==actual-{'SHA256SUMS_REVIEW.json'},'352_manifest_coverage')
    for n,v in manifest.items():
        p=ROOT/n;check(sha(p)==v['sha256'] and p.stat().st_size==v['bytes'],'manifest:'+n)
    for p in (ROOT/'tools').glob('*.py'):
        other=PAYLOAD/p.name
        if other.exists():check(sha(p)==sha(other),'execution_tool_byte_binding:'+p.name)
    lock=read(EX/'IMPLEMENTATION_PRETRAIN_LOCK.json');plan=read(PAYLOAD/'PLAN.json')
    check(sha(PAYLOAD/'USER_AUTHORIZATION_REVISED.txt')==plan['authorization']['sha256'],'authorization_hash')
    bindings=[];unavailable=0
    for n,h in lock['source_and_input_files'].items():
        normalized=n.replace('\\','/')
        p=None
        if '/A2B021_20261009_v1/' in normalized:p=PAYLOAD/normalized.split('/A2B021_20261009_v1/',1)[1]
        elif '/project/src/' in normalized:p=ROOT/'upstream/src'/normalized.split('/project/src/',1)[1]
        elif normalized.endswith('/boundary_audit.py'):p=ROOT/'upstream/accepted_boundary_audit.py'
        elif '/A2B019_T1_20261009_v1/' in normalized and normalized.split('/')[-1] in {'archive_adapter.py','paired_experiment.py','t1_core.py'}:p=ROOT/'tools'/normalized.split('/')[-1]
        if p is not None and p.exists():check(sha(p)==h,'prefit_source_binding:'+str(p.relative_to(ROOT)));bindings.append(str(p.relative_to(ROOT)))
        else:unavailable+=1
    check(len(lock['full_feature_order'])==325 and not any(x.startswith(('layer__','plan_first__')) for x in lock['full_feature_order']),'325_no_layer_plan')
    check(all(x==0 for x in lock['initial_budget'].values()),'initial_zero_budget')
    check(sha(ROOT/'upstream/accepted_boundary_audit.py')=='753762da9a7e0a7c7f734587a458b961dbdd00d9eb4e4f489d1cbb0a659ddf67','accepted_entry_identity')
    for arm in ['B0','C1','C2','C3']:
        check(lock['model_and_preprocess_contracts'][arm]['model_get_params']==plan['complete_model_get_params'][arm],'actual_params:'+arm)
    c2=plan['complete_model_get_params']['C2'];c3=plan['complete_model_get_params']['C3']
    check({k:v for k,v in c2.items() if k!='loss'}=={k:v for k,v in c3.items() if k!='loss'},'C2_C3_loss_only_difference')
    check(plan['families']['repeated_seeds']==SEEDS[1:] and plan['families']['confirmation_seed']==20271009,'locked_seeds')
    events=[read(p) for p in sorted((EX/'events').glob('*.json'))]
    counts=Counter(e['event'] for e in events)
    check(dict(counts)=={'model_fit_entered':120,'fit_completed':120,'fold_completed':30},'event_counts')
    first=events[0];clarification=read(PAYLOAD/'NUMBERING_AND_EXECUTION_CLARIFICATION.json')
    check(datetime.fromisoformat(clarification['recorded_at'])<datetime.fromisoformat(lock['locked_at'])<datetime.fromisoformat(first['time']),'authorization_lock_fit_sequence')
    entered={};completed={};folds={};i=0
    for e in events:
        if e['event'] in {'model_fit_entered','fit_completed'}:
            tag=e['tag'];k=(tag['seed'],tag['fold'],tag['arm'])
            check(tag['stage']=='research' and tag['seed'] in SEEDS and tag['arm'] in ARMS[:4],f'research_only_event:{i}')
            target=entered if e['event']=='model_fit_entered' else completed
            check(k not in target,'unique_fit_event:'+str(i));target[k]=e
            if e['event']=='model_fit_entered':
                i+=1;check(e['train_wells'] in [64,65] and e['train_rows']==e['train_wells']*(12 if tag['arm']=='B0' else 2),'observed_scope:'+str(i))
                check(e['budget']['model_entered']==i and e['budget']['model_completed']==i-1,'entry_budget:'+str(i))
            else:
                check(k in entered and e['actual_calls']=={'preprocess':1,'model':1},'fit_complete_calls:'+str(i))
                check(e['budget']=={'pipeline_attempts':i,'preprocess_entered':i,'preprocess_completed':i,'model_entered':i,'model_completed':i,'retries_used':0},'completion_budget:'+str(i))
        else:
            k=(e['seed'],e['fold']);check(k not in folds,'unique_fold_event');folds[k]=e
            check(e['well_intersection']==0 and e['late_inheritance_checked'] is True,'runtime_isolation_and_late_claim')
    expected={(s,f,a) for s in SEEDS for f in range(1,6) for a in ARMS[:4]}
    check(set(entered)==set(completed)==expected,'all_120_registered_fits')
    families=[]
    for s in SEEDS:
        name='FIXED_FIVE_FOLD.json' if s is None else f'REPEAT_{s}.json'
        r=read(EX/name);check(r['seed']==s and r['structural_checks_passed'],'family_identity');families.append(r)
        well_counts=[81-entered[(s,f,'B0')]['train_wells'] for f in range(1,6)]
        check(sum(well_counts)==81,'OOF_well_counts')
        for arm,v in r['arms'].items():
            check(arm in ARMS and v['well_count']==81,'arm_and_well_count')
            u=v['monthly_unweighted_relative_error'];w=v['monthly_official_weighted_loss']
            check(len(u)==len(w)==12,'12_month_summary')
            for t in range(12):same(w[t],u[t]/2**(t+1),'monthly_weight')
            same(v['official_score'],100*(1-math.fsum(w)),'score_from_months')
            for n in [1,2,4,12]:same(v['official_weighted_prefix_loss'][str(n)],math.fsum(w[:n]),'prefix_loss')
            fs=v['fold_scores'];same(v['official_score'],math.fsum(a*n for a,n in zip(fs,well_counts))/81,'equal_well_fold_aggregation')
            same(v['worst_fold'],min(fs),'worst_fold');same(v['fold_std_ddof0'],statistics.pstdev(fs),'fold_ddof0')
            base=r['arms']['B0'];same(v['delta_vs_B0'],v['official_score']-base['official_score'],'family_delta')
            for f in range(1,6):
                same(fs[f-1],folds[(s,f)]['scores'][arm],'fold_event_binding')
                same(v['paired_fold_deltas'][f-1],fs[f-1]-base['fold_scores'][f-1],'paired_fold_delta')
            if arm!='B0':
                for t in range(2,12):same(w[t],base['monthly_official_weighted_loss'][t],'late_loss_unchanged')
            d=v['diagnostics'];same(d['improvement_distribution']['net_score_delta'],v['delta_vs_B0'],'diagnostic_net_gain')
            changes=d['monthly_net_weighted_loss_change_vs_B0']
            for t in range(12):same(changes[t],w[t]-base['monthly_official_weighted_loss'][t],'monthly_delta_binding')
            for groups in ['prediction_state_groups','retrospective_target_slices']:
                for g in d[groups].values():
                    if g['status']=='RELEASED':
                        check(g['group_wells']>=5 and g['complement_wells']>=5 and g['group_wells']+g['complement_wells']==81,'group_privacy_min')
                        same(g['net_loss_change_contribution_all_wells'],-g['score_delta_vs_B0_in_group']/100*g['group_wells']/81,'group_gain_identity')
    final=read(EX/'FINAL_RESULT.json');decision=read(EX/'RESEARCH_DECISION_LOCK.json')
    comparison=read(HERE/'received/MODEL_COMPARISON.json')['comparisons'];table=[]
    for arm in ARMS[1:]:
        scores=[r['arms'][arm]['official_score'] for r in families[1:]]
        delta=[r['arms'][arm]['official_score']-r['arms']['B0']['official_score'] for r in families[1:]]
        mean=statistics.mean(delta);positive=sum(x>0 for x in delta);worst=min(delta)
        passes=mean>=.2 and positive>=4 and worst>=-.2
        g=final['research_gates'][arm]
        same(g['mean_delta'],mean,'gate_mean');check(g['positive_repeats']==positive,'gate_direction');same(g['worst_repeat_delta'],worst,'gate_worst')
        check(g['mean_passed']==(mean>=.2) and g['direction_passed']==(positive>=4) and g['worst_passed']==(worst>=-.2),'gate_boolean_conditions')
        if arm in FUSIONS:
            pair=FUSIONS[arm];means={c:statistics.mean(r['arms'][c]['official_score'] for r in families[1:]) for c in pair}
            reference=min(pair,key=lambda c:(-means[c],ARMS.index(c)))
            extra=statistics.mean(scores)-means[reference]
            check(g['locked_reference_component']==reference,'fusion_locked_reference');same(g['mean_gain_over_reference'],extra,'fusion_extra_gain')
            check(g['reference_gain_passed']==(extra>=.05),'fusion_extra_gate');passes=passes and extra>=.05
        check(g['passed']==passes and not passes,'failed_qualification_independently')
        check(decision['gates'][arm]==g,'decision_gate_binding')
        v=next(v for v in comparison if v['model_id']==arm)
        same(v['fixed_score'],families[0]['arms'][arm]['official_score'],'comparison_fixed_binding')
        same(v['repeat_mean_delta'],mean,'comparison_repeat_binding')
        table.append({'arm':arm,'fixed_score':v['fixed_score'],'repeat_mean_delta':mean,'positive_repeats':positive,'worst_repeat_delta':worst,'qualified':passes})
    check(final['qualified']==final['confirmed']==decision['qualified']==[],'nothing_qualified_or_confirmed')
    check(not final.get('confirmation') and final['confirmation_gates']=={} and final['artifacts']=={},'stop_before_confirmation_and_save')
    check(final['budget']==events[-1]['budget'] and final['status']=='COMPLETED_NO_QUALIFIED_MODEL','final_stop_accounting')
    check(not (EX/'CONFIRMATION.json').exists() and not (PAYLOAD/'private_models').exists(),'no_confirmation_artifact')
    check(final['current_inputs_unchanged'] and final['environment_unchanged'] and final['old_artifacts_after']==lock['old_artifact_integrity'],'B_reported_freeze_consistency')
    return {'manifest_resources':len(manifest),'prefit_bindings_available':len(bindings),'prefit_private_or_historical_files_not_in_package':unavailable,
            'B_event_counts':dict(counts),'B_successful_model_fits':120,'B_preprocess_fits':120,'B_confirmation_or_full_fit':0,
            'aggregate_checks':len(CHECKS),'all_aggregate_checks_pass':True,'candidate_table':table,
            'scope':'independent aggregate arithmetic and source review; B real-fit events are not an A real reproduction',
            'historical_dtype':'UNKNOWN','event_semantics_and_forecast_time_P0':'OPEN'}

class IndependentOracleTests(unittest.TestCase):
    def frame(self, truths=None):
        import pandas as pd
        vals=truths or [[1.]*12,[2.]*12]
        rows=[('SYNTHETIC_'+str(i),t+1,y) for i,values in enumerate(vals) for t,y in enumerate(values)]
        return rows,pd.DataFrame(rows,columns=['WELL_ID','horizon','RCYL'])
    def test_independent_exact_zero_prediction(self):
        rows,_=self.frame();self.assertAlmostEqual(official(rows,[0.]*24),100*(1-statistics.mean((1-2**-12)*y/(y+1e-6) for y in [1.,2.])),12)
    def test_all_zero_is_100(self):
        rows,_=self.frame([[0.]*12]*2);self.assertEqual(official(rows,[0.]*24),100)
    def test_official_B_against_independent_oracle(self):
        from experiment_core import score_summary
        rows,f=self.frame();p=[.3+i*.1 for i in range(24)];self.assertAlmostEqual(official(rows,p),score_summary(f,p)['official_score'],12)
    def test_permutation_is_not_month_reversal(self):
        from experiment_core import score_summary
        rows,f=self.frame();p=[0.]*24;p[0]=7.;p[23]=8.
        self.assertAlmostEqual(official(rows,p),score_summary(f.iloc[::-1],p[::-1])['official_score'],12)
    def test_invalid_predictions_block(self):
        from experiment_core import score_summary,GateError
        rows,f=self.frame()
        for x in [-1.,float('nan'),float('inf')]:
            p=[1.]*24;p[0]=x
            with self.subTest(kind=str(x)):
                with self.assertRaises(ValueError):official(rows,p)
                with self.assertRaises(GateError):score_summary(f,p)
    def test_incomplete_and_duplicate_block(self):
        from experiment_core import score_summary,GateError
        rows,f=self.frame()
        with self.assertRaises(ValueError):official(rows[:-1],[1.]*23)
        with self.assertRaises(GateError):score_summary(f.iloc[:-1],[1.]*23)
        f.loc[11,'horizon']=11
        with self.assertRaises(GateError):score_summary(f,[1.]*24)
    def test_first_four_weights_are_not_normalized(self):
        self.assertEqual(sum(1/2**t for t in range(1,5)),.9375)
        self.assertEqual(sum(1/2**t for t in range(1,13)),1-2**-12)
    def test_epsilon_at_small_scale(self):
        from experiment_core import score_summary
        rows,f=self.frame([[1e-6]*12]*2);p=[0.]*24
        self.assertAlmostEqual(official(rows,p),50.01220703125,12)
        self.assertAlmostEqual(official(rows,p),score_summary(f,p)['official_score'],12)
    def test_per_well_equal_weight(self):
        from experiment_core import score_summary
        rows,f=self.frame([[1.]*12,[100.]*12]);p=[1.]*12+[0.]*12
        self.assertAlmostEqual(official(rows,p),score_summary(f,p)['official_score'],12)
    def test_late_prediction_drift_blocks(self):
        import numpy as np
        from experiment_core import fusion_prediction,GateError
        h=np.tile(np.arange(1,13),2);b=np.ones(24);p=b.copy();p[5]+=1e-12
        with self.assertRaises(GateError):fusion_prediction(p,b,b,h)

def synthetic_review():
    sys.path.insert(0,str(ROOT/'tools'));sys.dont_write_bytecode=True
    counters={'blocked_real_fit_attempts':0,'blocked_completed_execution_entries':0}
    def guard(frame,event,arg):
        if event!='call':return
        filename=frame.f_code.co_filename.replace('\\','/').lower();name=frame.f_code.co_name
        if '/sklearn/' in filename and name in {'fit','fit_transform','partial_fit','_fit'}:
            counters['blocked_real_fit_attempts']+=1;raise RuntimeError('A_REAL_FIT_FORBIDDEN')
        if filename.endswith(('/run_research.py','/paired_experiment.py')) and name=='execute':
            counters['blocked_completed_execution_entries']+=1;raise RuntimeError('A_EXECUTION_FORBIDDEN')
    import importlib
    loader=unittest.TestLoader();suite=unittest.TestSuite()
    for module in ['test_contracts','test_harness']:suite.addTests(loader.loadTestsFromModule(importlib.import_module(module)))
    suite.addTests(loader.loadTestsFromTestCase(IndependentOracleTests))
    log=io.StringIO()
    try:
        sys.setprofile(guard)
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    finally:sys.setprofile(None)
    with (HERE/'A_SYNTHETIC_TESTS.log').open('x',encoding='utf-8') as f:f.write(log.getvalue())
    out={'test_cases':result.testsRun,'B_packaged_synthetic_cases':30,'A_independent_oracle_cases':10,
         'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),**counters,'real_fits':0}
    check(result.wasSuccessful() and not any(counters.values()),'synthetic_and_no_fit_guard')
    return out

def main():
    before={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*') if p.is_file()}
    result=aggregate_review();result['synthetic']=synthetic_review()
    after={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*') if p.is_file()}
    check(before==after,'B_evidence_unchanged_by_A')
    result['aggregate_checks']=len(CHECKS);result['B_evidence_files_unchanged']=len(before)
    result['A_real_fit_count']=0;result['A_training_or_deployment_authorization']=False
    with (HERE/'A_INDEPENDENT_REVIEW.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    with (HERE/'A_CHECK_DETAILS.json').open('x',encoding='utf-8') as f:json.dump(CHECKS,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
