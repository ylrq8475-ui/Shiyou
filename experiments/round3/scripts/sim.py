from exp import *
import json
c=cfg(); tr=load_multisource_split(c,"train"); te=load_multisource_split(c,"test")
bp=build_training_samples(tr,c); bp["WELL_ID"]=bp.WELL_ID.astype(str)
def prof(tables, anchors):
    h=tables.history.copy(); h["WELL_ID"]=h.WELL_ID.astype(str); h["o"]=pd.to_datetime(h.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
    for k in ["RCYL","HS","SCTS","RCYL1"]: h[k]=pd.to_numeric(h[k],errors="coerce")
    out={}
    for w,a in anchors.items():
        g=h[h.WELL_ID==w].set_index("o")
        pre=g.loc[a-3:a-1]
        out[w]=dict(lvl=np.log(pre.RCYL.mean()+1e-3),hs=pre.HS.mean(),liq=np.log(pre.RCYL1.mean()+1e-3),anc=np.log((g.RCYL.get(a,np.nan)+1e-3)/(g.RCYL.get(a-1,np.nan)+1e-3)))
    return pd.DataFrame(out).T
atr={w:pd.Timestamp(g.anchor_time.iloc[0]).to_period("M").ordinal for w,g in bp.groupby("WELL_ID")}
teh=te.history.copy(); teh["WELL_ID"]=teh.WELL_ID.astype(str); teh["o"]=pd.to_datetime(teh.NY,errors="coerce").dt.to_period("M").map(lambda p:p.ordinal)
ate={w:int(g[pd.to_numeric(g.RCYL,errors="coerce").isna()].o.min())-1 for w,g in teh.groupby("WELL_ID")}
P=prof(tr,atr); Q=prof(te,ate)
print("pre-anchor 3m profile (median)  train:",P.median().round(2).to_dict(),"\n                                 test :",Q.median().round(2).to_dict())
print("test wells' level percentile within train:",sorted([int((P.lvl<v).mean()*100) for v in Q.lvl]))
print("test wells' HS percentile within train   :",sorted([int((P.hs<v).mean()*100) for v in Q.hs]))
# nearest-neighbour matched validation set: for each test well, 5 nearest train wells in (lvl, hs) standardized
Z=P[["lvl","hs"]]; mu,sd=Z.mean(),Z.std(); Zs=(Z-mu)/sd; Qs=(Q[["lvl","hs"]]-mu)/sd
wts=pd.Series(0.0,index=P.index)
for _,q in Qs.iterrows():
    d=((Zs-q)**2).sum(1).pow(.5).nsmallest(5); wts[d.index]+=1
matched=wts[wts>0]; print("matched train wells:",len(matched))
gm=lambda ws,arrs: np.exp(sum(w*np.log(a+1e-3) for w,a in zip(ws,arrs)))-1e-3
A=np.load("m_A2B.npy")[:2]; V=np.load("m_V7.npy")[:2]; T=np.load("ts_g1_all_hgb_w1.npy")[:2]; L=[np.load(f"lean_oof_{i}.npy") for i in range(2)]
subs={"A2B":A,"S1":[gm((.7,.3),(a,t)) for a,t in zip(A,T)],"S3":[a*np.exp(-.15) for a in A],"S4":[gm((.5,.5),(a,l)) for a,l in zip(A,L)],"v7":V}
tl=json.load(open("tl.json"))
print(f"\n{'':6s} {'all81':>7s} {'test-like47':>12s} {'matched(wtd)':>13s}   platform")
plat={"A2B":86,"S1":84,"S3":83,"S4":82,"v7":80.54}
for k,Pp in subs.items():
    ws=pd.concat([well_scores(bp,np.clip(p,0,None)) for p in Pp],axis=1).mean(1)
    print(f"{k:6s} {ws.mean():7.2f} {ws.loc[tl].mean():12.2f} {np.average(ws.loc[matched.index],weights=matched):13.2f}   {plat[k]}")
