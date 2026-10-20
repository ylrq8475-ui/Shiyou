"""Read official public model metadata/licenses only. Never fetch weights/data."""
import urllib.request,json,hashlib,concurrent.futures
from pathlib import Path
R=Path(__file__).resolve().parent
URLs={
 'tab_license':'https://huggingface.co/Prior-Labs/TabPFN-v2-reg/raw/4972a65a1b30806315c6f92499959ffbfc69a673/LICENSE.txt',
 'tab_tree':'https://huggingface.co/api/models/Prior-Labs/TabPFN-v2-reg/tree/4972a65a1b30806315c6f92499959ffbfc69a673?recursive=false',
 'chronos_tree':'https://huggingface.co/api/models/amazon/chronos-2/tree/29ec3766d36d6f73f0696f85560a422f50e8498c?recursive=false',
 'chronos_readme':'https://huggingface.co/amazon/chronos-2/raw/29ec3766d36d6f73f0696f85560a422f50e8498c/README.md',
 'chronos_license':'https://raw.githubusercontent.com/amazon-science/chronos-forecasting/main/LICENSE',
 'lgb_license':'https://raw.githubusercontent.com/microsoft/LightGBM/v4.6.0/LICENSE',
 'cat_license':'https://raw.githubusercontent.com/catboost/catboost/v1.2.8/LICENSE'
}
def one(k,url):
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Account-A2-public-license-audit'})
  with urllib.request.urlopen(req,timeout=25) as f:b=f.read(200001)
  assert len(b)<=200000
  text=b.decode('utf-8');p=R/'public_metadata'/ (k+'.txt');p.parent.mkdir(exist_ok=True);p.write_bytes(b)
  out={'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'status':'FETCHED'}
  if k.endswith('_tree'):out['lfs_files']=[{'path':v['path'],'lfs':v.get('lfs'),'size':v.get('size')} for v in json.loads(text) if v.get('lfs')]
  return k,out
 except Exception as e:return k,{'url':url,'status':'UNAVAILABLE','error_type':type(e).__name__,'message':str(e)}
out=dict(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(lambda kv:one(*kv),URLs.items()))
(R/'OFFICIAL_METADATA_CHECK.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
