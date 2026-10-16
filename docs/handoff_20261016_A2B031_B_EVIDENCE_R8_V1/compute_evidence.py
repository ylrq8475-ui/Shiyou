"""R8 zero-fit evidence. Private records live in memory; output is aggregate only.

Requires pandas and PyYAML. Reads the frozen ZIP without extraction. No model,
preprocessor, test-history parser, prediction, or scoring entry point is imported.
"""
import argparse, hashlib, io, json, math, platform, sys, zipfile
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path, PurePosixPath
import pandas as pd
import yaml

def digest(raw): return hashlib.sha256(raw).hexdigest()
def encode(obj): return (json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def save(folder,name,obj): (Path(folder)/name).write_bytes(encode(obj))
def require(ok,code):
    if not ok: raise RuntimeError(code)  # never include private values in exceptions
def member_name(info):
    value=info.filename
    if not info.flag_bits&0x800:
        try:value=value.encode('cp437').decode('gb18030')
        except UnicodeError:pass
    value=value.replace('\\','/')
    require(not PurePosixPath(value).is_absolute() and '..' not in PurePosixPath(value).parts and ':' not in value,'UNSAFE_ZIP_NAME')
    return value
def segments(months):
    out=[]
    for month in sorted(set(months)):
        if not out or month!=out[-1][1]+1:out.append([month,month])
        else:out[-1][1]=month
    return out
def conditions(event_segments, dates, records):
    valid=sorted(set(dates.dropna().dt.normalize()))
    unique=records>0 and dates.notna().all() and len(valid)==1
    completion=valid[0].to_period('M') if unique else None
    # For a multi-segment well, C3/C4 independently refer to its CURRENT last
    # segment; C1 is checked separately. Undefined dates fail, never pass.
    start,end=event_segments[-1]
    return [len(event_segments)==1, bool(unique), bool(unique and start<=completion<=end), bool(unique and completion<=end-1)]

def main(a):
    root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
    source_paths={'archive':Path(a.archive),'manifest':Path(a.manifest),'config':Path(a.config),'dictionary':Path(a.dictionary),'safe_source':Path(a.safe_source),'multistep_source':Path(a.multistep_source)}
    before={k:digest(p.read_bytes()) for k,p in source_paths.items()}
    require(before['config']=='89e60c301b1d553b1c7dab8e2f87d1d9a47b600abe4322f2e9895717201c0c72','CONFIG_DRIFT')
    cfg=yaml.safe_load(source_paths['config'].read_bytes());manifest=json.loads(source_paths['manifest'].read_bytes())
    require(cfg['anchors']['first_forecast_month_offset']==1 and cfg['anchors']['horizon_months']==12 and cfg['anchors']['same_month_tie_strategy']=='error','ANCHOR_DRIFT')
    environment={'python':sys.version,'build':platform.python_build(),'implementation':platform.python_implementation(),'pandas':pd.__version__,'PyYAML':yaml.__version__,'no_ML_imports':not any(x.startswith(('sklearn','xgboost','catboost','lightgbm')) for x in sys.modules)}
    save(root,'IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json',{'time':datetime.now(timezone(timedelta(hours=8))).isoformat(),'before_diagnostic_counts':True,'R8_commit':'252d421d4396c5e4119f03c772be239a9cdd1b7e','script_sha256':digest(Path(__file__).read_bytes()),'source_hashes':before,'environment':environment,'model_fit_budget':0,'preprocessor_fit_budget':0,'cohort_definition':'latest continuous eligible segment end M, complete finite nonnegative targets M+1..M+12, sorted WELL_ID; targets only determine established cohort, never used as features','C1':'exactly one eligible continuous segment','C2':'at least one plan row; all completion dates parse, exactly one normalized full date (not merely month)','C3':'unique completion month in current last segment, inclusive','C4':'unique completion month <= current last segment end M minus one month','independent_fail_denominator':81,'multiple_segment_rule':'C3/C4 use current last segment independently; C1 must still pass intersection','test_history_CSVs_parsed':0})
    w,d,e=tuple(cfg['anchors'][k] for k in ('well_column','date_column','event_column'));target=cfg.get('schema',{}).get('mapping',{}).get('target','RCYL');roles=cfg['data']['sources'];settings=cfg['data']['csv'];excluded=Counter();cohort={};train_ids=set();label_rows={}
    with zipfile.ZipFile(a.archive,'r') as z:
        infos=[i for i in z.infolist() if not i.is_dir()];entries={member_name(i):i for i in infos};declared={}
        require(len(entries)==len(infos)==manifest['file_count']==len(manifest['files'])==100,'INVENTORY_DRIFT')
        require(len({x.casefold() for x in entries})==100,'CASE_COLLISION')
        for row in manifest['files']:
            rel=row['relative_path'].replace('\\','/');matches=[n for n in entries if n==rel or n.endswith('/'+rel)]
            require(len(matches)==1 and matches[0] not in declared.values(),'MANIFEST_MEMBER_AMBIGUOUS')
            raw=z.read(entries[matches[0]]);require(len(raw)==row['bytes'] and digest(raw)==row['sha256'],'RAW_MEMBER_DRIFT');declared[rel]=matches[0]
        def table(rel,usecols=None):
            return pd.read_csv(io.BytesIO(z.read(entries[declared[rel.replace('\\','/')]])),encoding=settings.get('encoding','utf-8-sig'),sep=settings.get('delimiter',','),usecols=usecols)
        require(len(roles['train']['history'])==88 and len(set(roles['train']['history']))==88,'TRAIN_INVENTORY')
        styles=set()
        for filename in roles['train']['history']:
            frame=table(filename,[w,d,e,target]);ids=set(frame[w]);require(len(ids)==1,'HISTORY_WELL_COUNT');wid=next(iter(ids));require(wid not in train_ids,'WELL_ACROSS_FILES');train_ids.add(wid)
            stem=PurePosixPath(filename.replace('\\','/')).stem;require(wid in stem,'FILENAME_BINDING');position=stem.index(wid);styles.add((stem[:position],stem[position+len(wid):]))
            dates=pd.to_datetime(frame[d],errors='coerce');require(dates.notna().all(),'HISTORY_DATE_INVALID');months=dates.dt.to_period('M');require(not months.duplicated().any(),'DUPLICATE_WELL_MONTH')
            ss=segments(months[frame[e].isin(cfg['anchors']['eligible_event_values'])])
            if not ss:excluded['no_event']+=1;continue
            end=ss[-1][1];mapping=dict(zip(months,frame[target]));reason=None
            for step in range(1,13):
                if end+step not in mapping:reason='missing_month';break
                value=pd.to_numeric(mapping[end+step],errors='coerce')
                if pd.isna(value):reason='missing_target';break
                if not math.isfinite(float(value)):reason='nonfinite_target';break
                require(float(value)>=0,'NEGATIVE_COMPLETE_TARGET')
            if reason:excluded[reason]+=1;continue
            cohort[wid]=ss
            label_rows[wid]=[{w:wid,'horizon':step,'RCYL':float(pd.to_numeric(mapping[end+step]))} for step in range(1,13)]
        require(len(train_ids)==88 and len(cohort)==81,'COHORT_COUNT_DRIFT')
        label_frame=pd.DataFrame([row for wid in sorted(cohort) for row in label_rows[wid]])
        label_hash=digest(pd.util.hash_pandas_object(label_frame[[w,'horizon','RCYL']],index=True).values.tobytes())
        require(label_hash=='4e7db99d009ade76143f37ceed1a5370f0997e328cd77ee97e1f530aca4fbcda','COHORT_LABEL_ORDER_DRIFT')
        test_ids=set()
        for filename in roles['test']['history']:
            stem=PurePosixPath(filename.replace('\\','/')).stem;hits=set()
            for pre,suf in styles:
                if stem.startswith(pre) and stem.endswith(suf):
                    stop=len(stem)-len(suf) if suf else len(stem);candidate=stem[len(pre):stop]
                    if candidate:hits.add(candidate)
            require(len(hits)==1,'TEST_FILENAME_BINDING');test_ids|=hits
        require(len(test_ids)==10 and not test_ids&train_ids,'TRAIN_TEST_ID_OVERLAP')
        tables={};version={};coverage={}
        for role,key in (('layer','WELL_ID'),('plan','井号')):
            tr=roles['train'][role];te=roles['test'][role];require(len(tr)==len(te)==1 and tr==te,'ROLE_VERSION_MAPPING_DRIFT')
            tables[role]=table(tr[0]);f=tables[role];selected=f[f[key].isin(test_ids)]
            coverage[role]={'test_wells':10,'record_bearing_wells':int(selected[key].nunique()),'fields':[{'field':c,'record_denominator':len(selected),'nonmissing_records':int(selected[c].notna().sum()),'wells_with_nonmissing':int(selected.loc[selected[c].notna(),key].nunique())} for c in f.columns]}
            datefields=[c for c in f.columns if any(x in c for x in ('日期','时间','版本','更新','date','version','time'))]
            current_member=entries[declared[tr[0].replace('\\','/')]]
            version[role]={'current_train_test_same_archive_member':True,'member_sha256':digest(z.read(current_member)),'release_date':'无：包内未找到可核验的官方发布日期','version_or_update_fields':[c for c in datefields if c!='完工日期'],'date_fields':datefields,'completion_date_is_version_timestamp':False,'historical_asof_version_evidence':'无','same_member_not_historical_identity':True,'train_wells_with_records':int(f.loc[f[key].isin(train_ids),key].nunique()),'test_wells_with_records':int(selected[key].nunique()),'total_rows':len(f)}
        dictionary=json.loads(Path(a.dictionary).read_bytes())
        for role in ('plan','layer'):require([x['field'] for x in dictionary[role]]==list(tables[role].columns),'OFFICIAL_DICTIONARY_SCHEMA_DRIFT')
        plan=tables['plan'];pass_counts=[0]*4;funnel=[0]*4;all_pass=0;unique_month=0;date_errors=Counter();multiple_rows_unique=0
        for wid in sorted(cohort):
            rows=plan.loc[plan['井号']==wid];dates=pd.to_datetime(rows['完工日期'],format='mixed',errors='coerce');flags=conditions(cohort[wid],dates,len(rows));passed=True
            for i,flag in enumerate(flags):
                pass_counts[i]+=int(flag);passed=passed and flag;funnel[i]+=int(passed)
            all_pass+=int(all(flags));unique_month+=int(len(rows)>0 and dates.notna().all() and dates.dt.to_period('M').nunique()==1);multiple_rows_unique+=int(len(rows)>1 and flags[1])
            if len(rows)==0:date_errors['no_plan_rows']+=1
            elif dates.isna().any():date_errors['missing_or_invalid_date']+=1
            elif dates.dt.normalize().nunique()!=1:date_errors['multiple_distinct_full_dates']+=1
        result={'task':'A2B-031/补证','role':'账户B执行与交付','R8_commit':'252d421d4396c5e4119f03c772be239a9cdd1b7e','E3':{'cohort_wells':81,'cohort_rows':972,'source_train_wells':88,'exclusions':dict(excluded),'N_Q2_all':all_pass,'conditions':['C1_single_event_segment','C2_unique_complete_full_date','C3_completion_in_current_segment','C4_completion_at_or_before_M_minus_1'],'independent_pass_counts':pass_counts,'independent_failure_counts':[81-x for x in pass_counts],'cumulative_all_conditions_pass_counts':funnel,'single_event_wells':pass_counts[0],'unique_completion_month_wells':unique_month,'multiple_plan_rows_but_unique_full_date_wells':multiple_rows_unique,'date_ambiguity_counts':dict(date_errors),'date_field':{'field':'完工日期','official_meaning':'对应井史数据压裂日期','source':'O1 datasetDescription 压裂操作方案字典第2行'},'strict_date_uniqueness':'full date; several dates within same month are not accepted','C3_C4_independent_scope':'current last continuous event segment; C1 separately required','availability_proven_by_date_order':False,'new_candidate_scores_generated':False},'E1_test_field_coverage':coverage,'E4_local_file_metadata':version,'input_identity':before,'fit_counts':{'model_entered':0,'model_completed':0,'preprocessor_entered':0,'preprocessor_completed':0},'test_history_tables_parsed':0,'test_label_columns_read':0,'archive_extracted':False,'private_records_persisted':False,'hard_gates':{'泄漏':'UNKNOWN：Q1/Q2可得性待Codex；本次未构造或训练新增输入','错位':'通过：本次队列按冻结M+1..M+12；未预测或评分','井级隔离':'通过：训练/测试标识集合无交集；本次未切分或拟合','指标':'UNKNOWN：零拟合补证，不新算模型分数'},'Q1_Q2_independent_review':'PENDING; no B self-release','historical_dtype':'UNKNOWN; no historical lock rewritten'}
    require(before=={k:digest(p.read_bytes()) for k,p in source_paths.items()},'SOURCE_INTEGRITY_CHANGED')
    result['source_integrity']={'all_100_members_original_bytes_verified':True,'archive_config_manifest_sources_unchanged':True,'models_loaded':0,'old_artifacts_modified':False,'no_ML_imports':environment['no_ML_imports'],'cohort_label_key_order_sha256':label_hash,'matches_A2B028_B0_prefit_identity':True,'label_key_hash_is_not_a_new_score_or_feature_identity_claim':True}
    save(root,'COMPUTED_AGGREGATES.json',result);save(root,'ZERO_FIT_COUNTS.json',result['fit_counts']);save(root,'ENVIRONMENT_LOCK.json',environment)
    print(json.dumps({'N_Q2_all':all_pass,'independent_pass_counts':pass_counts,'independent_failure_counts':result['E3']['independent_failure_counts'],'funnel':funnel,'model_fits':0,'preprocessor_fits':0}))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('archive','manifest','config','dictionary','safe-source','multistep-source','output'):parser.add_argument('--'+name,required=True)
    main(parser.parse_args())
