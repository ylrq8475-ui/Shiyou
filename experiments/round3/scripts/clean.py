from common import *
h,layer,plan=load()
N=["RCYL","RCYL1","HS","SCTS","YCYL","YCYL1","NCYL","LJCYL","HSYCYL","BJ","CC","CC1","PL","YY","TY"]
for k in N: h[k]=pd.to_numeric(h[k],errors="coerce")
h["days"]=h.__p.dt.days_in_month
h=h.sort_values(["WELL_ID","__p"]); h["o"]=h.__p.map(lambda p:p.ordinal)
obs=h[h.RCYL.notna()].copy()
def pct(m): return f"{int(m.sum())} ({m.mean()*100:.2f}%)"
print("== 1. 基本")
print(" observed well-months:",len(obs)," negative values:",{k:int((obs[k]<0).sum()) for k in N if (obs[k]<0).any()} or 0)
g=h.groupby("WELL_ID").o.agg(["min","max","count"]); print(" wells with missing months inside span:",int(((g["max"]-g["min"]+1)!=g["count"]).sum()),"/",len(g))
print("== 2. 定义一致性")
r=obs.YCYL/(obs.RCYL*obs.SCTS); r2=obs.YCYL/(obs.RCYL*obs.days)
m=(obs.RCYL>0)&(obs.SCTS>0)
print(" YCYL/(RCYL*SCTS) median",round(float(r[m].median()),3)," within ±5%:",round(float(((r[m]-1).abs()<0.05).mean()),3),"| YCYL/(RCYL*days) median",round(float(r2[m].median()),3)," within ±5%:",round(float(((r2[m]-1).abs()<0.05).mean()),3))
hs=obs.HS; print(" HS range:",float(hs.min()),"-",float(hs.max())," (unit %: share>1 =",round(float((hs>1).mean()),2),")")
calc=obs.RCYL1*(1-obs.HS/100); m2=(obs.RCYL1>0)&hs.notna()
rr=obs.RCYL/calc
print(" RCYL vs RCYL1*(1-HS%): median",round(float(rr[m2].median()),3)," within ±5%:",round(float(((rr[m2]-1).abs()<0.05).mean()),3)," >20% off:",pct(((rr[m2]-1).abs()>0.2)))
print(" RCYL > RCYL1 (oil>liquid):",pct(obs.RCYL>obs.RCYL1+1e-9))
print(" SCTS > days in month:",pct(obs.SCTS>obs.days+0.01),"| SCTS==0 & RCYL>0:",pct((obs.SCTS==0)&(obs.RCYL>0)),"| SCTS>=20 & RCYL==0:",pct((obs.SCTS>=20)&(obs.RCYL==0)))
lj=obs.groupby("WELL_ID").LJCYL.diff(); print(" LJCYL decreasing month-to-month:",pct(lj<-1e-6))
print("== 3. 异常跳变 (RCYL 相邻月比值)")
obs["prev"]=obs.groupby("WELL_ID").RCYL.shift(); obs["po"]=obs.groupby("WELL_ID").o.shift()
j=obs[(obs.po==obs.o-1)&(obs.prev>0)&(obs.RCYL>0)]; jr=np.log(j.RCYL/j.prev)
print(" |log ratio|>ln3 (x3 or /3):",pct(jr.abs()>np.log(3)),"  >ln10:",pct(jr.abs()>np.log(10)))
sp=j[(jr>np.log(3))]; 
# isolated spikes: up then down
obs["next"]=obs.groupby("WELL_ID").RCYL.shift(-1)
iso=(obs.RCYL>3*obs.prev)&(obs.RCYL>3*obs.next); print(" isolated one-month spikes (>3x both neighbours):",pct(iso.fillna(False)))
dip=(obs.RCYL<obs.prev/3)&(obs.RCYL<obs.next/3)&(obs.RCYL>0); print(" isolated one-month dips (<1/3 both neighbours):",pct(dip.fillna(False)))
print("== 4. 训练/测试对比 (观测月)")
for s,gg in obs.groupby("__split"):
    m=(gg.RCYL1>0)&gg.HS.notna(); rr=gg.RCYL/(gg.RCYL1*(1-gg.HS/100))
    print(f" {s}: oil/liquid-consistency within 5%={((rr[m]-1).abs()<0.05).mean():.3f}  RCYL median={gg.RCYL.median():.2f}  HS median={gg.HS.median():.1f}  SCTS median={gg.SCTS.median():.1f}  zero-RCYL share={(gg.RCYL==0).mean():.3f}")
