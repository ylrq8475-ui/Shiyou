from exp import *
c=cfg(); tables=load_multisource_split(c,"train"); panel=build_training_samples(tables,c)
panel["WELL_ID"]=panel.WELL_ID.astype(str)
hist=tables.history.copy(); hist["WELL_ID"]=hist.WELL_ID.astype(str)
hist["o"]=pd.to_datetime(hist.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
ok={}
for w,g in panel.groupby("WELL_ID"):
    ao=pd.Timestamp(g.anchor_time.iloc[0]).to_period("M").ordinal
    hw=hist[hist.WELL_ID==w].set_index("o")
    sc=pd.to_numeric(hw.SCTS,errors="coerce").reindex(range(ao+1,ao+13))
    anc=pd.to_numeric(hw.RCYL,errors="coerce").get(ao,np.nan)
    last3=pd.to_numeric(hw.RCYL,errors="coerce").reindex(range(ao-2,ao+1))
    ok[w]=bool(anc>0 and (last3>0).all() and (sc>=20).all())
tl=[w for w,v in ok.items() if v]
print("test-like train wells:",len(tl),"/",len(ok))
def s(o,wells): 
    ws=well_scores(panel,o); return ws[ws.index.isin(wells)].mean()
base=np.load("oof_base.npy")
print(f"base: all={np.mean([well_scores(panel,o).mean() for o in base]):.2f}  test-like={np.mean([s(o,tl) for o in base]):.2f}  others={np.mean([s(o,set(ok)-set(tl)) for o in base]):.2f}")
import glob
for f in sorted(glob.glob("oof_*.npy")):
    if f=="oof_base.npy": continue
    o=np.load(f); n=len(o); b=base[:n]
    d_all=np.array([well_scores(panel,x).mean()-well_scores(panel,y).mean() for x,y in zip(o,b)])
    d_tl=np.array([s(x,tl)-s(y,tl) for x,y in zip(o,b)])
    print(f"{f[4:-4]:22s} n={n:2d}  diff all={d_all.mean():+.2f}  diff test-like={d_tl.mean():+.2f} (min {d_tl.min():+.2f} max {d_tl.max():+.2f})")
