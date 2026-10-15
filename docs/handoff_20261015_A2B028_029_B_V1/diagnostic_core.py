"""Pure numerical diagnostics. Real SVD fitting is counted by the caller."""
import hashlib, json
import numpy as np

EPSILON = DELTA = 1e-6
BASELINE = 73.71410733861434

class GateError(RuntimeError): pass
def require(condition, message):
    if not condition: raise GateError(message)
def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode()).hexdigest()
def array_hash(value):
    value=np.ascontiguousarray(value,dtype=np.int64)
    return hashlib.sha256(value.dtype.str.encode()+str(value.shape).encode()+value.tobytes()).hexdigest()

def official_summary(y, prediction):
    y, p = np.asarray(y, float), np.asarray(prediction, float)
    require(y.ndim == 2 and y.shape[1] == 12 and p.shape == y.shape, 'SCORE_SHAPE')
    require(np.isfinite(y).all() and np.isfinite(p).all() and (y >= 0).all() and (p >= 0).all(), 'SCORE_VALUES')
    err = np.abs(p-y)/(np.abs(p)+np.abs(y)+EPSILON)
    weighted = err * np.power(0.5, np.arange(1,13))
    losses = {f'm1_to_{n}': float(weighted[:, :n].sum(axis=1).mean()) for n in (1,2,4,12)}
    return {'official_score': float((100*(1-weighted.sum(axis=1))).mean()), 'weighted_losses': losses}

def shape_counts(y):
    y = np.asarray(y, float)
    require(y.ndim == 2 and y.shape[1] == 12 and np.isfinite(y).all() and (y>=0).all(), 'SHAPE_INPUT')
    a, b = y[:, :2].mean(axis=1), y[:, 3:6].mean(axis=1)
    rising, falling = b>1.1*a, b<0.9*a
    require(not (rising & falling).any(), 'SHAPE_OVERLAP')
    return {'上升': int(rising.sum()), '下降': int(falling.sum()), '稳产': int((~rising & ~falling).sum()), '含0值': int((y==0).any(axis=1).sum())}

def project_oracle(z_validation, mean, components, scale_validation, k):
    z, mu, axes, s = map(lambda x: np.asarray(x, float), (z_validation, mean, components, scale_validation))
    require(z.ndim==2 and z.shape[1]==12 and mu.shape==(12,) and axes.shape[1]==12 and s.shape==(len(z),), 'ORACLE_SHAPE')
    require(1<=k<=4 and k<=len(axes) and (s>0).all(), 'ORACLE_K_SCALE')
    basis = axes[:k]
    rebuilt = mu + ((z-mu) @ basis.T) @ basis
    p = np.maximum(np.expm1(rebuilt)*s[:,None], 0)
    require(np.isfinite(p).all(), 'NONFINITE_ORACLE')
    return p

def cross_residual_adjust(y, p, folds):
    """Prescribed diagnostic, not nested model validation. Never fits a model.

    Each held-out fold uses only residual samples from other folds at the same
    horizon. Generated outcomes and candidate points are p_current*exp(e_j).
    """
    y, p, folds = np.asarray(y,float), np.asarray(p,float), np.asarray(folds,int)
    official_summary(y,p)
    require(folds.shape==(len(y),) and len(np.unique(folds))==5, 'ALPHA_FOLDS')
    residual = np.log((y+DELTA)/(p+DELTA))
    answer = np.empty_like(p)
    records=[]
    for f in sorted(np.unique(folds)):
        tr, va = folds!=f, folds==f
        for t in range(12):
            ratios = np.exp(residual[tr,t])
            for i in np.flatnonzero(va):
                outcomes = p[i,t]*ratios
                candidates = np.concatenate(([0.], outcomes))
                err = np.abs(candidates[:,None]-outcomes[None,:])/(candidates[:,None]+outcomes[None,:]+EPSILON)
                answer[i,t] = candidates[np.argmin(err.mean(axis=1))]
        records.append({'outer_fold':int(f),'residual_sample_wells':int(tr.sum()),'validation_wells':int(va.sum()),'same_horizon_only':True,'current_fold_residuals_used':False})
    return answer, records

