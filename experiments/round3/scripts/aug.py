from exp import *
from oil_uplift.multistep import _history_features, _static_feature_map
from oil_uplift.training import _model_pipeline, _fit_pipeline
import time; t=time.time()
mode=sys.argv[1]  # clean | all
nseeds=int(sys.argv[2])
c=cfg(); tables=load_multisource_split(c,"train"); base=build_training_samples(tables,c)
base["WELL_ID"]=base.WELL_ID.astype(str); base["is_last"]=1
hist=tables.history.copy(); hist["WELL_ID"]=hist.WELL_ID.astype(str)
hist["o"]=pd.to_datetime(hist.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
cands=c["anchors"]["eligible_event_values"]; static=_static_feature_map(tables,c)
static={str(k):v for k,v in static.items()}
rows=[]; n_contam=0
for w,g in hist.groupby("WELL_ID"):
    if w not in set(base.WELL_ID): continue
    g=g.set_index("o").sort_index()
    r=runs_of(g.index[g.CSLB.astype("string").str.strip().isin(cands).fillna(False).to_numpy()])
    for i,(s,e) in enumerate(r[:-1]):
        tgt=pd.to_numeric(g.RCYL,errors="coerce").reindex(range(e+1,e+13))
        if tgt.isna().any(): continue
        contam = r[i+1][0] <= e+12
        if contam and mode=="clean": continue
        n_contam+=contam
        at=pd.Period(ordinal=e,freq="M").to_timestamp()
        b=_history_features(tables.history.assign(WELL_ID=tables.history.WELL_ID.astype(str)),w,at,c); b.update(static.get(w,{}))
        for hh in range(1,13):
            rows.append({"WELL_ID":w,"anchor_time":at,"horizon":hh,"forecast_step":hh,"RCYL":float(tgt.iloc[hh-1]),"is_last":0,**b})
aug=pd.DataFrame(rows)
panel=pd.concat([base,aug],ignore_index=True)
print(f"mode={mode} extra events={len(aug)//12} (contaminated kept {n_contam}) total samples={panel.shape[0]//12}")
feats=configured_feature_columns(panel,c)
last_idx=np.where(panel.is_last==1)[0]
# splits by well, evaluated on last-event rows only; same well->fold map as base splits
bs=make_splits(base.WELL_ID.to_numpy(),range(1,nseeds+1))
wells=panel.WELL_ID.to_numpy()
x=panel.loc[:,feats]; y=panel.RCYL; scores=[]
baseo=np.load("oof_base.npy")[:len(bs)]; allo=[]
for folds,bo in zip(bs,baseo):
    oof=np.full(len(base),np.nan)
    for tr,va in folds:
        trw=set(base.WELL_ID.iloc[tr]); tri=np.where(np.isin(wells,list(trw)))[0]
        est=_model_pipeline(NAME,x.iloc[tri],c)
        _fit_pipeline(est,NAME,x.iloc[tri],y.iloc[tri],panel.horizon.iloc[tri],panel.iloc[tri])
        oof[va]=np.clip(predict_pipeline_output(est,NAME,x.iloc[va],panel.iloc[va]),0,None)
    allo.append(oof); scores.append((well_scores(base,oof).mean(),well_scores(base,bo).mean()))
    if len(scores)==1:
        wd=well_scores(base,oof)-well_scores(base,bo)
s=np.array(scores); d=s[:,0]-s[:,1]

print(f"aug fixed={s[0,0]:.3f} (base {s[0,1]:.3f}) repeated={s[:,0].mean():.3f} (base {s[:,1].mean():.3f}) diff={d.mean():+.3f} min/max={d.min():+.2f}/{d.max():+.2f}")
print(f"per-well fixed: improved {int((wd>0.5).sum())} worse {int((wd<-0.5).sum())}; gain excl top-2 {(wd.sum()-wd.nlargest(2).sum())/len(wd):+.3f}; secs {time.time()-t:.0f}")
np.save(f"oof_aug_{mode}.npy",np.array(allo))
