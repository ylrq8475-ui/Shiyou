"""Global sliding-window time-series model. g=1: A2B info set (last observed = anchor-1); g=0: v7 info set."""
from exp import *
import json, time
from sklearn.ensemble import HistGradientBoostingRegressor, ExtraTreesRegressor
COLS=["RCYL","SCTS","HS","RCYL1","YY","TY","PL","BJ","CC"]
def grids(tables, cands):
    h=tables.history.copy(); h["WELL_ID"]=h.WELL_ID.astype(str)
    h["o"]=pd.to_datetime(h.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
    out={}
    for w,g in h.groupby("WELL_ID"):
        g=g.set_index("o").sort_index(); idx=range(g.index.min(),g.index.max()+1)
        G={c:pd.to_numeric(g[c],errors="coerce").reindex(idx).to_numpy(float) for c in COLS}
        G["ev"]=g.CSLB.astype("string").str.strip().isin(cands).fillna(False).reindex(idx).fillna(False).to_numpy(bool)
        G["o0"]=g.index.min(); G["n"]=len(idx)
        r=[]; 
        for i,e in enumerate(G["ev"]):
            if e:
                if r and r[-1][1]==i-1: r[-1][1]=i
                else: r.append([i,i])
        G["runs"]=r; out[w]=G
    return out
def feats(G, L, g):
    """features using months <= L (index in grid); target starts at L+g+1."""
    rc=G["RCYL"]
    def at(c,i): a=G[c]; return a[i] if 0<=i<len(a) else np.nan
    lvl=rc[L]
    if not (np.isfinite(lvl) and lvl>0):
        w=rc[max(0,L-2):L+1]; w=w[np.isfinite(w)&(w>0)]; lvl=w.mean() if len(w) else 1.0
    f={"log_lvl":np.log(lvl)}
    for k in range(12): f[f"lr_{k}"]=np.log1p(at("RCYL",L-k)/lvl) if L-k>=0 and np.isfinite(at("RCYL",L-k)) else np.nan
    for wdw in (3,6,12):
        seg=rc[max(0,L-wdw+1):L+1]; seg=seg[np.isfinite(seg)]
        f[f"m{wdw}"]=np.log1p(seg.mean()/lvl) if len(seg) else np.nan
        f[f"s{wdw}"]=seg.std()/lvl if len(seg)>1 else np.nan
        ls=np.log1p(seg/lvl)
        f[f"tr{wdw}"]=np.polyfit(np.arange(len(ls)),ls,1)[0] if len(ls)>=3 else np.nan
    for c in ("SCTS","HS","YY","TY","PL","BJ","CC"):
        f[f"{c}_0"]=at(c,L); seg=G[c][max(0,L-2):L+1]; f[f"{c}_m3"]=np.nanmean(seg) if np.isfinite(seg).any() else np.nan
    f["HS_d6"]=at("HS",L)-at("HS",L-6)
    f["liq_ratio"]=at("RCYL1",L)/lvl if np.isfinite(at("RCYL1",L)) else np.nan
    runs=[r for r in G["runs"] if r[0]<=L+g]
    f["n_runs"]=len(runs); f["hist_len"]=L+1
    if runs:
        s,e=runs[-1]; f["since_end"]=(L+g)-min(e,L+g); f["run_len"]=min(e,L+g)-s+1; f["ev_recent"]=int(f["since_end"]<=0)
        pre=rc[max(0,s-3):s]; pre=pre[np.isfinite(pre)]
        f["lvl_over_pre"]=np.log1p(lvl/pre.mean()) if len(pre) and pre.mean()>0 else np.nan
        if len(runs)>1:
            ps,pe=runs[-2]; f["gap_prev"]=s-pe
            pp=rc[max(0,ps-3):ps]; po=rc[pe+1:min(pe+4,s)]; pp=pp[np.isfinite(pp)]; po=po[np.isfinite(po)]
            f["prev_uplift"]=np.log1p(po.mean()/pp.mean()) if len(pp) and len(po) and pp.mean()>0 else np.nan
    else:
        f["since_end"]=99; f["run_len"]=0; f["ev_recent"]=0
    return f, lvl
def windows(G, g, origin_filter):
    rows=[]; n=G["n"]; rc=G["RCYL"]
    for L in range(5, n-g-12):
        tgt=rc[L+g+1:L+g+13]
        if len(tgt)<12 or not np.isfinite(tgt).all(): continue
        if not origin_filter(G,L,g): continue
        f,lvl=feats(G,L,g); rows.append((L,f,lvl,tgt))
    return rows
def is_event_origin(G,L,g):
    return any(e==L+g for s,e in G["runs"])
def build_rows(Gs, wells, g, mode):
    X=[];Y=[];W=[];meta=[]
    flt={"all":lambda G,L,g:True,"event":is_event_origin}[mode]
    for w in wells:
        for L,f,lvl,tgt in windows(Gs[w],g,flt):
            evo=is_event_origin(Gs[w],L,g)
            for h in range(12):
                d=dict(f); d["h"]=h+1; d["event_origin"]=int(evo); X.append(d); Y.append(np.log1p(max(tgt[h],0)/lvl)); W.append(1.0); meta.append((w,L,evo))
    return pd.DataFrame(X), np.array(Y), np.array(W), meta
def eval_rows(Gs, bp, g):
    X=[];lv=[]
    for w,grp in bp.groupby("WELL_ID",sort=False):
        G=Gs[w]; e=pd.Timestamp(grp.anchor_time.iloc[0]).to_period("M").ordinal-G["o0"]; L=e-g
        f,lvl=feats(G,L,g)
        for h in grp.horizon: d=dict(f); d["h"]=int(h); d["event_origin"]=1; X.append(d); lv.append(lvl)
    return pd.DataFrame(X), np.array(lv)
def make_model(kind, seed=0):
    if kind=="hgb": return HistGradientBoostingRegressor(max_iter=400,learning_rate=0.04,max_leaf_nodes=15,min_samples_leaf=40,l2_regularization=1.0,random_state=seed)
    return ExtraTreesRegressor(n_estimators=150,min_samples_leaf=20,max_features=0.4,max_samples=None,n_jobs=-1,random_state=seed)
if __name__=="__main__":
    t0=time.time(); g=int(sys.argv[1]); mode=sys.argv[2]; kind=sys.argv[3]; wev=float(sys.argv[4]); ns=int(sys.argv[5])
    c=cfg(); tables=load_multisource_split(c,"train"); bp=build_training_samples(tables,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
    Gs=grids(tables,c["anchors"]["eligible_event_values"]); tl=set(json.load(open("tl.json")))
    wells=list(pd.unique(bp.WELL_ID)); allw=[w for w in Gs]  # includes 7 excluded wells as extra training sequences
    Xall,Yall,Wall,meta=build_rows(Gs,allw,g,mode); mw=np.array([m[0] for m in meta]); evo=np.array([m[2] for m in meta])
    Wall=np.where(evo,wev,1.0)
    Xe,lv=eval_rows(Gs,bp,g); cols=list(Xall.columns); Xe=Xe.reindex(columns=cols)
    splits=make_splits(bp.WELL_ID.to_numpy(),range(1,ns+1)); oofs=[]
    for folds in splits:
        oof=np.full(len(bp),np.nan)
        for tr,va in folds:
            trw=set(bp.WELL_ID.iloc[tr]); valw=set(bp.WELL_ID.iloc[va])
            m=~np.isin(mw,list(valw))
            mdl=make_model(kind); 
            Xf=Xall[m].fillna(-999) if kind=="et" else Xall[m]
            mdl.fit(Xf,Yall[m],sample_weight=Wall[m])
            Xv=Xe.iloc[va].fillna(-999) if kind=="et" else Xe.iloc[va]
            oof[va]=np.clip(np.expm1(mdl.predict(Xv))*lv[va],0,None)
        oofs.append(oof)
    tag=f"ts_g{g}_{mode}_{kind}_w{wev:g}"; np.save(f"{tag}.npy",np.array(oofs))
    s=[well_scores(bp,o) for o in oofs]
    print(f"[{tag}] windows={len(Xall)//12} (event-origin {int(evo.sum()//12)}) all={np.mean([x.mean() for x in s]):.2f} test-like={np.mean([x[x.index.isin(tl)].mean() for x in s]):.2f} fixed={s[0].mean():.2f} {time.time()-t0:.0f}s")
