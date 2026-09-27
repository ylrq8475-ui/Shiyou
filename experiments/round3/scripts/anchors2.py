from common import *
import hashlib
h,layer,plan=load()
cs=h["CSLB"].astype("string").str.strip()
vals=sorted(set(v for v in cs.dropna() if v), key=lambda v: hashlib.sha256(v.encode()).hexdigest())
codefor={v:f"CSLB_{i:03d}" for i,v in enumerate(vals,1)}
cand=[v for v,c in codefor.items() if c in ("CSLB_012","CSLB_032")]
h["ev"]=cs.isin(cand); h["o"]=h.__p.map(lambda p:p.ordinal)
h["evcode"]=cs.astype(object).where(h["ev"]).map(lambda v: codefor.get(v) if isinstance(v,str) else None)
def runs(g):
    m=sorted(set(g.index[g.ev.astype(bool)])); out=[]
    for x in m:
        if out and x==out[-1][1]+1: out[-1][1]=x
        else: out.append([x,x])
    return out
plan=plan.copy(); plan["w"]=plan["井号"].astype(str)
plan["po"]=pd.to_datetime(plan["完工日期"],errors="coerce").dt.to_period("M").map(lambda p:p.ordinal if pd.notna(p) else None)
pw=plan.groupby("w").po.apply(list).to_dict()
print("plan: wells",plan.w.nunique(),"rows/well",plan.groupby('w').size().describe()[['min','50%','max']].to_dict())
allw=set(h.WELL_ID); tw=set(h[h.__split=="test"].WELL_ID)
print("plan coverage train/test wells:",len((allw-tw)&set(pw)),"/",len(allw-tw)," ",len(tw&set(pw)),"/",len(tw))
print("layer coverage train/test:",len((allw-tw)&set(layer.WELL_ID.astype(str))),len(tw&set(layer.WELL_ID.astype(str))), " layer rows/well median",layer.groupby('WELL_ID').size().median())
# multi-month runs profile + plan alignment
stat=[];align=[]
for (w,sp),g in h.groupby(["WELL_ID","__split"]):
    g=g.set_index("o").sort_index()
    for s,e in runs(g):
        pos=[p for p in pw.get(w,[]) if p is not None]
        d=[p-e for p in pos]; ds=[p-s for p in pos]
        align.append(dict(split=sp,len=e-s+1,plan_in_run=any(s<=p<=e for p in pos),
             plan_eq_start=any(p==s for p in pos),plan_eq_end=any(p==e for p in pos),
             plan_within2=any(abs(x)<=2 for x in d), codes="+".join(sorted(set(g.loc[s:e].evcode.dropna())))))
        if e>s:
            pre=g.RCYL.reindex(range(s-3,s)).mean()
            stat.append(dict(scts_s=g.SCTS.get(s),scts_e=g.SCTS.get(e),r_s=g.RCYL.get(s,np.nan)/pre if pre else np.nan,r_e=g.RCYL.get(e,np.nan)/pre if pre else np.nan,r_e1=g.RCYL.get(e+1,np.nan)/pre if pre else np.nan))
st=pd.DataFrame(stat); print("\nmulti-month runs n=",len(st)); print(st.median().round(2).to_dict())
print("share start-month SCTS<28:",round(float((st.scts_s<28).mean()),2)," end-month SCTS<28:",round(float((st.scts_e<28).mean()),2), " both:",round(float(((st.scts_s<28)&(st.scts_e<28)).mean()),2))
a=pd.DataFrame(align)
print("\nplan alignment by run length/split:"); print(a.groupby(["split","len"])[["plan_in_run","plan_eq_start","plan_eq_end","plan_within2"]].mean().round(2).assign(n=a.groupby(["split","len"]).size()).to_string())
print("\ncode combos per run:",a.codes.value_counts().to_dict())
# single-month runs SCTS
