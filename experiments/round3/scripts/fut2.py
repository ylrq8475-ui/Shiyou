from exp import *
from a2b import build, feats_of
import json, time
FC=["SCTS","YY","TY","BJ","CC","CC1","PL"]
def add_fut(panel, tables):
    h=tables.history.copy(); h["WELL_ID"]=h.WELL_ID.astype(str); h["o"]=pd.to_datetime(h.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
    for k in FC: h[k]=pd.to_numeric(h[k],errors="coerce")
    h["DISP"]=h.BJ**2*h.CC*h.CC1
    idx=h.set_index(["WELL_ID","o"])
    out=[]
    for w,at,hh in zip(panel.WELL_ID,panel.anchor_time,panel.horizon):
        a=pd.Timestamp(at).to_period("M").ordinal; d={}
        b=idx.loc[(w,a-1)] if (w,a-1) in idx.index else None; r=idx.loc[(w,a+int(hh))] if (w,a+int(hh)) in idx.index else None
        for k in FC+["DISP"]:
            rv=r[k] if r is not None else np.nan; bv=b[k] if b is not None else np.nan
            d[f"futr__{k}"]=np.log((rv+1e-3)/(bv+1e-3)) if pd.notna(rv) and pd.notna(bv) and rv>0 and bv>0 else np.nan
            d[f"futv__{k}"]=rv
        for fld in ("BZ","CSLB"):
            v=r[fld] if r is not None else np.nan
            d[f"futf__{fld}"]=0 if (pd.isna(v) or str(v).strip()=="") else 1
            if fld=="BZ": d["futf__BZ_len"]=0 if d["futf__BZ"]==0 else len(str(v))
        out.append(d)
    f=pd.DataFrame(out,index=panel.index)
    for k in ["BZ","CSLB"]:
        f[f"futw__n{k}"]=f.groupby(panel.WELL_ID.values)[f"futf__{k}"].transform(lambda s:s.iloc[:3].sum())
    for k in ["SCTS","YY","TY","DISP"]:
        f[f"futw__{k}"]=f.groupby(panel.WELL_ID.values)[f"futr__{k}"].transform(lambda s:s.iloc[:3].mean())
    return pd.concat([panel,f],axis=1)
if __name__=="__main__":
    tag=sys.argv[1]; kinds=sys.argv[2].split(","); ns=int(sys.argv[3]); t0=time.time()
    c=cfg(); tables=load_multisource_split(c,"train"); bp=build_training_samples(tables,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
    p=build(c,tables,False,False,False,base_panel=bp); p=add_fut(p,tables)
    feats=feats_of(p)+[k for k in p.columns if str(k).startswith(tuple(kinds))]
    oofs=cv(p,feats,c,make_splits(p.WELL_ID.to_numpy(),range(1,ns+1))); np.save(f"f_{tag}.npy",np.array(oofs))
    tl=json.load(open("tl.json")); A=np.load("m_A2B.npy")[:len(oofs)]
    s=[well_scores(p,o) for o in oofs]; sa=[well_scores(p,o) for o in A]
    print(f"[{tag}] feats={len(feats)} all={np.mean([x.mean() for x in s]):.2f} (A2B {np.mean([x.mean() for x in sa]):.2f}) test-like={np.mean([x.loc[tl].mean() for x in s]):.2f} (A2B {np.mean([x.loc[tl].mean() for x in sa]):.2f}) {time.time()-t0:.0f}s")
