"""One frozen Chronos-Bolt model. Offline inference, anonymous IPC only.

The inference request and response contain arrays only in anonymous process pipes;
neither pipe is logged or persisted. No competition data is used by --probe.
"""
import argparse,hashlib,importlib.metadata,json,os,platform,socket,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_DATASETS_OFFLINE','HF_HUB_DISABLE_TELEMETRY','DO_NOT_TRACK'):os.environ[k]='1'
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(a):
    import torch
    from chronos import ChronosBoltPipeline
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(20260916)
    torch.use_deterministic_algorithms(True)
    def blocked(*args,**kwargs):raise RuntimeError('OFFLINE_NETWORK_BLOCKED')
    socket.socket.connect=blocked;socket.create_connection=blocked
    weights=Path(a.model_dir)/'model.safetensors';before=sha(weights)
    t=time.perf_counter()
    pipeline=ChronosBoltPipeline.from_pretrained(a.model_dir,device_map='cpu',torch_dtype=torch.float32,local_files_only=True)
    pipeline.model.eval()
    param_count=sum(p.numel() for p in pipeline.model.parameters())
    config=pipeline.model.config.chronos_config
    quantiles=config['quantiles'];median=quantiles.index(.5)
    assert config['context_length']==2048 and median==4
    if a.probe:
        contexts=[torch.tensor([1.,float('nan'),2.,3.]),torch.tensor([float('nan'),1.,1.])]
    else:
        request=json.loads(sys.stdin.buffer.read())
        assert request['protocol']=='A029_CONTEXT_ONLY_V1' and len(request['contexts'])==81
        contexts=[torch.tensor([float('nan') if v is None else v for v in values],dtype=torch.float32) for values in request['contexts']]
        assert all(0<len(c)<=512 and bool(torch.isfinite(c).any()) for c in contexts)
    def infer(contexts):
        answer=[]
        with torch.inference_mode():
            for start in range(0,len(contexts),16):
                output=pipeline.predict(inputs=contexts[start:start+16],prediction_length=13)
                assert output.shape==(len(contexts[start:start+16]),9,13)
                # Origin is M-1: generated steps 1..13 correspond to M..M+12.
                out=output[:,median,1:13].clamp(min=0)
                assert torch.isfinite(out).all()
                answer.extend(out.tolist())
        return answer
    pred=infer(contexts)
    assert sha(weights)==before and not pipeline.model.training
    meta={'model':'amazon/chronos-bolt-tiny','revision':'a0e552de83495b5c28c14c71c374f3e33280b340','weight_sha256':before,'parameters':param_count,'native_nan_smoke_passed':True,'finite_outputs':True,'forecast_request_steps':13,'discarded_bridge_steps':1,'target_steps':12,'context_limit':512,'batch_size':16,'dtype':'float32','device':'cpu','threads':1,'eval_mode':True,'inference_mode':True,'network_connect_blocked':True,'model_fits':0,'competition_training':False,'elapsed_seconds':time.perf_counter()-t}
    if a.probe:
        assert pred==infer(contexts),'NONDETERMINISTIC_SMOKE'
        meta.update(python=platform.python_version(),build=platform.python_build(),executable_sha256=sha(sys.executable),dependencies=dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())))
        import chronos
        package=Path(chronos.__file__).parent
        meta['chronos_source_sha256']={str(p.relative_to(package)).replace('\\','/'):sha(p) for p in sorted(package.rglob('*.py'))}
        Path(a.probe).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'probe_passed':True,'parameters':param_count,'nan_supported':True}))
    else:sys.stdout.write(json.dumps({'prediction':pred,'metadata':meta},allow_nan=False))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model-dir',required=True);parser.add_argument('--probe');a=parser.parse_args()
    try:main(a)
    except Exception as exc:
        # Do not print native exception messages that might contain input values.
        sys.stderr.write('FM_FAILURE_CLASS='+type(exc).__name__+'\n');sys.exit(2)
