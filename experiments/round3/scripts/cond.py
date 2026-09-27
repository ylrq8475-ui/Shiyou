from exp import *
import json
c=cfg(); tables=load_multisource_split(c,"train"); bp=build_training_samples(tables,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
tl=json.load(open("tl.json"))
A=np.load("m_A2B.npy")[:2]; V=np.load("m_V7.npy")[:2]; T=np.load("ts_g1_all_hgb_w1.npy")[:2]
gm=lambda ws,arrs: np.exp(sum(w*np.log(a+1e-3) for w,a in zip(ws,arrs)))-1e-3
def pw(P): return pd.concat([well_scores(bp,np.clip(p,0,None)) for p in P],axis=1).mean(1).loc[tl]
cands={"A2B":A,"V7":V,"S1 (A2B.7*TS.3)":[gm((.7,.3),(a,t)) for a,t in zip(A,T)],"S3 (A2B x0.86)":[a*np.exp(-.15) for a in A],"S2 (A2B.5*V7.5)":[gm((.5,.5),(a,v)) for a,v in zip(A,V)]}
S={k:pw(v) for k,v in cands.items()}
rng=np.random.default_rng(1); idx=rng.integers(0,len(tl),(200000,10))
M={k:v.values[idx].mean(1) for k,v in S.items()}
sel=M["A2B"]>=86
print(f"local test-like means: "+", ".join(f"{k}={v.mean():.2f}" for k,v in S.items()))
print(f"draws with A2B>=86: {sel.sum()}  (P={sel.mean():.4f})")
for k in cands:
    if k=="A2B": continue
    d=M[k][sel]-M["A2B"][sel]
    print(f"  {k:18s} given A2B>=86: mean diff {d.mean():+.2f}, P(diff<=observed-ish)", end="")
    obs={"V7":-5.5,"S1 (A2B.7*TS.3)":-2.0,"S3 (A2B x0.86)":-3.0,"S2 (A2B.5*V7.5)":-3.0}[k]
    print(f" P(diff<={obs})={np.mean(d<=obs):.2f}  P(diff>=+4, i.e. reach 90)={np.mean(d>=4):.3f}")
print("paired per-well diff SD vs A2B -> 10-well SE:",{k:round(float((S[k]-S['A2B']).std()/np.sqrt(10)),2) for k in cands if k!='A2B'})
