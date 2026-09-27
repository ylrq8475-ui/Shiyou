import os, sys, json, copy, hashlib, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
os.environ["COMPETITION_DATA_ACCESS_ACK"]="I_AM_AUTHORIZED"
from oil_uplift.config import load_config
from oil_uplift.multistep import load_multisource_split, build_training_samples, build_test_samples
from oil_uplift.training import configured_feature_columns, _model_pipeline, _fit_pipeline, predict_pipeline_output
from oil_uplift.scoring import official_twelve_month_score
from sklearn.model_selection import GroupKFold
REPO=Path(os.path.expanduser("~/work/repo"))
CFG=REPO/"configs/private_data_inferred_trial_safe_plus_layer.yaml"
NAME="extra_trees_log_ratio_last"
EXTRA_HIST=["RCYL1","HS","YCYL1","YCYL","HSYCYL","NCYL","LJCYL"]
FUT=["SCTS","YY","TY","BJ","CC","CC1","PL"]

def cfg(extra_hist=False):
    c=load_config(CFG); c=copy.deepcopy(c)
    if extra_hist: c["features"]["history_numeric_columns"]=list(c["features"]["history_numeric_columns"])+EXTRA_HIST
    return c

def runs_of(months):
    out=[]
    for x in sorted(set(months)):
        if out and x==out[-1][1]+1: out[-1][1]=x
        else: out.append([x,x])
    return out

