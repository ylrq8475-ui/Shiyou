from common import *
h,layer,plan=load()
print("history cols:",list(h.columns))
print("layer cols:",None if layer is None else list(layer.columns), "rows",None if layer is None else len(layer))
print("plan cols:",None if plan is None else list(plan.columns),"rows",None if plan is None else len(plan))
for s,g in h.groupby("__split"):
    print(f"[{s}] wells={g.WELL_ID.nunique()} rows={len(g)} months/well median={g.groupby('WELL_ID').size().median()} range={g['__p'].min()}..{g['__p'].max()}")
    print("  dup well-month:",int(g.duplicated(['WELL_ID','__p']).sum()), " NY sample formats zero-padded share:", float(g.NY.astype(str).str.match(r'^\d{4}/\d{2}/\d{2}$').mean()))
    print("  missing share per col:", {c:round(float(g[c].isna().mean()),3) for c in g.columns if not c.startswith('__')})
cs=h["CSLB"].astype("string").str.strip()
vc=cs[cs.notna()&(cs!="")].value_counts()
print("CSLB distinct non-empty:",len(vc)," top counts:",[(code(k),int(v)) for k,v in vc.head(12).items()])
