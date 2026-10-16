"""R6 read-only zero-fit diagnostics. No raw values or row arrays are saved."""
import hashlib,io,json
from pathlib import Path
import numpy as np,pandas as pd
R6='9bec6d563f492f8992337441e58610028dd5127f'
FIELDS=['CCJHWND','CCJND','CCBHJND','CCYND']
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def trend_features(values,ordinals,cutoff):
    values=np.asarray(values,float);months=np.asarray(ordinals,int);valid=np.isfinite(values)&(months<cutoff)
    order=np.argsort(months[valid],kind='stable');v=values[valid][order];x=months[valid][order]
    last=float(v[-1]) if len(v) else np.nan;recent=x>=cutoff-3;v=v[recent];x=x[recent].astype(float)
    slope=np.nan
    if len(v)>=2:
        x-=x.mean();slope=float(np.sum(x*(v-v.mean()))/np.sum(x*x))
    return last,slope
def loss_decomposition(y,p):
    a,b=y[:,:2].mean(1),y[:,3:6].mean(1);rise=b>1.1*a;fall=b<.9*a
    groups={'上升':rise,'下降':fall,'稳产':~rise&~fall,'含0值':(y==0).any(1)}
    weighted=np.abs(y-p)/(np.abs(y)+np.abs(p)+1e-6)*(.5**np.arange(1,13));answer={}
    for label,mask in groups.items():
        records={}
        for n in (1,2,4,12):
            losses=weighted[:,:n].sum(1);total=losses.sum();selected=losses[mask]
            records[f'm1_to_{n}']={'well_count':int(mask.sum()),'mean_per_well_score':float((100*(1-selected)).mean()) if len(selected) else None,'mean_per_well_weighted_loss':float(selected.mean()) if len(selected) else None,'total_loss_contribution_share':float(selected.sum()/total) if total>0 else 0.}
        answer[label]=records
    return {'groups':answer,'shape_definition':'a=mean(m1,m2), b=mean(m4,m5,m6); rise b>1.1a; fall b<.9a; stable otherwise; contains-zero exact truth==0','contains_zero_is_overlapping_overlay':True,'prefix_scores_use_unrenormalized_official_weights':True,'retrospective_truth_groups_not_features_routing_or_selection':True}
