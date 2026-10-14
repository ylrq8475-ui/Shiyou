"""B execution of fixed A2B-026 stage 0. Never trains or saves real rows."""
from pathlib import Path
import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'


def digest_bytes(b):
    return hashlib.sha256(b).hexdigest()


def write_new(path, obj):
    data = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with Path(path).open('x', encoding='utf-8') as f:
        f.write(data)


def main(bridge_dir, prior_task):
    if (HERE/'EVENTS.json').exists() or (HERE/'PRE_DIAGNOSTIC_LOCK.json').exists():
        raise RuntimeError('ALREADY_STARTED_NO_AUTOMATIC_REPEAT')
    sys.path.insert(0, str(Path(bridge_dir)))
    import bridge as b
    sys.path.insert(0, str(HERE/'received/proposal/reference'))
    import diagnostics_reference as d
    np, pd, safe = b.np, b.pd, b.safe
    source_receipt = json.loads((HERE/'SOURCE_RECEIPT.json').read_bytes())

    def verify_sources():
        for label, info in source_receipt.items():
            for name, v in info['files'].items():
                p = HERE/'received'/label/name
                if p.stat().st_size != v['bytes'] or digest_bytes(p.read_bytes()) != v['sha256']:
                    raise RuntimeError('FIXED_SOURCE_CHANGED')

    verify_sources()
    env = b.public_environment()
    env['executable'] = Path(env['executable']).name
    env['native_files'] = {Path(p).name:h for p,h in env['native_files'].items()}
    counts = {'model_fit_attempted':0, 'model_fit_completed':0,
              'preprocessor_fit_attempted':0, 'preprocessor_fit_completed':0}
    patches = []
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
    from sklearn.tree import DecisionTreeRegressor, ExtraTreeRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler, OneHotEncoder
    def block(category):
        def blocked(*args, **kwargs):
            counts[category+'_fit_attempted'] += 1
            raise RuntimeError('FITTING_FORBIDDEN_IN_STAGE0')
        return blocked
    for cls, category in ((Pipeline,'model'),(ColumnTransformer,'preprocessor'),
        (ExtraTreesRegressor,'model'),(HistGradientBoostingRegressor,'model'),
        (DecisionTreeRegressor,'model'),(ExtraTreeRegressor,'model'),
        (SimpleImputer,'preprocessor'),(StandardScaler,'preprocessor'),(OneHotEncoder,'preprocessor')):
        for name in ('fit','fit_transform','partial_fit'):
            if hasattr(cls,name):
                patches.append((cls,name,getattr(cls,name),name in cls.__dict__))
                setattr(cls,name,block(category))
    events = []
    def event(name, **detail):
        e = {'sequence':len(events)+1, 'time':b.prior.stamp(), 'event':name,
             'fit_counts':dict(counts), **detail}
        events.append(e)
        write_new(HERE/f'event_{len(events):03d}.json', e)
        print(json.dumps({'event':name, **detail}, ensure_ascii=True), flush=True)
    store = None
    tick = time.perf_counter()
    result = {'task':'A2B-026','phase':0,'executor':'B','reviewer':'Codex',
              'designer':'Claude','review_status':'PENDING_CODEX_INDEPENDENT_REVIEW',
              'status':'STARTED','started':b.prior.stamp()}
    try:
        event('synthetic_tests_started_before_competition_data_read')
        suite = unittest.defaultTestLoader.loadTestsFromName('test_diagnostics_reference')
        log = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            tests = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        if not tests.wasSuccessful() or tests.testsRun != 12 or any(counts.values()):
            raise RuntimeError('REFERENCE_SYNTHETIC_GATE_FAILED')
        synthetic = {'tests':12,'passed':12,'failures':0,'errors':0,
                     'finished':b.prior.stamp(),'before_first_competition_data_read':True,
                     'fit_counts':dict(counts),'reference_module_sha256':digest_bytes(Path(d.__file__).read_bytes())}
        write_new(HERE/'SYNTHETIC_RESULTS.json',synthetic)
        (HERE/'SYNTHETIC_LOG.txt').write_text(log.getvalue(),encoding='utf-8')
        event('synthetic_tests_passed',tests=12)
        protected = b.old_snapshot()
        for old_root in (Path(prior_task), Path(bridge_dir), Path('D:/codex/A2B024_20261012_v1'),
                         Path('D:/codex/A2B024_R1_PLATFORM_EXPLORE_20261012_v1')):
            for p in old_root.rglob('*'):
                if p.is_file() and '__pycache__' not in p.parts:
                    protected[str(p)] = b.sha(p)
        source_hashes = {str(p):digest_bytes(p.read_bytes()) for p in HERE.rglob('*')
                         if p.is_file() and p.suffix == '.py'}
        authorization_sha = digest_bytes((HERE/'ROLE_AND_AUTHORIZATION.md').read_bytes())
        event('competition_data_read_started_after_synthetic_gate')
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            config = safe.safe_config(b.config_module.load_config(b.prior.PRIVATE_CONFIG))
            store = b.prior.ArchiveStore(b.prior.RAW_ARCHIVE, b.prior.RAW_MANIFEST)
            tt, vt, reader = store.load_tables(config,b.multi.MultiSourceTables)
            baseline, _, train_anchors = safe._build_train_panel(tt, config)
            test, reference, _, test_anchors = safe._build_test_panel(vt, config)
            features = b.training.configured_feature_columns(baseline, config)
        if len(baseline) != 972 or baseline.WELL_ID.nunique() != 81 or len(features) != 325:
            raise RuntimeError('FROZEN_TRAIN_COHORT_FAILED')
        if len(test) != 120 or test.WELL_ID.nunique() != 10 or not test[['WELL_ID','NY']].equals(reference):
            raise RuntimeError('TEST_TEMPLATE_ALIGNMENT_FAILED')
        if set(baseline.WELL_ID) & set(test.WELL_ID):
            raise RuntimeError('TRAIN_TEST_WELL_OVERLAP')
        prior_lock = json.loads((Path(prior_task)/'PREFIT_LOCK.json').read_bytes())
        baseline_id = b.panel_identity(baseline,features)
        if baseline_id != prior_lock['contract']['panel_identity'] or features != prior_lock['contract']['feature_order']:
            raise RuntimeError('FROZEN_BASELINE_PANEL_DRIFT')
        well_col, date_col = config['anchors']['well_column'], config['anchors']['date_column']
        target_col = config['schema']['mapping']['target']
        well_tokens = set(tt.history[well_col].astype(str)) | set(vt.history[well_col].astype(str))
        month_tokens = set()
        for a in (train_anchors,test_anchors):
            for m in a.anchor_period:
                for delta in range(-1,13): month_tokens.add(str(m+delta))

        def values_at_m(history, well, month):
            # Shift only the wrapper cutoff argument; the original M and targets are never shifted.
            return safe._safe_history_values(history,well,month+1,config)

        def candidate_and_audit(history, anchors, original):
            period = safe._periods(history,date_col)
            candidate = original.copy()
            checked, sensitive, shape_mismatch = 0,0,0
            for well,m in anchors[[well_col,'anchor_period']].itertuples(index=False,name=None):
                full = values_at_m(history,well,m)
                cropped = history.loc[(history[well_col]==well) & (period <= m)].copy()
                trimmed = values_at_m(cropped,well,m)
                if full.keys()!=trimmed.keys(): shape_mismatch += 1
                for key in full:
                    checked += 1
                    if key not in trimmed or not safe._same_feature_value(full[key],trimmed[key]): sensitive += 1
                    if key not in candidate.columns: raise RuntimeError('CANDIDATE_NEW_COLUMN')
                    candidate.loc[candidate[well_col]==well,key] = full[key]
            cf = b.training.configured_feature_columns(candidate,config)
            cols_same = cf==features and list(candidate[features].columns)==features
            meta_cols = [c for c in original.columns if c not in features]
            metadata_same = candidate[meta_cols].equals(original[meta_cols])
            return candidate, {'wells_checked':len(anchors),'feature_values_checked':checked,
                'sensitive_feature_count':sensitive,'feature_key_mismatch_wells':shape_mismatch,
                'feature_columns':len(cf),'same_name_and_order_as_B0':cols_same,
                'target_and_key_metadata_unchanged':metadata_same,
                'passed':cols_same and metadata_same and sensitive==0 and shape_mismatch==0}
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ctrain, d0train = candidate_and_audit(tt.history,train_anchors,baseline)
            ctest, d0test = candidate_and_audit(vt.history,test_anchors,test)
        d0 = {'train':d0train,'test':d0test,'passed':d0train['passed'] and d0test['passed'],
              'baseline_feature_count':325,'history_cutoff_for_diagnostic_only':'M',
              'frozen_model_cutoff':'M-1','forecast_index_features_unchanged':2}
        write_new(HERE/'D0_STRUCTURE.json',d0)
        if not d0['passed']: raise RuntimeError('D0_HARD_GATE_FAILED')
        # Verify that no finite future RCYL in test inputs is used as a label.
        test_future_finite = 0
        periods_test = safe._periods(vt.history,date_col)
        for w,m in test_anchors[[well_col,'anchor_period']].itertuples(index=False,name=None):
            vals = pd.to_numeric(vt.history.loc[(vt.history[well_col]==w) & (periods_test>m),target_col],errors='coerce')
            test_future_finite += int(np.isfinite(vals).sum())
        if test_future_finite: raise RuntimeError('UNEXPECTED_FINITE_TEST_FUTURE_TARGETS')
        def raw_month(history, anchors, delta):
            periods = safe._periods(history,date_col)
            values=[]
            for w,m in anchors[[well_col,'anchor_period']].itertuples(index=False,name=None):
                col = history.loc[(history[well_col]==w) & (periods==m+delta),target_col]
                if len(col)>1: raise RuntimeError('DUPLICATE_RAW_ANCHOR_MONTH')
                values.append(float(pd.to_numeric(col,errors='coerce').iloc[0]) if len(col) else float('nan'))
            return np.asarray(values,float)
        targets=[]
        for w in train_anchors[well_col]:
            group=baseline.loc[baseline[well_col]==w].sort_values('horizon',kind='mergesort')
            if group.horizon.tolist()!=list(range(1,13)): raise RuntimeError('TARGET_HORIZON_ALIGNMENT')
            y=group.RCYL.to_numpy(dtype=float)
            if not np.isfinite(y).all() or (y<0).any(): raise RuntimeError('TARGET_VALUES_INVALID')
            targets.append(y)
        am,am1=raw_month(tt.history,train_anchors,0),raw_month(tt.history,train_anchors,-1)
        tm,tm1=raw_month(vt.history,test_anchors,0),raw_month(vt.history,test_anchors,-1)
        test_both=int((np.isfinite(tm)&(tm>0)&np.isfinite(tm1)&(tm1>0)).sum())
        lock = {'task':'A2B-026','phase':0,'time':b.prior.stamp(),
            'before_new_real_diagnostic_scores':True,'roles_commit':source_receipt['roles']['commit'],
            'proposal_commit':source_receipt['proposal']['commit'],'environment':env,
            'source_receipt_sha256':digest_bytes((HERE/'SOURCE_RECEIPT.json').read_bytes()),
            'execution_source_sha256':digest_bytes(Path(__file__).read_bytes()),
            'role_and_authorization_sha256':authorization_sha,'synthetic_sha256':digest_bytes((HERE/'SYNTHETIC_RESULTS.json').read_bytes()),
            'reference_sha256':digest_bytes(Path(d.__file__).read_bytes()),'DECISION':d.DECISION,
            'private_config_sha256':b.sha(b.prior.PRIVATE_CONFIG),
            'raw_archive_sha256':store.archive_hash,'raw_manifest_sha256':store.manifest_hash,
            'input_panel_identity':baseline_id,'candidate_panel_identity':b.panel_identity(ctrain,features),
            'feature_order_sha256':b.fingerprint(features),
            'candidate_ordered_dtype_sha256':b.fingerprint(list(zip(features,ctrain[features].dtypes.astype(str)))),
            'raw_anchor_pair_input_sha256':digest_bytes(np.column_stack((am,am1)).tobytes()),
            'D0':d0,'test_both_anchors_finite_positive_wells':test_both,
            'train_wells':81,'train_rows':972,'test_wells':10,'test_rows':120,
            'protected_frozen_files':len(protected),'protected_snapshot_sha256':b.fingerprint(protected),
            'model_fits_allowed':0,'preprocessor_fits_allowed':0,'historical_dtype':'UNKNOWN',
            'D4_implementation':'unmodified sequential 261 slopes x 801 level multipliers, twice per well',
            'D4_interpretation':'finite label-oracle grid; no universal continuous-curve or platform upper-bound claim',
            'current_anchor_and_target_window_changed':False,'raw_data_copied':False}
        write_new(HERE/'PRE_DIAGNOSTIC_LOCK.json',lock)
        event('structure_passed_diagnostic_lock_saved',train_checks=d0train['feature_values_checked'],test_checks=d0test['feature_values_checked'])
        d1=d.zero_month_mass(targets)
        write_new(HERE/'D1_ZERO_MASS.json',d1)
        event('D1_completed',wells=d1['wells'])
        d2=d.compare_anchors(targets,am,am1)
        write_new(HERE/'D2_ANCHOR_COMPARISON.json',d2)
        event('D2_completed',wells_compared=d2['wells_compared'],test_both_positive=test_both)
        event('D4_original_finite_grid_started',wells=81)
        d4=d.smooth_oracle_scores(targets)
        write_new(HERE/'D4_SMOOTH_ORACLE.json',d4)
        event('D4_completed',wells=d4['wells'])
        zero=d1['max_recoverable_points_if_perfect_zero_detection']
        info=d2['delta_score_M_minus_M1']
        info_gate=info>=d.DECISION['G_INFO']['run_route_A_stage1_if_delta_score_ge'] and d2['delta_first2_loss_M_minus_M1']<0
        decision = {
            'D0':'PASS','G_ZERO': 'ACTIVATE_ROUTE_B_DESIGN' if zero>=d.DECISION['G_ZERO']['activate_route_B_if_points_ge'] else 'ELIMINATE_ROUTE_B' if zero<d.DECISION['G_ZERO']['eliminate_route_B_if_points_lt'] else 'KEEP_ROUTE_B_RESERVE',
            'G_INFO':'STAGE1_ELIGIBLE_PENDING_APPROVAL_AND_CODEX_REVIEW' if info_gate else 'ELIMINATE_ROUTE_A' if info<=d.DECISION['G_INFO']['eliminate_route_A_if_delta_score_le'] else 'WEAK_OR_UNMET_FIRST2_SIGNAL_NO_AUTOMATIC_EXECUTION',
            'G_CEIL':'95_NOT_CREDIBLE_UNDER_REGISTERED_DIAGNOSTIC_POLICY' if d4['smooth_plus_zero_oracle_score']<d.DECISION['G_CEIL']['declare_95_not_credible_if_smooth_plus_zero_oracle_lt'] else 'SMOOTH_ZERO_GRID_NOT_REJECTED_AT_90',
            'report_order':['D0_HARD_GATE','G_CEIL','G_INFO','G_ZERO'],
            'thresholds_unmodified':True,'phase1_executed':False,'machine_decision_is_not_user_approval':True}
        event('registered_decisions_computed')
        verify_sources()
        sources_unchanged=all(digest_bytes(Path(p).read_bytes())==h for p,h in source_hashes.items())
        frozen_unchanged=all(Path(p).is_file() and b.sha(p)==h for p,h in protected.items())
        if not sources_unchanged or not frozen_unchanged or not store.unchanged() or any(counts.values()):
            raise RuntimeError('INTEGRITY_OR_ZERO_FIT_GATE_FAILED')
        result.update(status='COMPLETED',D0=d0,D1=d1,D2=d2,D4=d4,decisions=decision,
            test_both_anchors_finite_positive_wells=test_both,
            target_template_and_well_isolation_passed=True,test_labels_read=False,
            test_future_finite_target_count=0,raw_members_verified=reader['raw_files_verified'],
            source_unchanged=True,frozen_files_unchanged=True,frozen_files_checked=len(protected),
            raw_archive_and_manifest_unchanged=True,raw_data_copied=False,
            private_config_unchanged=b.sha(b.prior.PRIVATE_CONFIG)==lock['private_config_sha256'],
            phase1_training=False,models_loaded_or_saved=False,formal_submission_generated=False,platform_uploaded=False)
        result.update(finished=b.prior.stamp(),seconds=time.perf_counter()-tick,fit_counts=dict(counts))
        write_new(HERE/'RESULT_STAGE0.json',result)
        event('stage0_completed',status='COMPLETED')
        write_new(HERE/'EVENTS.json',events)
        # Full exact in-memory private tokens; no identifiers are written as scan findings.
        report_files=[p for p in HERE.iterdir() if p.is_file() and p.suffix in {'.json','.md','.txt','.py'}]
        tokens=well_tokens | month_tokens | {str(x) for x in config['anchors']['eligible_event_values'] if isinstance(x,str) and len(x)>=2}
        token_hits=0
        generic_hits=0
        for p in report_files:
            text=p.read_text(encoding='utf-8-sig')
            for token in tokens:
                if re.search(r'(?<![\w])'+re.escape(token)+r'(?![\w])',text):token_hits+=1
            generic_hits+=bool(re.search(r'(?i)(gh[pousr]_[a-z0-9]{20,}|github_pat_|wxid_|C:[\\/]Users[\\/])',text))
        privacy={'passed':token_hits==0 and generic_hits==0,'scanned_files':len(report_files),
            'exact_private_token_hits':token_hits,'generic_credential_or_user_path_hits':generic_hits,
            'identifier_tokens_checked':len(well_tokens),'actual_calendar_month_tokens_checked':len(month_tokens),
            'raw_rows_targets_predictions_or_well_mappings_serialized':False,'new_model_and_preprocessor_fits':0}
        write_new(HERE/'PRIVACY_SCAN.json',privacy)
        if not privacy['passed']:raise RuntimeError('PRIVACY_GATE_FAILED')
        print(json.dumps({'status':'COMPLETED','decisions':decision,'fit_counts':counts,
                         'D1_points':zero,'D2_delta':info,'D4_scores':d4},ensure_ascii=True),flush=True)
    except Exception as exc:
        failure={'status':'STOPPED','error_type':type(exc).__name__,
                 'error_code':str(exc) if isinstance(exc,RuntimeError) else 'DETAIL_SUPPRESSED',
                 'fit_counts':dict(counts),'finished':b.prior.stamp()}
        write_new(HERE/'STOPPED.json',failure)
        print(json.dumps(failure,ensure_ascii=True),flush=True)
        raise SystemExit(1)
    finally:
        if store is not None:store.close()
        for cls,name,old,own in reversed(patches):
            if own:setattr(cls,name,old)
            else:delattr(cls,name)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--bridge-dir',required=True)
    parser.add_argument('--prior-task',required=True)
    args=parser.parse_args()
    main(args.bridge_dir,args.prior_task)
