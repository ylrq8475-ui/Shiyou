"""Append-only anonymous fit events; no global fit ceiling under R13."""
import json,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
from core import encode,require
class Ledger:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.value=json.loads(self.path.read_bytes()) if self.path.exists() else {'R13_fit_cap':None,'models_entered':0,'models_completed':0,'preprocessors_entered':0,'preprocessors_completed':0,'failures':0,'retries':0,'events':[]};self.save()
    def save(self):
        p=self.path.with_suffix('.writing');p.write_bytes(encode(self.value));p.replace(self.path)
    def run(self,kind,stage,fn):
        require(kind in ('model','preprocessor'),'FIT_KIND');require(not any(e['stage']==stage and e['event']==kind+'_entered' for e in self.value['events']),'FIT_STAGE_ALREADY_ENTERED')
        def event(name,**more):self.value['events'].append({'sequence':len(self.value['events'])+1,'time':datetime.now(timezone(timedelta(hours=8))).isoformat(),'stage':stage,'event':name,**more});self.save()
        self.value[kind+'s_entered']+=1;event(kind+'_entered');tick=time.perf_counter()
        try:answer=fn()
        except Exception as exc:self.value['failures']+=1;event(kind+'_failed',type=type(exc).__name__,seconds=time.perf_counter()-tick);raise
        self.value[kind+'s_completed']+=1;event(kind+'_completed',seconds=time.perf_counter()-tick);return answer