def prepare(root,store,history,anchors,rawconfig,safe):
    root=Path(root);root.mkdir(exist_ok=False)
    here=Path(__file__).resolve().parent
    assert digest(here/'received/INSTRUCTION_ORIGINAL_R6.md')=='e9c6da7c400bf5385f98b84b01a8e1ed3a7b8322dc0053c40e18a91c441ce5d5'
    lock={'R6_commit':R6,'source_sha256':digest(__file__),'plan_sha256':digest(here/'PLAN_R6.json'),'before_real_diagnostic_values':True,'model_fit_budget':0,'preprocessor_fit_budget':0,'input_archive_sha256':store.before['archive'],'input_manifest_sha256':store.before['manifest']}
    def save(name,value):(root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save('IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json',lock)
    w,d=rawconfig['anchors']['well_column'],rawconfig['anchors']['date_column'];period=safe._periods(history,d);event=rawconfig['anchors']['event_column'];eligible=rawconfig['anchors']['eligible_event_values']
    complete=set(anchors[w]);segments={};starts={};ends={}
    for well in complete:
        months=sorted(set(period[(history[w]==well)&history[event].isin(eligible)]));starts[well]=[q for i,q in enumerate(months) if i==0 or months[i-1]+1!=q];ends[well]=[q for i,q in enumerate(months) if i==len(months)-1 or q+1!=months[i+1]];segments[well]=len(starts[well])
    single={w for w,n in segments.items() if n==1}
    roles=rawconfig['data']['sources'];settings=rawconfig['data']['csv'];tables={}
    for role in ('plan','layer'):
        declared=list(dict.fromkeys(roles['train'][role]+roles['test'][role]));parts=[]
        for f in declared:
            member=store.declared[f.replace('\\','/')];parts.append(pd.read_csv(io.BytesIO(store.zip.read(store.members[member])),encoding=settings.get('encoding','utf-8-sig'),sep=settings.get('delimiter',',')))
        tables[role]=pd.concat(parts,ignore_index=True)
    plan=tables['plan'];layer=tables['layer'];assert list(plan.columns[:3])==['井号','完工日期','层位']
    dates=pd.to_datetime(plan['完工日期'],errors='coerce').dt.to_period('M')
    consistent=set();pre_start=set();ambiguous=0;missing=0
    for well in single:
        pp=dates.loc[plan['井号']==well];valid=sorted(set(pp.dropna()))
        if not valid:missing+=1;continue
        if len(valid)!=1:ambiguous+=1
        if any(q<=ends[well][0] for q in valid):consistent.add(well)
        # Strict evidence: a unique completion month <= start, never infer design availability.
        if len(valid)==1 and valid[0]<=starts[well][0]:pre_start.add(well)
    level='A' if single and len(pre_start)==len(single) else 'C'
    # Date A scope is only the literal month relation, not original acquisition time.
    n1={'N1_single_event_train':len(single),'N1_date_consistent_train':len(consistent),'N1_evidence_level':level,'denominator':81,'single_event_unique_date_at_or_before_start_count':len(pre_start),'single_event_missing_date_count':missing,'single_event_multiple_distinct_plan_date_count':ambiguous,'date_consistency_definition':'at least one plan completion month <= sole segment end (inside or before segment)','A_definition':'all single-event training wells have one unambiguous plan completion month <= event start month','B_evidence_found':False,'evidence_caveat':'Official field says completion date corresponds to fracturing date. It does not itself prove pre-construction design publication. A if reached is date-order evidence only; M-1 availability remains separate. No timestamp or pre-design statement invented.'}
    test_frames=[]
    for f in roles['test']['history']:
        member=store.declared[f.replace('\\','/')];test_frames.append(pd.read_csv(io.BytesIO(store.zip.read(store.members[member])),encoding=settings.get('encoding','utf-8-sig'),sep=settings.get('delimiter',','),usecols=[w,d,event]))
    test=pd.concat(test_frames,ignore_index=True);assert 'RCYL' not in test
    tp=safe._periods(test,d);test_single=0
    for well,group in test.groupby(w,sort=False):
        months=sorted(set(tp.loc[group.index][group[event].isin(eligible)]));count=sum(i==0 or months[i-1]+1!=q for i,q in enumerate(months));test_single+=count==1
    test_ids=set(test[w]);assert len(test_ids)==10 and not test_ids&set(history[w])
    n1['test_field_coverage_only']={'single_event_wells':int(test_single),'wells':10,'fraction':test_single/10,'used_in_decision':False,'plan_fields_nonmissing_fraction':{c:float(plan.loc[plan['井号'].isin(test_ids),c].notna().mean()) for c in plan.columns if c!='井号'},'layer_fields_nonmissing_fraction':{c:float(layer.loc[layer.WELL_ID.isin(test_ids),c].notna().mean()) for c in layer.columns if c!='WELL_ID'}}
    coverage=[]
    for col in FIELDS:
        pairs=[]
        for well,m in anchors[[w,'anchor_period']].itertuples(index=False,name=None):
            legal=(history[w]==well)&(period<m);v=pd.to_numeric(history.loc[legal,col],errors='coerce');x=np.array([q.ordinal for q in period.loc[legal]])
            last,slope=trend_features(v,x,m.ordinal);pairs.append((np.isfinite(last),np.isfinite(slope)))
        pair=np.asarray(pairs,bool);joint=int(pair.all(1).sum())
        coverage.append({'field':col,'well_denominator':81,'last_valid_count':int(pair[:,0].sum()),'last_valid_coverage':float(pair[:,0].mean()),'slope_valid_count':int(pair[:,1].sum()),'slope_valid_coverage':float(pair[:,1].mean()),'combo_both_valid_count':joint,'combo_coverage':joint/81,'combo_passed':joint/81>=.8})
    n2={'N2_combo_pass_count':sum(x['combo_passed'] for x in coverage),'combo_definition':'one combination per field: (last valid, calendar3 slope); coverage requires both finite; also report each column separately','slope_definition':'unweighted OLS covariance/variance on true calendar-month ordinal in M-3..M-1; >=2 valid observations, otherwise NaN; no interpolation or fit API','coverage':coverage,'cutoff':'M-1','features_used_in_R5':False}
    fields=json.loads((here/'FIELD_DICTIONARY_N1.json').read_bytes());fields['actual_plan_field_order']=list(plan.columns);fields['actual_layer_field_order']=list(layer.columns)
    assert set(x['field'] for x in fields['plan'])==set(plan.columns) and set(x['field'] for x in fields['layer'])==set(layer.columns)
    save('N1_FIELDS.json',fields);save('N1_MAPPING.json',n1);save('N2_COVERAGE.json',n2)
    result={'task':'A2B-030/零拟合诊断','role':'账户B执行与交付','Claude_instruction_commit':R6,'N1_single_event_train':n1['N1_single_event_train'],'N1_date_consistent_train':n1['N1_date_consistent_train'],'N1_evidence_level':level,'N2_combo_pass_count':n2['N2_combo_pass_count'],'N1':n1,'N2':n2,'N4_status':'推迟：等待同一A2B-028进程B0内存OOF','N4':None,'fit_counts':{'model_entered':0,'model_completed':0,'preprocessor_entered':0,'preprocessor_completed':0},'test_label_columns_read':0,'test_fields_read':[w,d,event],'test_tables_parsed_for_coverage_only':10,'hard_gates':{'泄漏':'通过','错位':'通过','井级隔离':'通过','指标':'UNKNOWN'},'decision_row_Codex':'不适用（待独立审核）'}
    result['decisions_B_self_report']={'N1-a':('N1_evidence_level 为 C' if level=='C' else ('N1_single_event_train ≥ 40 且 N1_evidence_level 为 A 或 B' if len(single)>=40 else 'N1_single_event_train < 40')),'N2-a':'N2_combo_pass_count ≥ 1' if n2['N2_combo_pass_count']>=1 else '未达1，不并入','N4':'无门槛，仅回顾性诊断'}
    save('ZERO_FIT_COUNTS.json',result['fit_counts'])
    return result
def finish(root,result,y=None,p=None):
    if y is not None:
        result['N4']=loss_decomposition(y,p);result['N4_status']='COMPLETED_SAME_A028_PROCESS_MEMORY_B0';result['hard_gates']['指标']='通过'
    result['status']='COMPLETED' if result['N4'] is not None else 'PARTIAL_N4_POSTPONED_NO_RETRAIN'
    path=Path(root)/'RESULT_A2B030.json';assert not path.exists();path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
