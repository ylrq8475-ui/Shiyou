from common import *
import hashlib
h,layer,plan=load()
cs=h["CSLB"].astype("string").str.strip()
vals=sorted(set(v for v in cs.dropna() if v), key=lambda v: hashlib.sha256(v.encode()).hexdigest())
codefor={v:f"CSLB_{i:03d}" for i,v in enumerate(vals,1)}
cand=[v for v,c in codefor.items() if c in ("CSLB_012","CSLB_032")]
print("candidates found:",len(cand), [codefor[v] for v in cand], "rows:",[int((cs==v).sum()) for v in cand])
h["ev"]=cs.isin(cand)
def runs(months):
    m=sorted(set(x.ordinal for x in months)); out=[]
    for x in m:
        if out and x==out[-1][1]+1: out[-1][1]=x
        else: out.append([x,x])
    return out
# ---- test wells
print("\n== TEST ==")
rows=[]
for w,g in h[h.__split=="test"].groupby("WELL_ID"):
    g=g.sort_values("__p"); miss=g[g.RCYL.isna()]
    T=miss.__p.min().ordinal; tgt=sorted(x.ordinal for x in miss.__p)
    contiguous = tgt==list(range(T,T+len(tgt)))
    r=runs(g.loc[g.ev,"__p"]); last=r[-1] if r else None
    obs_after_T = int(g[(g.__p.map(lambda p:p.ordinal)>=T)&g.RCYL.notna()].shape[0])
    anchor_rcyl_obs = bool(g[g.__p.map(lambda p:p.ordinal)==T-1].RCYL.notna().any())
    last_hist = g[g.RCYL.notna()].__p.max().ordinal
    rows.append(dict(n_tgt=len(tgt),contig=contiguous,obs_after_T=obs_after_T,n_runs=len(r),
        last_run_len=None if not last else last[1]-last[0]+1,
        T_minus_runstart=None if not last else T-last[0], T_minus_runend=None if not last else T-last[1],
        month_before_T_has_RCYL=anchor_rcyl_obs, T_minus_last_observed=T-last_hist,
        ev_rows_in_target=int(g[g.ev & g.RCYL.isna()].shape[0])))
t=pd.DataFrame(rows); print(t.to_string(index=False))
# future covariates present in target months
tt=h[(h.__split=="test")&h.RCYL.isna()]
print("\nnon-missing share in TEST TARGET months:",{c:round(float(tt[c].notna().mean()),2) for c in ["CYFS","SCTS","BJ","CC","CC1","PL","BX","YY","TY","LY","RCYL1","HS","CMD","CCJHWND","CCYND","SXDL","XXDL","CSLB","BZ"]})
print("SCTS in target months: min/median/max",tt.SCTS.min(),tt.SCTS.median(),tt.SCTS.max(), " zero-share",round(float((tt.SCTS==0).mean()),3))
# ---- train
print("\n== TRAIN ==")
tr=h[h.__split=="train"].copy(); tr["o"]=tr.__p.map(lambda p:p.ordinal)
lens=[];nruns=[]
prof={}
for w,g in tr.groupby("WELL_ID"):
    g=g.set_index("o").sort_index(); r=runs(g.loc[g.ev].__p)
    nruns.append(len(r))
    for s,e in r:
        lens.append(e-s+1)
        pre=g.RCYL.reindex(range(s-3,s)).mean()
        if not pre or not np.isfinite(pre) or pre<=0: continue
        for k in range(-2,6):
            for ref,nm in ((s,"start"),(e,"end")):
                v=g.RCYL.get(ref+k,np.nan); d=g.SCTS.get(ref+k,np.nan)
                prof.setdefault((nm,k),[]).append((v/pre, d))
print("runs per well:",pd.Series(nruns).value_counts().sort_index().to_dict())
print("run length dist:",pd.Series(lens).value_counts().sort_index().to_dict())
print("RCYL / pre3mean and SCTS around event (median, n):")
for nm in ("start","end"):
    print(" rel to run",nm, {k:(round(float(np.nanmedian([a for a,_ in prof[(nm,k)]])),2), round(float(np.nanmedian([b for _,b in prof[(nm,k)]])),1)) for k in range(-2,6) if (nm,k) in prof})
# multi-month runs only
print("multi-month runs only:")
