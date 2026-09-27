from exp import *
from a2b import build
from fut2 import add_fut
from sklearn.ensemble import HistGradientBoostingRegressor, ExtraTreesRegressor
import json, time
t0=time.time(); use_fut=sys.argv[1]=="1"; kind=sys.argv[2]; ns=int(sys.argv[3])
c=cfg(); tables=load_multisource_split(c,"train"); bp=build_training_samples(tables,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
tl=json.load(open("tl.json"))
p=build(c,tables,False,False,True,base_panel=bp); p=add_fut(p,tables)
lvl=p["history__RCYL__last"].where(p["history__RCYL__last"]>0,1.0).fillna(1.0)
X=pd.DataFrame({"h":p.horizon,"log_lvl":np.log(lvl),
  "anc_ratio_prev":np.log1p(p.anc__ratio_prev),"anc_ratio_pre":np.log1p(p.anc__ratio_pre),"anc_SCTS":p.anc__SCTS,"anc_HS":p.anc__HS,
  "anc_run_len":p.anc__run_len,"trend6":p.history__RCYL__trend_6/lvl,"std12":p.history__RCYL__roll_12_std/lvl,
  "m3":np.log1p(p.history__RCYL__roll_3_mean/lvl),"m12":np.log1p(p.history__RCYL__roll_12_mean/lvl),
  "scts_last":p.history__SCTS__last,"hist_n":p.history_month_count})
if use_fut:
    for k in [c for c in p.columns if str(c).startswith(("futr__","futw__","futf__"))]: X[k]=p[k]
y=np.log1p(np.clip(bp.RCYL.values,0,None)/lvl.values)
A=np.load("m_A2B.npy")
splits=make_splits(bp.WELL_ID.to_numpy(),range(1,ns+1)); res=[]
for si,folds in enumerate(splits):
    oof=np.full(len(p),np.nan)
    for tr,va in folds:
        if kind=="hgb": m=HistGradientBoostingRegressor(max_iter=300,learning_rate=0.03,max_leaf_nodes=7,min_samples_leaf=30,l2_regularization=2.0,random_state=0)
        else: m=ExtraTreesRegressor(n_estimators=500,min_samples_leaf=10,max_features=0.5,n_jobs=-1,random_state=0)
        Xt=X.iloc[tr] if kind=="hgb" else X.iloc[tr].fillna(-999); Xv=X.iloc[va] if kind=="hgb" else X.iloc[va].fillna(-999)
        m.fit(Xt,y[tr]); oof[va]=np.clip(np.expm1(m.predict(Xv))*lvl.values[va],0,None)
    np.save(f"lean_oof_{si}.npy",oof)
    for w in (1.0,0.5,0.3):
        bl=np.exp(w*np.log(oof+1e-3)+(1-w)*np.log(A[si]+1e-3))-1e-3
        ws=well_scores(bp,np.clip(bl,0,None)); wa=well_scores(bp,A[si])
        res.append((w,ws.mean()-wa.mean(),ws.loc[tl].mean()-wa.loc[tl].mean(),ws.loc[tl].mean()))
R=pd.DataFrame(res,columns=["w","d_all","d_tl","tl"]).groupby("w").agg(["mean","min"]).round(2)
print(f"[lean fut={use_fut} {kind}] features={X.shape[1]}  {time.time()-t0:.0f}s"); print(R.to_string())
