"""Execute only R9 B T1–T3; all private data stay in memory."""
import argparse,hashlib,io,json,platform,subprocess,sys,time,zipfile
from collections import Counter
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone,timedelta
import numpy as np,pandas as pd,yaml
from audit_core import *
R9='493eabed3a83d646182787fd65dd070f652a4780'
EXPECTED_KEYS='6f27b2b7eb8880428aac42935a34fce881a8af8d089838df3983767887c87c58'
EXPECTED_LABELS='4e7db99d009ade76143f37ceed1a5370f0997e328cd77ee97e1f530aca4fbcda'
def name(info):
    text=info.filename
    if not info.flag_bits&0x800:
        try:text=text.encode('cp437').decode('gb18030')
        except UnicodeError:pass
    text=text.replace('\\','/');require(not PurePosixPath(text).is_absolute() and '..' not in PurePosixPath(text).parts and ':' not in text,'UNSAFE_MEMBER');return text
def main(a):
    started=time.perf_counter();root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
    def save(n,v):(root/n).write_bytes(encoded(v))
    paths={k:Path(getattr(a,k)) for k in ('archive','manifest','config','template_receipt','scoring_source')};before={k:sha(v.read_bytes()) for k,v in paths.items()}
    require(before['config']=='89e60c301b1d553b1c7dab8e2f87d1d9a47b600abe4322f2e9895717201c0c72','CONFIG_IDENTITY')
    receipt=json.loads(paths['template_receipt'].read_bytes());require(receipt['test_key_sha256']==EXPECTED_KEYS,'TEMPLATE_RECEIPT_IDENTITY')
    cfg=yaml.safe_load(paths['config'].read_bytes());manifest=json.loads(paths['manifest'].read_bytes());well,date,event=tuple(cfg['anchors'][k] for k in ('well_column','date_column','event_column'));target=cfg['schema']['mapping']['target'];roles=cfg['data']['sources'];settings=cfg['data']['csv'];encoding=settings.get('encoding','utf-8-sig');delimiter=settings.get('delimiter',',')
    require(cfg['anchors']['first_forecast_month_offset']==1 and cfg['anchors']['horizon_months']==12 and cfg['scoring']['epsilon']==1e-6,'FROZEN_CONTRACT')
    environment={'python':sys.version,'build':platform.python_build(),'numpy':np.__version__,'pandas':pd.__version__,'PyYAML':yaml.__version__,'ML_modules_imported':any(x.startswith(('sklearn','xgboost','lightgbm','catboost')) for x in sys.modules)}
    save('IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json',{'time':datetime.now(timezone(timedelta(hours=8))).isoformat(),'R9_commit':R9,'input_hashes':before,'source_hashes':{p:sha((Path(__file__).parent/p).read_bytes()) for p in ('audit_core.py','run_audit.py','test_audit.py','PLAN_R9.json')},'environment':environment,'model_fit_budget':0,'preprocessor_fit_budget':0,'no_candidate_scores_viewed':True,'template_keys_method':'candidate last 12 calendar keys per declared test CSV must exactly match prior locked ordered template key SHA256 BEFORE dynamic history access; no RCYL missingness inspected','cohort_identity':EXPECTED_LABELS,'ALIGN_MATCH_definition':'unique marginal modes match and >=8/10 same test wells match BOTH modes','P3_reference_literal':'new target start minus one month; under literal R9 wording this is identical to P3; no silent reinterpretation as M-1 on a shifted window','frozen_config_not_edited':True})
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(paths['scoring_source'].resolve().parents[1]))
    from oil_uplift import scoring as frozen_scoring
    require(Path(frozen_scoring.__file__).resolve()==paths['scoring_source'].resolve(),'SCORER_IMPORT_IDENTITY')
    with zipfile.ZipFile(a.archive,'r') as z:
        infos=[i for i in z.infolist() if not i.is_dir()];members={name(i):i for i in infos};decl={}
        require(len(members)==len(infos)==manifest['file_count']==len(manifest['files'])==100,'INVENTORY')
        for row in manifest['files']:
            rel=row['relative_path'].replace('\\','/');hits=[n for n in members if n==rel or n.endswith('/'+rel)];require(len(hits)==1 and hits[0] not in decl.values(),'MEMBER_IDENTITY')
            raw=z.read(members[hits[0]]);require(len(raw)==row['bytes'] and sha(raw)==row['sha256'],'RAW_BYTES');decl[rel]=hits[0]
        def rawfile(rel):return z.read(members[decl[rel.replace('\\','/')]] )
        # Template-only pass: WELL_ID and NY, never RCYL or event/missingness.
        allkeys=[];test_keys=[];test_ids=set();projected=0
        require(roles['test']['template']==roles['test']['history'] and len(roles['test']['history'])==10,'TEST_ROLE_MAPPING')
        for f in roles['test']['template']:
            keys,_=key_projection(rawfile(f),well,date,encoding,delimiter);projected+=len(keys)
            require(len(keys)>=12 and len(set(keys))==len(keys),'TEST_KEYS');ids={x[0] for x in keys};require(len(ids)==1 and not ids&test_ids,'TEST_FILE_WELL_ID');test_ids|=ids
            periods=[pd.Timestamp(x[1]).to_period('M') for x in keys];require(len(set(periods))==len(periods),'TEST_DUPLICATE_MONTH')
            latest=set(sorted(periods)[-12:]);selected=[key for key,month in zip(keys,periods) if month in latest]
            ordered=sorted(latest);require(ordered==[ordered[0]+i for i in range(12)] and len(selected)==12,'TEST_TEMPLATE_12_MONTH_KEYS')
            allkeys+=selected;test_keys.append((f,ordered[0]))
        require(fingerprint(allkeys)==EXPECTED_KEYS,'TEMPLATE_KEY_HASH_MISMATCH_NO_DYNAMIC_READ')
        t1pairs=[];last=finite_pre=finite_m=0;gaps=[];unrecognized=Counter();audits=[]
        for f,t0 in test_keys:
            pre,audit=permitted_test_history(rawfile(f),well,date,event,target,t0,encoding,delimiter);audits.append(audit)
            require(all(p[1]<t0 for p in pre),'TEST_WINDOW_ENTRY');lookup={p[1]:p[3] for p in pre};last+=int(bool(pre) and max(lookup)==t0-1)
            finite_pre+=int(number(lookup.get(t0-1)) is not None)
            ss=segments([p[1] for p in pre if p[2] in cfg['anchors']['eligible_event_values']])
            if not ss:unrecognized['no_eligible_event_in_permitted_pretemplate_history']+=1;continue
            start,end=ss[-1];t1pairs.append((t0.ordinal-start.ordinal,t0.ordinal-end.ordinal));finite_m+=int(number(lookup.get(end)) is not None)
            if t0-1>end:gaps.append((t0-1).ordinal-end.ordinal)
        t1={'wells':10,'identified_wells':len(t1pairs),'k_start':distribution([x[0] for x in t1pairs]),'k_end':distribution([x[1] for x in t1pairs]),'last_pretemplate_row_equals_T0_minus_1_wells':last,'T0_minus_1_RCYL_finite_wells':finite_pre,'M_RCYL_finite_wells':finite_m,'gap_wells':len(gaps),'gap_month_count_distribution':distribution(gaps),'unrecognized_wells':sum(unrecognized.values()),'unrecognized_reasons':dict(unrecognized),'events_source':'only pretemplate history; no event values from template window','key_projection_rows':projected,'template_key_sha256':fingerprint(allkeys),'matches_existing_locked_template_keys':True}
        # Training pass: exact original complete cohort, no fitted features.
        histories={};cohort={};train_ids=set();excluded=Counter();label_rows=[]
        for f in roles['train']['history']:
            frame=pd.read_csv(io.BytesIO(rawfile(f)),encoding=encoding,sep=delimiter,usecols=[well,date,event,target]);ids=set(frame[well]);require(len(ids)==1 and not ids&train_ids,'TRAIN_WELL');wid=next(iter(ids));train_ids|=ids
            parsed=pd.to_datetime(frame[date],errors='coerce');require(parsed.notna().all(),'TRAIN_DATE');months=parsed.dt.to_period('M');require(not months.duplicated().any(),'TRAIN_MONTH_DUPLICATE');lookup=dict(zip(months,frame[target]));histories[wid]=lookup
            ss=segments(months[frame[event].isin(cfg['anchors']['eligible_event_values'])]);require(bool(ss),'TRAIN_NO_EVENT');start,end=ss[-1];truth=[];reason=None
            for step in range(1,13):
                if end+step not in lookup:reason='missing_month';break
                value=number(lookup[end+step])
                if value is None:reason='missing_or_nonfinite_target';break
                require(value>=0,'NEGATIVE_TRAIN_TARGET');truth.append(value)
            if reason:excluded[reason]+=1;continue
            cohort[wid]={'S':start,'M':end,'truth':truth,'P1':number(lookup.get(end-1)),'P2':number(lookup.get(end))}
        require(len(train_ids)==88 and len(cohort)==81 and not train_ids&test_ids,'TRAIN_COHORT_ISOLATION')
        for wid in sorted(cohort):label_rows +=[{well:wid,'horizon':i,'RCYL':v} for i,v in enumerate(cohort[wid]['truth'],1)]
        label_frame=pd.DataFrame(label_rows);labelhash=sha(pd.util.hash_pandas_object(label_frame[[well,'horizon','RCYL']],index=True).values.tobytes());require(labelhash==EXPECTED_LABELS,'TRAIN_LABEL_ORDER_IDENTITY')
        records=[cohort[wid] for wid in sorted(cohort)];t2pairs=[(r['M'].ordinal+1-r['S'].ordinal,1) for r in records]
        t2={'wells':81,'rows':972,'k_start':distribution([x[0] for x in t2pairs]),'k_end':distribution([x[1] for x in t2pairs]),'source_train_wells':88,'exclusions':dict(excluded),'label_key_order_sha256':labelhash,'current_target':'M+1..M+12'}
        aligned=alignment(t1pairs,t2pairs);p1=persistence(records,'P1');p2=persistence(records,'P2')
        delta=p2['all_well_score']['official_score']-p1['all_well_score']['official_score'] if p1['all_well_score'] and p2['all_well_score'] else None
        p3={'status':'NOT_TRIGGERED_ALIGN_MATCH_YES','score':None}
        if not aligned['ALIGN_MATCH']:
            if len(aligned['test_k_start_modes'])!=1:p3={'status':'UNKNOWN_NONUNIQUE_TEST_START_MODE','score':None}
            else:
                k=aligned['test_k_start_modes'][0];new=[];fail=Counter()
                for wid in sorted(cohort):
                    original=cohort[wid];lookup=histories[wid];start=original['S']+k;truth=[number(lookup.get(start+i)) for i in range(12)]
                    if any(v is None or v<0 for v in truth):fail['incomplete_or_invalid_redefined_target']+=1;continue
                    new.append({'truth':truth,'P3':number(lookup.get(start-1))})
                value=persistence(new,'P3') if new else None
                primary=value if value and len(new)==81 else None
                score_value=primary['all_well_score']['official_score'] if primary and primary['all_well_score'] else None
                p3={'status':'COMPLETE' if score_value is not None else 'INCOMPLETE_NO_IMPUTATION','k_start_star':k,'original_well_denominator':81,'complete_redefined_target_wells':len(new),'exclusions':dict(fail),'score':primary,'valid_target_subset_only':value if len(new)<81 else None,'prediction_month':'S+k_start_star-1','target':'S+k_start_star .. S+k_start_star+11','redefined_target_P1_reference':primary,'P3_minus_redefined_target_P1':0.0 if score_value is not None else None,'literal_reference_note':'R9 P1 reference says use preceding month of redefined target. This is the same predictor/target as P3; identity is reported rather than silently inventing a different control. Original M-1 on a shifted target may overlap target and is NOT used.','P3_minus_original_P1_different_target_descriptive_only':score_value-p1['all_well_score']['official_score'] if score_value is not None and p1['all_well_score'] else None,'cross_target_difference_is_model_gain':False}
    require(before=={k:sha(v.read_bytes()) for k,v in paths.items()},'INPUT_MUTATION')
    official_checks=[]
    def check_official(items,predictor,label):
        rows=[]
        for index,item in enumerate(items):
            v=item[predictor]
            if v is None or v<0:continue
            rows.extend({'well':index,'horizon':h,'truth':truth,'prediction':v} for h,truth in enumerate(item['truth'],1))
        if not rows:return
        frame=pd.DataFrame(rows)
        actual=frozen_scoring.official_twelve_month_score(frame,truth_column='truth',prediction_column='prediction',well_column='well',epsilon=1e-6).total
        own=persistence(items,predictor);expected=(own['all_well_score'] or own['valid_subset_only'])['official_score'];difference=actual-expected
        require(abs(difference)<=1e-12,'OFFICIAL_SCORER_MISMATCH');official_checks.append({'name':label,'well_count':int(frame.well.nunique()),'official_module_score':actual,'difference_vs_local_formula':difference,'tolerance':1e-12})
    check_official(records,'P1','P1');check_official(records,'P2','P2')
    if not aligned['ALIGN_MATCH'] and len(aligned['test_k_start_modes'])==1:check_official(new,'P3','P3_and_literal_redefined_P1')
    t3={'P1':p1,'P2':p2,'P2_minus_P1':delta,'P3':p3,'B0_reference':73.71410733861434,'B0_newly_reproduced':False,'no_imputation_no_scaling_no_fit':True,'T4_permission_implied_by_P2_score':False,'frozen_official_scorer_cross_checks':official_checks}
    decoder_totals={'test_files':len(audits),'test_window_rows_skipped_before_dynamic_cell_decode':sum(x['test_window_rows_skipped_before_dynamic_cell_decode'] for x in audits),'test_window_RCYL_decoded':0,'test_window_event_decoded':0,'test_window_other_dynamic_decoded':0,'decoded_cells':{k:sum(x['decoded_cells'].get(k,0) for x in audits) for k in sorted({k for x in audits for k in x['decoded_cells']})}}
    row='ALIGN_MATCH = 否' if not aligned['ALIGN_MATCH'] else ('ALIGN_MATCH = 是，且 P2_minus_P1 < +1.0' if delta is not None and delta<1 else 'CONDITIONAL_PENDING_T4' if delta is not None else 'UNKNOWN_MISSING_PRIMARY_SCORE')
    result={'task':'A2B-032','role':'账户B执行与交付','R9_commit':R9,'T1':t1,'T2':t2,**aligned,'T3':t3,'P1':p1['all_well_score']['official_score'] if p1['all_well_score'] else None,'P2':p2['all_well_score']['official_score'] if p2['all_well_score'] else None,'P2_minus_P1':delta,'P3':p3['score']['all_well_score']['official_score'] if p3.get('score') and p3['score']['all_well_score'] else None,'T4':'NOT_DECIDED_BY_B','decision_B_self_report':row,'decision_row_Codex':'不适用','fit_counts':{'model_entered':0,'model_completed':0,'preprocessor_entered':0,'preprocessor_completed':0},'read_boundary':{'raw_100_members_hash_verified':True,'archive_extracted':False,'train_history_tables_parsed':88,'test_history_tables_full_parsed':0,'template_keys_only_tables_projected':10,'template_key_hash_verified_before_history_dynamic_access':True,'test_window_dynamic_values_decoded':0,'test_window_RCYL_parsed':0,'test_window_other_fields_used':0,'test_decoder_aggregate':decoder_totals,'plan_layer_tables_parsed':0,'private_rows_persisted':False},'integrity':{'input_hashes_before':before,'input_hashes_after':before,'old_artifacts_modified':False},'hard_gates':{'泄漏':'通过：本次T1–T3限定读取；T4另由Codex判定','错位':'通过：逐月与既有模板键、训练标签键身份核对；ALIGN_MATCH结果不等于泄漏','井级隔离':'通过：训练/测试井交集0；未拟合','指标':'通过：训练井内存逐井官方公式；无测试评分'},'runtime_seconds':time.perf_counter()-started,'training_authorized_by_this_audit':False,'ML_modules_imported':any(x.startswith(('sklearn','xgboost','lightgbm','catboost')) for x in sys.modules)}
    save('RESULT_A2B032.json',result);save('ZERO_FIT_COUNTS.json',result['fit_counts']);save('ENVIRONMENT_LOCK.json',environment);save('READ_BOUNDARY_AND_INTEGRITY.json',{'read_boundary':result['read_boundary'],'integrity':result['integrity']})
    print(json.dumps({'T1_k_start':t1['k_start'],'T1_k_end':t1['k_end'],'T2_k_start':t2['k_start'],'T2_k_end':t2['k_end'],'ALIGN_MATCH':aligned['ALIGN_MATCH'],'test_joint_modal_wells':aligned['test_joint_modal_wells'],'P1':result['P1'],'P2':result['P2'],'P2_minus_P1':delta,'P3':result['P3'],'model_fits':0,'preprocessor_fits':0}))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('archive','manifest','config','template-receipt','scoring-source','output'):p.add_argument('--'+key,required=True)
    main(p.parse_args())