def event_features(hist, cands, well, anchor_o):
    g=hist[hist.WELL_ID==well].copy()
    g["o"]=pd.to_datetime(g.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
    g=g[g.o<=anchor_o].set_index("o").sort_index()
    r=runs_of(g.index[g.CSLB.astype("string").str.strip().isin(cands).fillna(False).to_numpy()])
    f={}
    if not r: return f
    s,e=r[-1]
    rc=pd.to_numeric(g.RCYL,errors="coerce")
    pre=rc.reindex(range(s-3,s)).mean()
    f["ev__run_len"]=e-s+1
    f["ev__pre_level"]=pre
    f["ev__anchor_uplift"]=rc.get(e,np.nan)/pre if pre and pre>0 else np.nan
    f["ev__start_uplift"]=rc.get(s,np.nan)/pre if pre and pre>0 else np.nan
    f["ev__n_prev"]=len(r)-1
    for col in ("SCTS",):
        f[f"ev__{col}_anchor"]=pd.to_numeric(g[col],errors="coerce").get(e,np.nan)
    if len(r)>1:
        ps,pe=r[-2]; ppre=rc.reindex(range(ps-3,ps)).mean()
        post=rc.reindex(range(pe+1,min(pe+4,s))).mean()
        f["ev__gap_prev"]=s-pe
        f["ev__prev_uplift"]=post/ppre if ppre and ppre>0 else np.nan
        post6=rc.reindex(range(pe+1,min(pe+7,s)))
        f["ev__prev_decay"]=(post6.iloc[-1]/post6.iloc[0]) if post6.notna().sum()>=4 and post6.iloc[0]>0 else np.nan
    return f

def plan_features(plan, well, anchor_o, run_start_o):
    p=plan[plan["井号"].astype(str)==well].copy()
    p["o"]=pd.to_datetime(p["完工日期"],errors="coerce").dt.to_period("M").map(lambda q:q.ordinal if pd.notna(q) else -10**9)
    before=p[p.o<=anchor_o].sort_values("o")
    f={"planev__n_before":len(before)}
    if before.empty: return f
    last=before.iloc[-1]
    f["planev__months_since"]=anchor_o-last.o
    f["planev__matched"]=int(run_start_o-1<=last.o<=anchor_o)
    for c in p.columns:
        if c in ("井号","完工日期","o"): continue
        if c in ("层位","压裂方式"): f[f"planev__{c}"]=str(last[c])
        else: f[f"planev__{c}"]=float(pd.to_numeric(pd.Series([last[c]]),errors="coerce").iloc[0])
    return f

def future_features(hist, well, anchor_o, horizon):
    g=hist[hist.WELL_ID==well].copy()
    g["o"]=pd.to_datetime(g.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
    row=g[g.o==anchor_o+horizon]
    return {f"fut__{c}":(pd.to_numeric(row[c],errors="coerce").iloc[0] if len(row) else np.nan) for c in FUT}

def augment(panel, tables, c, use_event=False, use_plan=False, use_future=False):
    cands=c["anchors"]["eligible_event_values"]; hist=tables.history.copy(); hist["WELL_ID"]=hist.WELL_ID.astype(str)
    out=panel.copy(); out["WELL_ID"]=out.WELL_ID.astype(str)
    cache={}
    for w,g in out.groupby("WELL_ID",sort=False):
        ao=pd.Timestamp(g.anchor_time.iloc[0]).to_period("M").ordinal
        f={}
        if use_event or use_plan:
            ef=event_features(hist,cands,w,ao)
            if use_event: f.update(ef)
            if use_plan: f.update(plan_features(tables.plan,w,ao,ao-ef.get("ev__run_len",1)+1))
        cache[w]=(ao,f)
    add=pd.DataFrame([cache[w][1] for w in out.WELL_ID],index=out.index)
    out=pd.concat([out,add],axis=1)
    if use_future:
        fut=pd.DataFrame([future_features(hist,w,cache[w][0],h) for w,h in zip(out.WELL_ID,out.horizon)],index=out.index)
        out=pd.concat([out,fut],axis=1)
    return out

def select(panel,c,prefixes):
    base=configured_feature_columns(panel,c)
    extra=[col for col in panel.columns if any(str(col).startswith(p) for p in prefixes) and not panel[col].isna().all()]
    return base+extra

def cv(panel,feats,c,splits,name=NAME):
    x=panel.loc[:,feats]; y=panel.RCYL; oofs=[]
    for folds in splits:
        oof=np.full(len(panel),np.nan)
        for tr,va in folds:
            est=_model_pipeline(name,x.iloc[tr],c)
            _fit_pipeline(est,name,x.iloc[tr],y.iloc[tr],panel.horizon.iloc[tr],panel.iloc[tr])
            oof[va]=np.clip(predict_pipeline_output(est,name,x.iloc[va],panel.iloc[va]),0,None)
        oofs.append(oof)
    return oofs

def make_splits(groups, seeds):
    splits=[list(GroupKFold(5).split(np.zeros(len(groups)),groups=groups))]
    uw=pd.unique(groups)
    for s in seeds:
        rng=np.random.default_rng(s); perm=rng.permutation(len(uw)); fold_of={w:i%5 for i,w in zip(range(len(uw)),uw[perm])}
        f=np.array([fold_of[w] for w in groups])
        splits.append([(np.where(f!=k)[0],np.where(f==k)[0]) for k in range(5)])
    return splits

def well_scores(panel,pred):
    d=panel[["WELL_ID","horizon","RCYL"]].copy(); d["p"]=pred
    return pd.Series(official_twelve_month_score(d,truth_column="RCYL",prediction_column="p",epsilon=1e-6).components)

def lean(panel, extra_prefixes=()):
    keep=["horizon","forecast_step","history_month_count"]
    for col in ["RCYL","RCYL1","HS","SCTS","YY","TY","PL","BJ","CC","CMD","SXDL","XXDL"]:
        for s in ["last","lag_2","lag_3","roll_3_mean","roll_6_mean","roll_12_mean","roll_12_std","trend_3","trend_6","trend_12"]:
            k=f"history__{col}__{s}"
            if k in panel and not panel[k].isna().all(): keep.append(k)
    keep+=[c for c in panel.columns if str(c).startswith("layer__") and str(c).endswith("__mean")]
    keep+=[c for c in panel.columns if any(str(c).startswith(p) for p in extra_prefixes) and not panel[c].isna().all()]
    return keep
