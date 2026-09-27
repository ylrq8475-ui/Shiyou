from exp import *
c=cfg(); cands=c["anchors"]["eligible_event_values"]
h=pd.concat([load_multisource_split(c,s).history.assign(split=s) for s in ("train","test")],ignore_index=True)
h["WELL_ID"]=h.WELL_ID.astype(str); h["o"]=pd.to_datetime(h.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
h["RCYL"]=pd.to_numeric(h.RCYL,errors="coerce"); h["SCTS"]=pd.to_numeric(h.SCTS,errors="coerce")
# 1) generic month-to-month persistence of zero production (all train months)
tr=h[h.split=="train"].sort_values(["WELL_ID","o"]).copy()
tr["prev"]=tr.groupby("WELL_ID").RCYL.shift(1); tr["prev_o"]=tr.groupby("WELL_ID").o.shift(1)
tr=tr[tr.prev_o==tr.o-1]
print("train months RCYL==0 share:",round(float((tr.RCYL==0).mean()),4))
print("P(next=0 | cur=0):",round(float((tr[tr.prev==0].RCYL==0).mean()),3),"n=",int((tr.prev==0).sum()))
print("P(next=0 | cur>0):",round(float((tr[tr.prev>0].RCYL==0).mean()),4))
# 2) after-event windows (all events w/ observed following months), keyed by anchor RCYL==0
rows=[]
for w,g in tr.groupby("WELL_ID"):
    pass
H=h[h.split=="train"].set_index(["WELL_ID","o"]).sort_index()
ev=[]
for w,g in h[h.split=="train"].groupby("WELL_ID"):
    g=g.set_index("o").sort_index()
    r=runs_of(g.index[g.CSLB.astype("string").str.strip().isin(cands).fillna(False).to_numpy()])
    for s,e in r:
        a=g.RCYL.get(e,np.nan); sc=g.SCTS.get(e,np.nan)
        fut=g.RCYL.reindex(range(e+1,e+13))
        ev.append(dict(anc0=a==0, scts0=sc==0, nz=[(fut.iloc[k]==0) if pd.notna(fut.iloc[k]) else np.nan for k in range(12)]))
E=pd.DataFrame(ev)
for key in ("anc0",):
    for val in (True,False):
        sub=E[E[key]==val]
        m=np.array([[x for x in r] for r in sub.nz],dtype=float)
        print(f"events {key}={val}: n={len(sub)}  P(zero) by horizon:",np.round(np.nanmean(m,axis=0),2).tolist() if len(sub) else None)
# 3) test: anchor month state (aggregate only)
te=h[h.split=="test"]
cnt=0;cnt_s=0; lastzero=0
for w,g in te.groupby("WELL_ID"):
    g=g.set_index("o").sort_index(); T=g[g.RCYL.isna()].index.min()
    a=g.RCYL.get(T-1); sc=g.SCTS.get(T-1)
    cnt+=int(a==0); cnt_s+=int(sc==0)
    lastzero+=int((g.RCYL.reindex(range(T-3,T))==0).any())
print(f"TEST wells: anchor RCYL==0: {cnt}/10, anchor SCTS==0: {cnt_s}/10, any zero in last 3 obs months: {lastzero}/10")
print("TEST target-month SCTS==0 rows:",int((te[te.RCYL.isna()].SCTS==0).sum()))
