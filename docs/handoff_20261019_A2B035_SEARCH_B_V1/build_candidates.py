"""Build <=3 private complete versions, with independent retrain/inference."""
import sys,subprocess,shutil,zipfile,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'source'));from core import *
FIRST=Path(sys.executable);SECOND=ROOT.parent/'A2B033_STEP2_20261019_v1/clean_venv/Scripts/python.exe'

ENTRY='''"""Complete version entry; the reviewed feature/model core is unchanged."""
from delivery_guard import prepare
if __name__=='__main__':
    prepare(OPERATION)
    from {module} import main
    main()
'''
GUARD='''"""CLI defaults, live runtime evidence and actual Codex scope enforcement."""
import sys,platform,importlib.metadata as im,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'source'))
from guard035 import *
def option(name,default):
    for i,v in enumerate(sys.argv):
        if v==name:return sys.argv[i+1]
        if v.startswith(name+'='):return v[len(name)+1:]
    sys.argv.extend([name,str(default)]);return str(default)
def prepare(operation):
    config=option('--config',ROOT/'variant.json');policy=option('--policy',ROOT/'runtime_policy.json')
    if operation=='predict':option('--model',ROOT/'models/model.joblib')
    verify_source_lock();c=load_variant(config);require_release(c);s=json.loads((HERE/'PIPELINE_APPROVAL.json').read_bytes())['allowed_scope']
    def check(m):require(m['learner']['name'] in ('ExtraTrees','MultiOutputExtraTrees') and m['features'] in s['features'] and m['target']['scale'] in s['target_scales'],'NOT_RELEASED_IN_THIS_PACKAGE')
    if c['learner']['name']=='Ensemble':
        require(c['fusion']['method'] in s['fusion_methods'],'FUSION_SCOPE')
        for m in c['fusion']['members']:check(m)
    else:check(c)
    versions={d.metadata['Name']:d.version for d in im.distributions()};locked=json.loads((HERE/'ENVIRONMENT_LOCK.json').read_bytes());require(platform.python_version()==locked['python_version'] and list(platform.python_build())==locked['python_build'] and versions==locked['dependencies'],'ACTUAL_ENVIRONMENT_DIFFERS')
    require(file_sha(policy)==json.loads((HERE/'DATA_CONTRACT.json').read_bytes())['private_policy_sha256'],'POLICY_CHANGED')
    evidence={'operation':operation,'actual_python':platform.python_version(),'actual_build':list(platform.python_build()),'actual_executable_sha256':file_sha(sys.executable),'actual_dependencies':dict(sorted(versions.items())),'config_sha256':file_sha(config),'pipeline_lock_sha256':file_sha(HERE/'PIPELINE_LOCK.json'),'before_fitting_or_inference':True}
    if '--output' in sys.argv:
        out=Path(sys.argv[sys.argv.index('--output')+1]);out.parent.mkdir(parents=True,exist_ok=True);Path(str(out)+'.runtime_before.json').write_bytes(encode(evidence))
'''

def run_cli(exe,args,cwd,stage,logdir):
    tick=time.perf_counter();p=subprocess.run([str(exe),'-B',*map(str,args)],cwd=cwd,capture_output=True)
    receipt={'stage':stage,'exit_code':p.returncode,'seconds':time.perf_counter()-tick,'stderr_lines':len(p.stderr.splitlines()),'stdout_lines':len(p.stdout.splitlines()),'arbitrary_diagnostics_not_public':True};(logdir/(stage+'.json')).write_bytes(encode(receipt))
    if p.returncode:
        (logdir/(stage+'.PRIVATE_STDERR.txt')).write_bytes(p.stderr);raise RuntimeError('CANDIDATE_CLI_FAILED_'+stage)
def read_values(path):
    keys=[];values=[]
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            for row in list(csv.DictReader(io.StringIO(z.read(info).decode('utf-8-sig')))):
                keys.append((row['WELL_ID'],row['NY']));values.append(float(row['RCYL']))
    return keys,np.asarray(values)
