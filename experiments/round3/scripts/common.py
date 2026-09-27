import os, sys, hashlib
from pathlib import Path
import pandas as pd, numpy as np
RAW = Path(os.path.expanduser("~/mnt/data"))
def read(p):
    for enc in ("utf-8-sig","gbk","gb18030"):
        try: return pd.read_csv(p, encoding=enc)
        except UnicodeDecodeError: pass
    raise RuntimeError("enc")
def role(cols):
    c=set(map(str,cols))
    if {"WELL_ID","NY","RCYL"}<=c: return "history"
    if "井号" in c: return "plan"
    if "XH" in c or "YCZMC" in c: return "layer"
    return "other"
def load():
    hist=[];layer=None;plan=None
    for p in sorted(RAW.rglob("*.csv")):
        f=read(p); r=role(f.columns)
        if r=="history":
            f["__split"]="test" if "test" in p.parent.name.lower() else "train"; hist.append(f)
        elif r=="layer": layer=f
        elif r=="plan": plan=f
    h=pd.concat(hist,ignore_index=True)
    h["__p"]=pd.to_datetime(h["NY"],errors="coerce").dt.to_period("M")
    h["WELL_ID"]=h["WELL_ID"].astype(str)
    return h,layer,plan
def code(v): return "C"+hashlib.sha256(str(v).encode()).hexdigest()[:4]
