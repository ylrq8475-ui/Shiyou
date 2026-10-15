"""R5 pure features/evaluation; no fitting, data export or network operations."""
import hashlib,json
import numpy as np
import pandas as pd
from diagnostic_core import require,fingerprint,array_hash,official_summary,cross_residual_adjust,eligible_segment_ends,BASELINE

F0_NAMES=[f'f0_C{i:02d}_{stat}' for i in range(1,6) for stat in ('last_valid','mean_calendar3')]
def combinations(history,periods):
    n=lambda c:pd.to_numeric(history[c],errors='coerce').to_numpy(float)
    l,o,yy,ty,pl,bx,up,dn,days=map(n,['RCYL1','RCYL','YY','TY','PL','BX','SXDL','XXDL','SCTS'])
    calendar=periods.dt.days_in_month.to_numpy(float)
    with np.errstate(all='ignore'):
        values=[(l-o)/l,yy-ty,pl*bx/100,(up-dn)/(up+dn),days/calendar]
    masks=[np.isfinite(l)&np.isfinite(o)&(l>0)&(o>=0)&(o<=l),np.isfinite(yy)&np.isfinite(ty)&(yy>=0)&(ty>=0),np.isfinite(pl)&np.isfinite(bx)&(pl>0)&(bx>=0)&(bx<=100),np.isfinite(up)&np.isfinite(dn)&(up>=0)&(dn>=0)&(up+dn>0),np.isfinite(days)&(days>=0)&(days<=calendar)]
    return np.column_stack([np.where(m&np.isfinite(v),v,np.nan) for v,m in zip(values,masks)])

def f0_event(history,well,m,config,safe):
    w,d=config['anchors']['well_column'],config['anchors']['date_column']
    periods=safe._periods(history,d)
    part=history.loc[(history[w]==well)&(periods<m)].copy()
    p=periods.loc[part.index];order=np.argsort(p.to_numpy(),kind='stable');part=part.iloc[order];p=p.iloc[order]
    v=combinations(part,p);answer={}
    for k in range(5):
        valid=v[:,k][np.isfinite(v[:,k])];recent=v[:,k][(p>=m-3).to_numpy()];recent=recent[np.isfinite(recent)]
        answer[F0_NAMES[2*k]]=float(valid[-1]) if len(valid) else np.nan
        answer[F0_NAMES[2*k+1]]=float(recent.mean()) if len(recent) else np.nan
    return answer

def add_f0(panel,history,config,safe):
    out=panel.copy();cache={}
    for well,anchor in panel[['WELL_ID','anchor_time']].drop_duplicates().itertuples(index=False,name=None):
        m=pd.Period(anchor,freq='M');cache[(well,anchor)]=f0_event(history,well,m,config,safe)
    for name in F0_NAMES:out[name]=[cache[(w,m)][name] for w,m in panel[['WELL_ID','anchor_time']].itertuples(index=False,name=None)]
    require(all(pd.api.types.is_numeric_dtype(out[n]) for n in F0_NAMES),'F0_NUMERIC_SCHEMA')
    return out

