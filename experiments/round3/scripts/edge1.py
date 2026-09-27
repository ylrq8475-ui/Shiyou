from exp import *
from ts import grids
import json
c=cfg(); cands=c["anchors"]["eligible_event_values"]
tr=load_multisource_split(c,"train"); te=load_multisource_split(c,"test")
G=grids(tr,cands); Gt=grids(te,cands)
def ev_rows(G, test=False):
    out=[]
    for w,g in G.items():
        rc=g["RCYL"]; runs=g["runs"]
        if test:
            T=int(np.where(~np.isfinite(rc))[0].min()); runs=[r for r in runs if r[1]==T-1][-1:] 
        for s,e in runs:
            prev=rc[e-1] if e-1>=0 else np.nan
            if not (np.isfinite(prev) and prev>0): continue
            pre=rc[max(0,e-3):e]; hs=g["HS"][max(0,e-3):e]; liq=g["RCYL1"][max(0,e-3):e]
            d=dict(w=w,last=(s,e)==tuple(g["runs"][-1]) if not test else True,lvl=np.log(np.nanmean(pre)),hs=np.nanmean(hs),liq=np.log(np.nanmean(liq)),
                   anc=np.log((rc[e]+1e-3)/(prev+1e-3)), trend=np.log((rc[e-1]+1e-3)/(np.nanmean(rc[max(0,e-6):e-3])+1e-3)) if e>=4 else np.nan, oil_frac=np.log(1-np.nanmean(hs)/100))
            if not test:
                f=rc[e+1:e+13]
                if len(f)<12 or not np.isfinite(f).all(): continue
                d["y13"]=np.log((f[:3].mean()+1e-2)/(prev+1e-2)); d["y46"]=np.log((f[3:6].mean()+1e-2)/(prev+1e-2)); d["y712"]=np.log((f[6:].mean()+1e-2)/(prev+1e-2))
            out.append(d)
    return pd.DataFrame(out)
E=ev_rows(G); T=ev_rows(Gt,True)
E=E[np.isfinite(E.y13)]
print("train events with full window:",len(E)," (last events:",int(E['last'].sum()),")  test wells:",len(T))
# ranges
for k in ["lvl","hs","liq","oil_frac"]:
    lo,hi=E[k].quantile([.05,.95]); mn,mx=E[k].min(),E[k].max()
    print(f" {k:8s} train p5..p95 [{lo:.2f},{hi:.2f}] min..max [{mn:.2f},{mx:.2f}] | test outside p5-p95: {int(((T[k]<lo)|(T[k]>hi)).sum())}  outside min-max: {int(((T[k]<mn)|(T[k]>mx)).sum())}")
print("\n== 压后增幅 y13=log(前3月均产/锚点前一月) 与锚点前状态的关系 (所有训练事件)")
for k in ["hs","oil_frac","lvl","liq","anc","trend"]:
    s=E[[k,"y13","y712"]].dropna()
    b=np.polyfit(s[k],s.y13,1)[0]
    print(f" {k:8s} spearman(y13)={s[k].rank().corr(s.y13.rank()):+.2f}  spearman(y7-12)={s[k].rank().corr(s.y712.rank()):+.2f}  OLS slope(y13)={b:+.3f}")
print("\n== 按含水分组 (训练事件)")
E["hs_bin"]=pd.qcut(E.hs,5); print(E.groupby("hs_bin",observed=True).agg(n=("y13","size"),uplift_h1_3=("y13",lambda s:round(float(np.exp(s.median())),2)),uplift_h7_12=("y712",lambda s:round(float(np.exp(s.median())),2))).to_string())
E["lvl_bin"]=pd.qcut(E.lvl,5); print(E.groupby("lvl_bin",observed=True).agg(n=("y13","size"),uplift_h1_3=("y13",lambda s:round(float(np.exp(s.median())),2)),uplift_h7_12=("y712",lambda s:round(float(np.exp(s.median())),2))).to_string())
print("\ntest wells per HS bin:",pd.cut(T.hs,[-1]+[b.right for b in E.hs_bin.cat.categories[:-1]]+[101]).value_counts(sort=False).tolist(), " per level bin:",pd.cut(T.lvl,[-99]+[b.right for b in E.lvl_bin.cat.categories[:-1]]+[99]).value_counts(sort=False).tolist())
E.to_pickle("edge_E.pkl"); T.to_pickle("edge_T.pkl")