def pack_code(folder,dest):
    items=[]
    for f in sorted(folder.rglob('*')):
        if not f.is_file() or '__pycache__' in f.parts:continue
        rel=f.relative_to(folder).as_posix()
        if f.name.startswith('result.zip') or f.suffix=='.zip':continue
        require(f.suffix in ('.py','.json','.txt','.md','.joblib'),'UNEXPECTED_CODE_PACKAGE_TYPE');items.append((rel,f))
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,f in items:
            zi=zipfile.ZipInfo(n,date_time=(1980,1,1,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;z.writestr(zi,f.read_bytes())
    require(dest.stat().st_size<5_000_000_000,'CODE_PACKAGE_EXCEEDS_5GB')
    with zipfile.ZipFile(dest) as z:require(z.testzip() is None,'CODE_PACKAGE_CRC')
    return {'sha256':file_sha(dest),'bytes':dest.stat().st_size,'members':[{'path':n,'sha256':file_sha(f),'bytes':f.stat().st_size} for n,f in items],'CRC':'PASS','under5GB':True}
def main(a):
    global SECOND
    SECOND=Path(a.verification_python);require(SECOND.is_file(),'VERIFICATION_INTERPRETER_MISSING')
    summary_path=ROOT/'execution/RESULT_CANDIDATES.json';require(not summary_path.exists(),'CANDIDATES_ALREADY_COMPLETED');search=json.loads((ROOT/'execution/RESULT_DAILY_SEARCH.json').read_bytes());chosen=search['selected_for_local_packages'];require(1<=len(chosen)<=3,'DAILY_PACKAGE_LIMIT');records={r['variant']:r for r in search['records']};results=[]
    for ordinal,name in enumerate(chosen,1):
        row=records[name];base=ROOT/'candidates_private'/f'V{ordinal:02d}_{name}';require(not base.exists(),'SUCCESSFUL_VERSION_MUST_NOT_RETRAIN');base.mkdir();package=base/'package';package.mkdir();logs=base/'execution';logs.mkdir();shutil.copytree(ROOT/'source',package/'source',ignore=shutil.ignore_patterns('__pycache__'));(package/'runtime_policy.json').write_bytes((ROOT/'private/runtime_policy.json').read_bytes());(package/'variant.json').write_bytes(encode(row['config']));(package/'requirements.txt').write_bytes((ROOT/'source/requirements.txt').read_bytes());(package/'delivery_guard.py').write_text(GUARD,encoding='utf-8',newline='\n')
        for operation in ('train','predict'):(package/(operation+'.py')).write_text(ENTRY.replace('OPERATION',repr(operation)).format(module=operation),encoding='utf-8',newline='\n')
        # Import reviewed modules by distinct qualified path; root wrapper names
        # must not shadow source/train.py or source/predict.py.
        for operation in ('train','predict'):
            p=package/(operation+'.py');p.write_text(p.read_text().replace('from '+operation+' import main','from source.'+operation+' import main'),encoding='utf-8',newline='\n')
        info={'task':'A2B-035','role':'账户B执行与交付','version':name,'R13_commit':'ee2fa7a97530b57cc4a0aaa2a0bfd22530ed3937','Codex_pipeline_release':'3001037a7d465117fd8062e5cbc6b2d168575fef','config':row['config'],'fixed_OOF':row['results']['fixed']['score'],'repeated_mean':row['results']['repeated_summary']['mean'],'repeated_SE':row['results']['repeated_summary']['standard_error'],'selection':'2026-10-19 first daily internal search: repeated CV ranking plus prespecified OOF diversity; no platform score tuning','model_upgrade_or_final_designation':False,'external_models_or_geology_used':False,'historical_dtype':'UNKNOWN, inherited exception; no backfill'};(package/'VERSION_INFO.json').write_bytes(encode(info))
        learner=row['config']['learner']['name'];transform=row['config']['target'];readme=f'''# A2B-035 {name}：完整预测代码包

账户B执行与交付。本包是R13允许的完整平台候选版本；尚未上传平台，不是最终指定版本。共用管线已由Codex放行内部ET范围，最终包另审。

算法：{learner}。完整配置见variant.json，训练参数、目标/尺度、特征、切分及融合权重确定方式均由它与VERSION_INFO.json记录。81口完整训练井、972行；基础325列，base325_R另含R1–R5。全部特征、尺度和响应字段仅取同井NY<T0；M−1仅可作为融合成员。目标窗口不变，训练T0为末次事件段M之后首月，测试T0及原始输出键/日期继承冻结官方模板。窗口内所有动态字段不解码、不进入pandas或特征、尺度、筛选。

单模型目标为log1p(RCYL/s)，inverse=expm1乘s并裁剪非负；直接log1p时s=1。可选尺度与回退规则、R1–R5公式在source/guard035.py，缺月/零分母为NaN，原始尺度非有限/非正回退1。逐井输入特征保留现有lag/rolling/trend定义，无层位、方案、扩样、校准或外部模型。数值中位数填补、缺失指示、StandardScaler及分类编码仅在相应训练折/全量训练井拟合。

模型种子20260916。固定五折及种子1–5的5×5分井CV用于版本选择。指标逐井等权、epsilon1e−6、t从1起、2^-t不归一化。重复OOF均值{info['repeated_mean']:.14f}，描述性标准误{info['repeated_SE']:.14f}；同81井重复切分，不是独立数据重复。没有根据测试分布、标识、缺失模式或单井/月榜单反调结果。

如配置为Ensemble，equal为固定等权；inner_grid_0.1仅在训练侧内层五折OOF上选非负权重（和1，步长0.1），最终全量训练时重新只在训练井内确定，再拟合成员。没有对测试集拟合、校准或调整权重。推理逐井独立，预处理只transform，fit/fit_transform被守卫禁止。

## 环境

受检Windows Python3.13.7，完整构建和全部依赖见source/ENVIRONMENT_LOCK.json及requirements.txt。运行前会实时核对版本。使用该版本Python创建独立虚拟环境后，所有后续命令使用同一显式解释器：

```text
python -m venv .venv
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
```

Linux将下面及上面的`.venv\\Scripts\\python.exe`统一换为`.venv/bin/python`；跨操作系统二进制逐字节复现尚未签署。树内部n_jobs=-1，逐折顺序；BLAS/OpenMP1；预测顺序归约。

## 运行

从官方原始数据完整训练后推理，无需改代码、手工填数或交互操作：

```text
.venv\\Scripts\\python.exe train.py --config variant.json --data_dir "D:/official_data" --output "./trained"
.venv\\Scripts\\python.exe predict.py --config variant.json --data_dir "D:/official_data" --model "./trained/model.joblib" --output "./result.zip"
```

直接加载本包权重的一条命令：

```text
.venv\\Scripts\\python.exe predict.py --config variant.json --data_dir "D:/official_data" --output "./result.zip"
```

--data_dir为官方原始目录（原下发相对结构）或赛事原ZIP。--output训练时为未存在的新模型目录，推理时为未存在的result.zip。--config默认本包variant.json；--policy默认随包runtime_policy.json；--model默认models/model.joblib，可指定本次重训的对应模型。无需原工程或训练缓存；私有策略随本地正式包提供，旧路径文本不用于数据定位。不要覆盖已有模型或已成功输出。

## 文件

根train.py/predict.py是命令入口；delivery_guard.py补默认路径、实时环境探针及实际Codex范围检查；source/是字节不变的已审共用代码和冻结原方法模块；variant.json为本版完整参数；runtime_policy.json为本地私有数据角色与特征身份；models/model.joblib为训练成员与预处理器，models/MODEL_RECEIPT.json核对身份；VERSION_INFO.json记录研究选择来源。代码包不含原始CSV。私有配置、权重和result.zip不上GitHub。

输出ZIP根目录10个WELL_ID.csv，120行，严格WELL_ID、NY、RCYL三列。自动linter检查原模板键/日期/顺序、唯一性、有限非负、平铺结构及CRC。原始数据只读。模型保存为本轮独立候选，不替换旧模型。实际泄漏/错位/隔离/指标仍为硬门禁；事件语义按T4与版本化项目假设，不以分数证明官方规则。
''';(package/'README.md').write_text(readme,encoding='utf-8',newline='\n')
        prefiles={f.relative_to(package).as_posix():file_sha(f) for f in package.rglob('*') if f.is_file()};(logs/'PREFIT_PACKAGE_LOCK.json').write_bytes(encode({'source_files':prefiles,'data_archive_sha256':file_sha(a.data_dir),'environment_reference_sha256':file_sha(package/'source/ENVIRONMENT_LOCK.json'),'config_sha256':file_sha(package/'variant.json'),'before_full_fit':True}));print('BUILD_BEGIN '+name,flush=True)
        run_cli(FIRST,['train.py','--data_dir',a.data_dir,'--output',package/'models'],package,'FULL_TRAIN',logs)
        run_cli(FIRST,['predict.py','--data_dir',a.data_dir,'--output',package/'result.zip'],package,'PREDICT',logs)
        code=base/'submission_code.zip';manifest=pack_code(package,code);(logs/'CODE_PACKAGE_MANIFEST.json').write_bytes(encode(manifest));(base/'result.zip').write_bytes((package/'result.zip').read_bytes())
        clean=base/'independent_reproduction';clean.mkdir()
        with zipfile.ZipFile(code) as z:
            for n in z.namelist():require((clean/n).resolve().is_relative_to(clean.resolve()),'UNSAFE_SOURCE_ZIP_MEMBER')
            z.extractall(clean)
        run_cli(SECOND,['train.py','--data_dir',a.data_dir,'--output',clean/'from_scratch'],clean,'INDEPENDENT_FULL_TRAIN',logs)
        run_cli(SECOND,['predict.py','--data_dir',a.data_dir,'--model',clean/'from_scratch/model.joblib','--output',clean/'reproduced_result.zip'],clean,'INDEPENDENT_PREDICT',logs)
        k1,v1=read_values(base/'result.zip');k2,v2=read_values(clean/'reproduced_result.zip');require(k1==k2 and np.array_equal(v1,v2),'120_PREDICTIONS_NOT_IDENTICAL');require((base/'result.zip').read_bytes()==(clean/'reproduced_result.zip').read_bytes(),'RESULT_ZIP_BYTES_NOT_IDENTICAL');require(all(file_sha(package/n)==h for n,h in prefiles.items()),'PACKAGE_SOURCE_CHANGED_DURING_REPRODUCTION')
        firstcounts=json.loads((package/'models/FIT_COUNTS.json').read_bytes());secondcounts=json.loads((clean/'from_scratch/FIT_COUNTS.json').read_bytes());receipt={'version':name,'ordinal':ordinal,'configuration':row['config'],'CV':{'fixed':info['fixed_OOF'],'repeated_mean':info['repeated_mean'],'repeated_SE':info['repeated_SE']},'result_zip_sha256':file_sha(base/'result.zip'),'result_zip_bytes':(base/'result.zip').stat().st_size,'submission_code_zip_sha256':file_sha(code),'submission_code_zip_bytes':code.stat().st_size,'submission_code_member_count':len(manifest['members']),'code_CRC':'PASS','code_under5GB':True,'result_linter':json.loads((package/'result.zip.receipt.json').read_bytes())['lint'],'independent_retrain_120_values_identical':True,'independent_retrain_ZIP_original_bytes_identical':True,'independent_interpreter':'separate existing isolated Python3.13.7 with identical live dependencies; no shared system site-packages','new_environment_created_for_this_daily_batch':False,'primary_full_training_counts':{k:v for k,v in firstcounts.items() if k!='events'},'independent_full_training_counts':{k:v for k,v in secondcounts.items() if k!='events'},'private_models_not_replacing_old_models':True,'platform_upload_by_B':False,'final_designation_reviewed':False};(base/'DELIVERY_RECEIPT.json').write_bytes(encode(receipt));results.append(receipt);print('BUILD_COMPLETE '+name,flush=True)
    summary_path.write_bytes(encode({'task':'A2B-035/first daily complete candidate packages','role':'账户B执行与交付','versions':results,'count':len(results),'all_reproduced_exactly':True,'formal_platform_uploads_by_B':0,'final_package_review':'NOT_THIS_DAILY_BUILD'}));print('CANDIDATE_BUILD_COMPLETE',flush=True)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--data_dir',required=True);p.add_argument('--verification_python',required=True);main(p.parse_args())
