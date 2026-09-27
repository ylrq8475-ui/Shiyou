from exp import *
from a2b import build
from fut2 import add_fut
import json
c=cfg(); tables=load_multisource_split(c,"train"); bp=build_training_samples(tables,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
tl=set(json.load(open("tl.json")))
p=build(c,tables,False,False,True,base_panel=bp); p=add_fut(p,tables)
P=np.load("m_A2B.npy").mean(0)
d=p.copy(); d["pred"]=P; d["y"]=bp.RCYL.values
d["term"]=np.abs(d.pred-d.y)/(d.pred+d.y+1e-6); d["w"]=0.5**d.horizon; d["loss"]=d.w*d.term
d["r"]=np.log((d.pred+0.01)/(d.y+0.01)); d["tl"]=d.WELL_ID.isin(tl)
T=d[d.tl]
tot=T.loss.sum()
print("== TEST-LIKE A2B OOF: where is the loss")
print(" by horizon share:",(T.groupby("horizon").loss.sum()/tot).round(3).to_dict())
wl=T.groupby("WELL_ID").loss.sum().sort_values(ascending=False)
print(" worst 5 wells share:",round(wl.head(5).sum()/tot,3)," worst 10:",round(wl.head(10).sum()/tot,3))
h13=T[T.horizon<=3]
print(" h1-3: over-predicted share",round(float((h13.r>0).mean()),2)," median r",round(float(h13.r.median()),3)," median|r|",round(float(h13.r.abs().median()),3))
# error is mostly level (well-constant) or shape?
wm=T.groupby("WELL_ID").r.transform("mean")
print(" variance of r: between-well (level) share",round(float(wm.var()/T.r.var()),2))
# which signals explain residual? spearman on h<=3 rows, test-like and all
cand=[k for k in d.columns if str(k).startswith(("futr__","futw__","anc__"))]+["history__RCYL__last","history__RCYL__trend_6","history__HS__last" if "history__HS__last" in d else "history__SCTS__last","history__RCYL__roll_12_std","history_month_count"]
res=[]
for k in cand:
    for nm,S in (("tl",T[T.horizon<=3]),("all",d[d.horizon<=3])):
        s=S[[k,"r"]].dropna()
        if len(s)>30: res.append((k,nm,s[k].rank().corr(s.r.rank()),len(s)))
R=pd.DataFrame(res,columns=["feat","set","spearman","n"]).pivot(index="feat",columns="set",values="spearman")
print("\n== residual r=log(pred/truth), h1-3: spearman with signals (|rho| sorted, test-like)")
print(R.reindex(R["tl"].abs().sort_values(ascending=False).index).round(2).head(15).to_string())
