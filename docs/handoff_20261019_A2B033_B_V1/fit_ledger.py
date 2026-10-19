"""Shared process-safe sequential ledger. One failed fit stops all stages."""
import json,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
from core import encode,require,training,safe,np
def now():return datetime.now(timezone(timedelta(hours=8))).isoformat()
class Ledger:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists():self.value=json.loads(self.path.read_bytes())
        else:self.value={'max_models':7,'max_preprocessors':7,'models_entered':0,'models_completed':0,'preprocessors_entered':0,'preprocessors_completed':0,'failures':0,'retries':0,'events':[]};self.save()
        require(not self.value['failures'],'PREVIOUS_FIT_FAILED_NO_RETRY')
    def save(self):
        temporary=self.path.with_suffix('.writing');temporary.write_bytes(encode(self.value));temporary.replace(self.path)
    def event(self,kind,stage,**data):
        self.value['events'].append({'sequence':len(self.value['events'])+1,'time':now(),'event':kind,'stage':stage,**data});self.save()
    def run(self,kind,stage,fn):
        v=self.value;require(not v['failures'],'FIT_AFTER_FAILURE_FORBIDDEN');key=kind+'s';require(v[key+'_entered']<v['max_'+key],'FIT_BUDGET');require(not any(x['stage']==stage and x['event']==kind+'_entered' for x in v['events']),'FIT_STAGE_ALREADY_ENTERED_NO_REFIT')
        v[key+'_entered']+=1;self.event(kind+'_entered',stage);tick=time.perf_counter()
        try:answer=fn()
        except Exception as exc:v['failures']+=1;self.event(kind+'_failed',stage,exception_type=type(exc).__name__,seconds=time.perf_counter()-tick);raise
        v[key+'_completed']+=1;self.event(kind+'_completed',stage,seconds=time.perf_counter()-tick);return answer
def fit_once(panel,features,config,ledger,stage):
    x=panel[features];pipe=training._model_pipeline(safe.MODEL_NAME,x,config);prep=pipe.named_steps['preprocess'];model=pipe.named_steps['model'];p=model.get_params();require(p['n_estimators']==400 and p['min_samples_leaf']==6 and p['max_features']==.75 and p['random_state']==20260916 and p['n_jobs']==-1,'MODEL_PARAMETERS')
    raw=panel['history__RCYL__last'].to_numpy(float);scale=np.where(np.isfinite(raw)&(raw>0),raw,1.);z=training._transform_target(panel.RCYL,panel,'log_ratio_last');require(np.array_equal(z,np.log1p(panel.RCYL.to_numpy(float)/scale)),'TARGET_TRANSFORM')
    xx=ledger.run('preprocessor',stage,lambda:prep.fit_transform(x,z));ledger.run('model',stage,lambda:model.fit(xx,z));return pipe
