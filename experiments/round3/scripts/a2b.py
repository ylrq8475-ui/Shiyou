from exp import *
from oil_uplift.multistep import _history_features, _static_feature_map
import json, time
def tl_wells(panel, hist):
    out=[]
    for w,g in panel.groupby("WELL_ID"):
        ao=pd.Timestamp(g.anchor_time.iloc[0]).to_period("M").ordinal; hw=hist[hist.WELL_ID==w].set_index("o")
        rc=pd.to_numeric(hw.RCYL,errors="coerce"); sc=pd.to_numeric(hw.SCTS,errors="coerce").reindex(range(ao+1,ao+13))
        if rc.get(ao,np.nan)>0 and (rc.reindex(range(ao-2,ao+1))>0).all() and (sc>=20).all(): out.append(w)
    return out
def build(c, tables, anchor_obs=True, layer=True, anc_feats=False, split="train", base_panel=None):
    """Rebuild panel from base (anchors/targets identical); history cutoff controlled by anchor_obs."""
    hist=tables.history.copy(); hist["WELL_ID"]=hist.WELL_ID.astype(str)
    hist["o"]=pd.to_datetime(hist.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
    static={str(k):v for k,v in _static_feature_map(tables,c).items()} if layer else {}
    cands=c["anchors"]["eligible_event_values"]
    rows=[]
    for w,g in base_panel.groupby("WELL_ID",sort=False):
        at=pd.Timestamp(g.anchor_time.iloc[0]); ao=at.to_period("M").ordinal
        cut=at if anchor_obs else (at.to_period("M")-1).to_timestamp()
        f=_history_features(hist,w,cut,c); f.update(static.get(w,{}))
        if not anchor_obs: f["anchor_year"]=at.year; f["anchor_month"]=at.month
        if anc_feats:
            hw=hist[hist.WELL_ID==w].set_index("o").sort_index()
            rc=pd.to_numeric(hw.RCYL,errors="coerce"); sc=pd.to_numeric(hw.SCTS,errors="coerce")
            r=runs_of(hw.index[hw.CSLB.astype("string").str.strip().isin(cands).fillna(False).to_numpy()])
            s,e=r[-1] if r else (ao,ao)
            prev=rc.get(ao-1,np.nan); pre=rc.reindex(range(s-3,s)).mean()
            f.update({"anc__RCYL":rc.get(ao,np.nan),"anc__SCTS":sc.get(ao,np.nan),
                      "anc__ratio_prev":rc.get(ao,np.nan)/prev if prev and prev>0 else np.nan,
                      "anc__ratio_pre":rc.get(ao,np.nan)/pre if pre and pre>0 else np.nan,
                      "anc__run_len":e-s+1,"anc__start_ratio_pre":rc.get(s,np.nan)/pre if pre and pre>0 else np.nan})
            for col in ("RCYL1","HS","YY","TY"):
                f[f"anc__{col}"]=pd.to_numeric(hw[col],errors="coerce").get(ao,np.nan)
        for _,row in g.iterrows():
            d={"WELL_ID":w,"anchor_time":at,"horizon":row.horizon,"forecast_step":row.forecast_step,**f}
            if "RCYL" in g: d["RCYL"]=row.RCYL
            if "NY" in g: d["NY"]=row["NY"]
            rows.append(d)
    return pd.DataFrame(rows)
def feats_of(p):
    return [k for k in p.columns if (k in ("horizon","forecast_step","history_month_count") or str(k).startswith(("history__","layer__","anc__"))) and not p[k].isna().all()]
if __name__=="__main__":
    tag=sys.argv[1]; ao=sys.argv[2]=="1"; ly=sys.argv[3]=="1"; af=sys.argv[4]=="1"; ns=int(sys.argv[5])
    t0=time.time(); c=cfg(); tables=load_multisource_split(c,"train"); bp=build_training_samples(tables,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
    p=build(c,tables,ao,ly,af,base_panel=bp)
    assert (p.RCYL.values==bp.RCYL.values).all()
    feats=feats_of(p)
    oofs=cv(p,feats,c,make_splits(p.WELL_ID.to_numpy(),range(1,ns+1))); np.save(f"m_{tag}.npy",np.array(oofs))
    hist=tables.history.copy(); hist["WELL_ID"]=hist.WELL_ID.astype(str); hist["o"]=pd.to_datetime(hist.NY,errors="coerce").dt.to_period("M").map(lambda q:q.ordinal)
    tl=tl_wells(bp,hist); json.dump(tl,open("tl.json","w"))
    a=[well_scores(p,o) for o in oofs]
    print(f"[{tag}] anchor_obs={ao} layer={ly} anc_feats={af} feats={len(feats)} fixed={a[0].mean():.3f} all={np.mean([x.mean() for x in a]):.2f} test-like={np.mean([x[x.index.isin(tl)].mean() for x in a]):.2f} {time.time()-t0:.0f}s")
