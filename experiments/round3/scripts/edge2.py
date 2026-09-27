import sys
sys.excepthook=lambda t,v,tb: print('ERROR', t.__name__, '(details suppressed)')
from exp import *
from sklearn.linear_model import RidgeCV
import json
c=cfg(); tables=load_multisource_split(c,"train"); bp=build_training_samples(tables,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
E=pd.read_pickle("edge_E.pkl"); T=pd.read_pickle("edge_T.pkl")
last=E[E["last"]].set_index("w")
# regime: level in top 40% of train events AND HS in bottom 60%  (test wells mostly here)
lv_cut=E.lvl.quantile(.6); hs_cut=E.hs.quantile(.6)
print("test wells in regime (lvl>=p60 & hs<=p60):",int(((T.lvl>=lv_cut)&(T.hs<=hs_cut)).sum()),"/10;  lvl>=p60:",int((T.lvl>=lv_cut).sum()),"; hs<=p60:",int((T.hs<=hs_cut).sum()))
reg=[w for w in last.index if last.loc[w,"lvl"]>=lv_cut and last.loc[w,"hs"]<=hs_cut and w in set(bp.WELL_ID)]
reg_lv=[w for w in last.index if last.loc[w,"lvl"]>=lv_cut and w in set(bp.WELL_ID)]
print("train last-event wells in regime:",len(reg)," (level-only regime:",len(reg_lv),")")
gm=lambda ws,arrs: np.exp(sum(w*np.log(a+1e-3) for w,a in zip(ws,arrs)))-1e-3
A=np.load("m_A2B.npy")[:2]; V=np.load("m_V7.npy")[:2]; Tt=np.load("ts_g1_all_hgb_w1.npy")[:2]; L=[np.load(f"lean_oof_{i}.npy") for i in range(2)]
# linear extrapolating model: per-horizon ridge on log(RCYL_h/prev) with event-level features; trained on ALL train events of training-fold wells
def lin_oof(use_anc):
    feats=["lvl","hs","liq","trend"]+(["anc"] if use_anc else [])
    # need per-horizon targets for all events: rebuild from grids
    from ts import grids
    G=grids(tables,c["anchors"]["eligible_event_values"])
    rows=[]
    for w,g in G.items():
        rc=g["RCYL"]
        for s,e in g["runs"]:
            prev=rc[e-1] if e>=1 else np.nan; f=rc[e+1:e+13]
            if not(np.isfinite(prev) and prev>0) or len(f)<12 or not np.isfinite(f).all(): continue
            pre=rc[max(0,e-3):e]; d=dict(w=w,e=e,lvl=np.log(np.nanmean(pre)),hs=np.nanmean(g["HS"][max(0,e-3):e]),liq=np.log(np.nanmean(g["RCYL1"][max(0,e-3):e])),
                anc=np.log((rc[e]+1e-3)/(prev+1e-3)),trend=np.log((rc[e-1]+1e-3)/(np.nanmean(rc[max(0,e-6):e-3])+1e-3)) if e>=4 else 0.0,prev=prev)
            for h in range(12): d[f"y{h+1}"]=np.log((f[h]+1e-2)/(prev+1e-2))
            rows.append(d)
    D=pd.DataFrame(rows).fillna(0.0)
    # last-event rows aligned to bp order
    lastrow={}
    for w,grp in bp.groupby("WELL_ID"):
        g=G[w]; rc=g["RCYL"]; e=pd.Timestamp(grp.anchor_time.iloc[0]).to_period("M").ordinal-g["o0"]
        pre=rc[max(0,e-3):e]; prev=rc[e-1]
        if not(np.isfinite(prev) and prev>0):
            pp=pre[np.isfinite(pre)&(pre>0)]; prev=pp.mean() if len(pp) else 1.0
        lastrow[w]=pd.Series(dict(lvl=np.log(np.nanmean(pre)+1e-3),hs=np.nanmean(g["HS"][max(0,e-3):e]),liq=np.log(np.nanmean(g["RCYL1"][max(0,e-3):e])+1e-3),
            anc=np.log((rc[e]+1e-3)/(prev+1e-3)),trend=np.log((rc[e-1]+1e-3)/(np.nanmean(rc[max(0,e-6):e-3])+1e-3)) if e>=4 else 0.0,prev=prev)).fillna(0.0)
    outs=[]
    for folds in make_splits(bp.WELL_ID.to_numpy(),range(1,2)):
        oof=np.full(len(bp),np.nan)
        for tr_,va in folds:
            trw=set(bp.WELL_ID.iloc[tr_]); Dt=D[D.w.isin(trw)]
            mu,sd=Dt[feats].mean(),Dt[feats].std()
            for h in range(1,13):
                m=RidgeCV(alphas=[0.3,1,3,10,30]).fit((Dt[feats]-mu)/sd,Dt[f"y{h}"])
                idx=[i for i in va if bp.horizon.iloc[i]==h]
                X=pd.DataFrame([lastrow[bp.WELL_ID.iloc[i]][feats] for i in idx]).astype(float)
                pv=np.array([lastrow[bp.WELL_ID.iloc[i]]["prev"] for i in idx])
                oof[idx]=np.clip(np.exp(m.predict((X-mu)/sd))*(pv+1e-2)-1e-2,0,None)
        outs.append(oof)
    return outs
Lin=lin_oof(False); LinA=lin_oof(True)
subs={"A2B":A,"S1":[gm((.7,.3),(a,t)) for a,t in zip(A,Tt)],"S3":[a*np.exp(-.15) for a in A],"S4":[gm((.5,.5),(a,l)) for a,l in zip(A,L)],"v7":V,
      "LIN(no anc)":Lin,"LIN(+anc)":LinA,"A2B*LIN .5":[gm((.5,.5),(a,l)) for a,l in zip(A[:1],Lin)]}
plat={"A2B":86,"S1":84,"S3":83,"S4":82,"v7":80.54}
tl=json.load(open("tl.json"))
print(f"\n{'':12s} {'all81':>6s} {'test-like':>9s} {'regime':>7s} {'level-regime':>12s}  platform")
for k,P in subs.items():
    ws=pd.concat([well_scores(bp,np.clip(p,0,None)) for p in P],axis=1).mean(1)
    print(f"{k:12s} {ws.mean():6.2f} {ws.loc[tl].mean():9.2f} {ws.loc[reg].mean():7.2f} {ws.loc[reg_lv].mean():12.2f}  {plat.get(k,'')}")