def eligible_segment_ends(ordinals):
    ordered = sorted(set(int(x) for x in ordinals))
    return [x for i,x in enumerate(ordered) if i==len(ordered)-1 or ordered[i+1]!=x+1]

def historical_event_counts(month_to_target, eligible_ordinals, final_end):
    events=set(int(x) for x in eligible_ordinals)
    out={'prior_segments':0,'qualified_events':0,'rejected_nonconsecutive_or_missing':0,'rejected_refracture':0,'new_m1_labels':0,'new_m2_labels':0}
    for end in eligible_segment_ends(events):
        if end>=final_end: continue
        out['prior_segments']+=1
        window=list(range(end+1,end+13))
        if any(m not in month_to_target or not np.isfinite(month_to_target[m]) or month_to_target[m]<0 for m in window):
            out['rejected_nonconsecutive_or_missing']+=1;continue
        if events.intersection(window): out['rejected_refracture']+=1;continue
        out['qualified_events']+=1;out['new_m1_labels']+=1;out['new_m2_labels']+=1
    return out

def lagged_common_trend(well_histories):
    """Input consists solely of pre-cutoff history, never target-window rows."""
    pooled=[];by_month={}
    for rows in well_histories:
        rows=dict(rows)
        for month,value in rows.items():
            prev=rows.get(month-1,np.nan)
            if np.isfinite(value) and np.isfinite(prev) and value>=0 and prev>=0:
                diff=float(np.log(value+DELTA)-np.log(prev+DELTA))
                pooled.append(diff);by_month.setdefault(month,[]).append(diff)
    common={m:float(np.mean(v)) for m,v in by_month.items() if len(v)>=5}
    require(len(pooled)>=2 and len(common)>=2,'GAMMA_INSUFFICIENT_DATA')
    den=float(np.var(pooled,ddof=0));num=float(np.var(list(common.values()),ddof=0))
    require(den>0,'GAMMA_ZERO_TOTAL_VARIANCE')
    pairs=[(common[m-1],common[m]) for m in sorted(common) if m-1 in common]
    require(len(pairs)>=2,'GAMMA_INSUFFICIENT_ADJACENT_MONTHS')
    pairs=np.asarray(pairs,float)
    require(np.std(pairs[:,0])>0 and np.std(pairs[:,1])>0,'GAMMA_ZERO_PAIR_VARIANCE')
    lag=float(np.corrcoef(pairs[:,0],pairs[:,1])[0,1])
    return {'Dgamma_share':num/den,'Dgamma_lag1':lag,'valid_well_month_differences':len(pooled),'eligible_common_months':len(common),'excluded_months_under_5_wells':sum(len(v)<5 for v in by_month.values()),'adjacent_common_month_pairs':len(pairs),'common_variance_ddof0':num,'pooled_variance_ddof0':den}

def decisions(r):
    f1=max(r[f'F1_oracle_K{k}'] for k in (1,2,3))
    return {
        'F0':{'passed':r['F0_combo_pass_count']>=1,'next':'列入阶段 1 候选特征' if r['F0_combo_pass_count']>=1 else '不列入'},
        'F1':{'passed':f1>=90,'route_2_rejected':r['F1_oracle_K3']<85,'next':'起草路线 ② 预注册' if f1>=90 else ('路线 ② 淘汰' if r['F1_oracle_K3']<85 else '未达90且未触发K3<85；不自动启动下一阶段')},
        'D-α':{'passed':None if r['Dalpha_delta'] is None else r['Dalpha_delta']>=1.0,'next':'UNKNOWN，缺固定逐行OOF' if r['Dalpha_delta'] is None else ('并入路线 ② 最后一步' if r['Dalpha_delta']>=1 else '不并入')},
        'D-β':{'passed':r['Dbeta_increase_m1']>=.3 or r['Dbeta_increase_m2']>=.3,'next':'阶段 1 增加扩样对照' if r['Dbeta_increase_m1']>=.3 or r['Dbeta_increase_m2']>=.3 else '不增加扩样对照'},
        'D-γ':{'passed':r['Dgamma_share']>=.3 and r['Dgamma_lag1']>=.5,'next':'列入阶段 1 候选特征' if r['Dgamma_share']>=.3 and r['Dgamma_lag1']>=.5 else '不列入'}
    }
