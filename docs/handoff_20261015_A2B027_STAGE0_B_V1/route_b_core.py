"""Locked Route B numeric contracts; no data loading or fitting at import."""
import hashlib, json, math
import numpy as np

BASELINE=73.71410733861434
TOLERANCE=1e-9
EPSILON=1e-6
STARTUP='启动条件：第 11 项经 Codex 判为"通过"，且用户另行批准 B-2。'
TABLE='''| Codex 确认的结果 | 下一步 |
|---|---|
| 任一硬门禁失败（泄漏、错位、井级隔离、指标） | 路线 B 停止 |
| OOF 分数差 ≥ +1.0 | 建议用户考虑保留候选；交付必须含 train.py；平台提交另行批准 |
| 0 < 分数差 < +1.0 | 弱信号，交用户决定，默认不执行 |
| 分数差 ≤ 0 | 路线 B 淘汰 |'''

class GateError(Exception): pass
def require(value,code):
    if not value: raise GateError(code)
def fingerprint(x): return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def array_hash(x):
    x=np.ascontiguousarray(x,dtype=np.int64)
    return hashlib.sha256(x.dtype.str.encode()+str(x.shape).encode()+x.tobytes()).hexdigest()
def zero_labels(y):
    y=np.asarray(y,dtype=float)
    require(np.isfinite(y).all() and (y>=0).all(),'INVALID_TARGET_LABEL')
    return (y==0).astype(np.int64)
def raw_scale(x):
    x=np.asarray(x,dtype=float)
    return np.where(np.isfinite(x)&(x>0),x,1.)
def losses(y,p):
    y,p=np.asarray(y,float),np.asarray(p,float)
    require(y.shape==p.shape and np.isfinite(y).all() and np.isfinite(p).all() and (y>=0).all() and (p>=0).all(),'INVALID_SCORING_VALUES')
    return np.abs(p-y)/(np.abs(p)+np.abs(y)+EPSILON)
def numeric_summary(frame,p):
    groups=frame.WELL_ID.to_numpy(); y=frame.RCYL.to_numpy(float); h=frame.horizon.to_numpy(int)
    ell=losses(y,p); w=np.power(.5,h.astype(float))
    per=[]; partial={str(k):[] for k in (1,2,4,12)}
    for g in dict.fromkeys(groups):
        keep=groups==g
        require(sorted(h[keep].tolist())==list(range(1,13)),'SCORING_TARGET_HORIZONS')
        per.append(float(np.sum(w[keep]*ell[keep])))
        for k in (1,2,4,12):partial[str(k)].append(float(np.sum(w[keep&(h<=k)]*ell[keep&(h<=k)])))
    require(bool(per),'EMPTY_OFFICIAL_SCORE')
    return {'official_score':float(np.mean([100.*(1.-x) for x in per])),'official_weighted_loss':float(np.mean(per)),'weighted_loss_by_horizon_prefix':{k:float(np.mean(v)) for k,v in partial.items()},'wells':len(per),'rows':len(frame)}
def positive_inner_loss(frame,p):
    groups=frame.WELL_ID.to_numpy(); y=frame.RCYL.to_numpy(float);h=frame.horizon.to_numpy(int)
    ell=losses(y,p);w=np.power(.5,h.astype(float)); values=[]
    for g in dict.fromkeys(groups):
        mask=(groups==g)&(y>0)
        if mask.any():values.append(float(np.sum(w[mask]*ell[mask])/np.sum(w[mask])))
    require(bool(values),'INNER_POSITIVE_LOSS_UNDEFINED')
    result=float(np.mean(values));require(math.isfinite(result) and 0<=result<=1,'INNER_POSITIVE_LOSS_INVALID')
    return result,{'positive_target_rows':int((y>0).sum()),'positive_target_wells':len(values),'positive_conditional_weighted_loss':result}
def tau_from_folds(values):
    require(len(values)==3 and all(math.isfinite(x) and 0<=x<=1 for x in values),'INNER_TAU_ESTIMATES_INVALID')
    lp=float(np.mean(values));return (1.-lp)/(2.-lp),lp
def zero_probability(model,x):
    classes=np.asarray(model.classes_)
    require(len(classes) in (1,2) and set(classes.tolist())<=set((0,1)),'CLASS_LABEL_IDENTITY')
    proba=np.asarray(model.predict_proba(x),float)
    require(proba.shape==(len(x),len(classes)) and np.isfinite(proba).all(),'CLASS_PROBABILITY_SHAPE')
    if 1 not in classes:return np.zeros(len(x))
    result=proba[:,int(np.flatnonzero(classes==1)[0])]
    require(((result>=0)&(result<=1)).all(),'CLASS_PROBABILITY_RANGE')
    return result
def route_prediction(b0,q,tau):
    b0,q=np.asarray(b0,float),np.asarray(q,float)
    require(b0.shape==q.shape and np.isfinite(b0).all() and (b0>=0).all() and np.isfinite(q).all() and ((q>=0)&(q<=1)).all(),'ROUTING_INPUT_INVALID')
    require(math.isfinite(tau) and 0<=tau<=.5,'TAU_RANGE')
    route=q>tau;answer=b0.copy();answer[route]=0.
    require(np.array_equal(answer[~route],b0[~route]),'NONZERO_BRANCH_CHANGED')
    return answer,route
def decision(delta,hard_pass):
    if not hard_pass:return TABLE.splitlines()[2]
    require(math.isfinite(delta),'UNDEFINED_DECISION_DELTA')
    return TABLE.splitlines()[3 if delta>=1. else 4 if delta>0 else 5]

class FitBudget:
    def __init__(self):self.counts={'model_entered':0,'model_completed':0,'model_failed':0,'preprocessor_entered':0,'preprocessor_completed':0,'preprocessor_failed':0,'retries':0,'inner_regressor':0,'outer_regressor':0,'outer_classifier':0,'inner_classifier':0,'full_fits':0}
    def enter(self,kind,role):
        require(kind in ('model','preprocessor'),'UNKNOWN_FIT_CATEGORY')
        require(self.counts[kind+'_entered']<(25 if kind=='model' else 20),'LOCKED_FIT_BUDGET_EXHAUSTED')
        self.counts[kind+'_entered']+=1
        if kind=='model':self.counts[role]+=1
    def completed(self,kind):self.counts[kind+'_completed']+=1
    def failed(self,kind):self.counts[kind+'_failed']+=1
    def snapshot(self):return dict(self.counts)
