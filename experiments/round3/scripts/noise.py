from exp import *
import json
c=cfg(); tables=load_multisource_split(c,"train"); bp=build_training_samples(tables,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
tl=json.load(open("tl.json"))
def pw(f): 
    o=np.load(f); return pd.concat([well_scores(bp,x) for x in o],axis=1).mean(axis=1)
A=pw("m_A2B.npy"); V=pw("m_V7.npy"); A=A[A.index.isin(tl)]; V=V[V.index.isin(tl)]
print(f"test-like wells n={len(A)}  A2B mean={A.mean():.2f} sd={A.std():.1f}   V7 mean={V.mean():.2f} sd={V.std():.1f}")
print(f"SE of a 10-well mean: A2B {A.std()/np.sqrt(10):.1f}  V7 {V.std()/np.sqrt(10):.1f};  paired diff V7-A2B per well: mean {(V-A).mean():+.2f} sd {(V-A).std():.1f} -> 10-well SE {(V-A).std()/np.sqrt(10):.1f}")
rng=np.random.default_rng(0); B=20000
ia=rng.integers(0,len(A),(B,10))
ma=A.values[ia].mean(1); mv=V.values[ia].mean(1); dd=mv-ma
print(f"bootstrap 10-well draws: A2B P(>=86)={np.mean(ma>=86):.3f} P(>=90)={np.mean(ma>=90):.3f} | 5-95% [{np.percentile(ma,5):.1f},{np.percentile(ma,95):.1f}]")
print(f"                         V7  P(>=86)={np.mean(mv>=86):.3f} P(>=90)={np.mean(mv>=90):.3f} | 5-95% [{np.percentile(mv,5):.1f},{np.percentile(mv,95):.1f}]")
print(f"P(V7 below A2B by >=5 on same 10 wells)={np.mean(dd<=-5):.3f};  P(V7 below A2B at all)={np.mean(dd<0):.3f}")
# conditional: draws where A2B>=86, what does V7 get?
sel=ma>=86
print(f"given A2B>=86 draws (n={sel.sum()}): V7 mean {mv[sel].mean():.1f}, P(V7>=90)={np.mean(mv[sel]>=90):.2f}")
# per-well score distribution
print("A2B per-well test-like quantiles:",A.quantile([.1,.25,.5,.75,.9]).round(1).to_dict())
