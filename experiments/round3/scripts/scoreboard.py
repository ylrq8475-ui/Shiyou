from exp import *
import json
c=cfg(); tables=load_multisource_split(c,"train"); bp=build_training_samples(tables,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
tl=json.load(open("tl.json"))
gm=lambda ws,arrs: np.exp(sum(w*np.log(a+1e-3) for w,a in zip(ws,arrs)))-1e-3
A=np.load("m_A2B.npy")[:2]; V=np.load("m_V7.npy")[:2]; T=np.load("ts_g1_all_hgb_w1.npy")[:2]; L=[np.load(f"lean_oof_{i}.npy") for i in range(2)]
M={"A2B-013":A,"S1":[gm((.7,.3),(a,t)) for a,t in zip(A,T)],"S3":[a*np.exp(-.15) for a in A],"S4":[gm((.5,.5),(a,l)) for a,l in zip(A,L)],"v7":V,
   "时序模型单独":T,"精简修正模型单独":L}
for k,P in M.items():
    s=[well_scores(bp,np.clip(p,0,None)) for p in P]
    print(f"{k}\tfixed5fold={s[0].mean():.2f}\tall81={np.mean([x.mean() for x in s]):.2f}\ttestlike47={np.mean([x.loc[tl].mean() for x in s]):.2f}\tfold_sd={np.std([well_scores(bp,P[0])[bp.WELL_ID.drop_duplicates().values].groupby(np.arange(81)%5).mean()]):.2f}")