def auxiliary_panel(history,anchors,config,safe):
    w,d=config['anchors']['well_column'],config['anchors']['date_column'];event=config['anchors']['event_column']
    p=safe._periods(history,d);latest,_=safe.segment_end_anchors(history,config)
    complete=set(anchors[w]);last=dict(latest[[w,'anchor_period']].itertuples(index=False,name=None))
    rows=[];hist_events=inc_events=0;counts=[];audit_events=[]
    for well in sorted(last):
        group=history.loc[history[w]==well];gp=p.loc[group.index]
        targets=dict(zip(gp,pd.to_numeric(group.RCYL,errors='coerce').to_numpy(float)))
        eligible={int(q.ordinal) for q in gp.loc[group[event].isin(config['anchors']['eligible_event_values'])]}
        chosen=[]
        if well in complete:
            for end in eligible_segment_ends(eligible):
                if end>=last[well].ordinal:continue
                m=pd.Period(ordinal=end,freq='M');window=[m+h for h in range(1,13)]
                if any(q not in targets or not np.isfinite(targets[q]) or targets[q]<0 for q in window):continue
                if eligible.intersection(q.ordinal for q in window):continue
                chosen.append((m,[(h,targets[m+h]) for h in range(1,13)],'historical'));hist_events+=1
        else:
            m=last[well];valid=[(h,targets[m+h]) for h in range(1,13) if m+h in targets and np.isfinite(targets[m+h]) and targets[m+h]>=0]
            if valid:chosen.append((m,valid,'incomplete'));inc_events+=1
        for m,valid,kind in chosen:
            base=safe._safe_history_values(history,well,m,config)
            trimmed=history.loc[(history[w]==well)&(p<m)]
            safe_base=safe._safe_history_values(trimmed,well,m,config)
            require(base.keys()==safe_base.keys() and all(safe._same_feature_value(base[k],safe_base[k]) for k in base),'AUX_FUTURE_SENSITIVITY')
            full_f0=f0_event(history,well,m,config,safe);trim_f0=f0_event(trimmed,well,m,config,safe)
            require(all(safe._same_feature_value(full_f0[k],trim_f0[k]) for k in full_f0),'AUX_F0_FUTURE_SENSITIVITY')
            audit_events.append({'WELL_ID':well,'anchor_period':m})
            for h,y in valid:rows.append({'WELL_ID':well,'anchor_time':m.to_timestamp(),'horizon':h,'forecast_step':h,'RCYL':y,**base})
            counts.append({'kind':kind,'label_rows':len(valid),'m1':int(any(h==1 for h,_ in valid)),'m2':int(any(h==2 for h,_ in valid))})
    require(hist_events==26 and inc_events==6 and len(counts)==32,'A027_AUX_EVENT_IDENTITY_COUNT')
    require(sum(c['m1'] for c in counts)==32 and sum(c['m2'] for c in counts)==32,'A027_AUX_EARLY_LABEL_COUNT')
    out=pd.DataFrame(rows)
    require(not out[['WELL_ID','anchor_time','horizon']].duplicated().any(),'AUX_DUPLICATE_KEY')
    return out,{'historical_events':hist_events,'incomplete_events':inc_events,'events':len(counts),'rows':len(out),'historical_rows':sum(x['label_rows'] for x in counts if x['kind']=='historical'),'incomplete_rows':sum(x['label_rows'] for x in counts if x['kind']=='incomplete'),'m1_labels':32,'m2_labels':32,'future_sensitive_features':0}

def identity(frame,features):
    return {'feature_order_sha256':fingerprint(features),'feature_dtype_sha256':fingerprint(list(zip(features,frame[features].dtypes.astype(str)))),'feature_frame_sha256':hashlib.sha256(pd.util.hash_pandas_object(frame[features],index=True).values.tobytes()).hexdigest(),'label_key_frame_sha256':hashlib.sha256(pd.util.hash_pandas_object(frame[['WELL_ID','horizon','RCYL']],index=True).values.tobytes()).hexdigest()}

def summarize(y,p,folds,b0=None):
    answer=official_summary(y,p)
    fs=[official_summary(y[folds==f],p[folds==f])['official_score'] for f in range(5)]
    answer.update(score=answer['official_score'],delta=answer['official_score']-BASELINE,fold_scores=fs,worst_fold=min(fs),fold_std_ddof0=float(np.std(fs,ddof=0)))
    if b0 is not None:
        ref=[official_summary(y[folds==f],b0[folds==f])['official_score'] for f in range(5)]
        delta=np.array(fs)-ref;answer.update(paired_fold_deltas=delta.tolist(),positive_folds=int((delta>0).sum()))
        answer['meets_retention']=answer['delta']>=1 and answer['positive_folds']>=4
    return answer

def cross_blend(y,b0,fm,folds):
    out=np.full_like(y,np.nan);records=[]
    for f in range(5):
        train=folds!=f;valid=~train
        scores=[official_summary(y[train],w*b0[train]+(1-w)*fm[train])['official_score'] for w in np.linspace(0,1,11)]
        best=max(scores);idx=max(i for i,s in enumerate(scores) if s==best);w=idx/10
        out[valid]=w*b0[valid]+(1-w)*fm[valid]
        records.append({'fold':f+1,'baseline_weight':w,'selection_wells':int(train.sum()),'validation_wells':int(valid.sum()),'selection_score':best,'own_fold_labels_used':False,'selection_grid_scores':scores})
    return out,records

def select_retained(candidates):
    retained={k:v for k,v in candidates.items() if v.get('meets_retention')}
    if not retained:return None
    best=max(v['delta'] for v in retained.values());near=[k for k,v in retained.items() if best-v['delta']<=.1]
    # Pre-score simplicity: no FM, fewer mechanisms, fewer features, no augmentation,
    # no residual adjustment, finally stable candidate identifier.
    def complexity(k):return ('FM' in k,int('F0' in k)+int('AUG' in k)+int('ALPHA' in k)+int('FM' in k),int('F0' in k),int('AUG' in k),int('ALPHA' in k),k)
    return min(near,key=complexity)
