"""README-only ZIP revision. Standard library only; zero ML entry points."""
import copy,difflib,hashlib,json,re,subprocess,zipfile
from pathlib import Path
R=Path(__file__).resolve().parent;OLD=R.parent/'A2B033_STEP2_20261019_v1';C=OLD/'publish_checkout'
PREFIX='docs/handoff_20261019_A2B033_R11_FIX01_B_V1';U=R/'upload'/PREFIX;D=R/'deliverables_private'
REVIEW='3ed4d57337b3805a3b40457ff66dc45c7ecde8e4';BASE='47077ee354a784bdf99444dd19adb7a8dac36d80'
def sha(x):return hashlib.sha256(x).hexdigest()
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
def save(name,x):(U/name).write_bytes(enc(x))
def protected():
    paths=[]
    for sub in ('package','execution','private','deliverables_private'):
        paths.extend(p for p in (OLD/sub).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.extend(p for p in (OLD/'clean_run').rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'synthetic_records' not in p.parts)
    return {p:sha(p.read_bytes()) for p in paths}
def main():
    assert not D.exists(),'FIX_ALREADY_CREATED_DO_NOT_OVERWRITE'
    U.mkdir(parents=True);D.mkdir()
    before=protected();oldzip=OLD/'deliverables_private/submission_code.zip';resultzip=OLD/'deliverables_private/result.zip'
    assert sha(oldzip.read_bytes())=='75943e9244606400d3addd218589069a51519fc2a69af96f8f4633c6f15e241f'
    assert sha(resultzip.read_bytes())=='9670e0d0bbea8e2720e53d032883f91900df65abe49b0da5c4642f755f3084de'
    with zipfile.ZipFile(oldzip) as z:
        assert z.testzip() is None
        infos=z.infolist();old={i.filename:z.read(i) for i in infos}
    readme=old['README.md'].decode('utf-8');assert (OLD/'package/README.md').read_bytes()==old['README.md']
    new=readme
    replacements=[('python train.py ','.venv\\Scripts\\python.exe train.py ',1),('python predict.py ','.venv\\Scripts\\python.exe predict.py ',2),('`python -m unittest -v test_033`','`.venv\\Scripts\\python.exe -m unittest -v test_033`',1)]
    counts=[]
    for original,revised,count in replacements:
        assert new.count(original)==count
        new=new.replace(original,revised);counts.append({'old':original,'new':revised,'occurrences':count})
    original_note='Linux等环境使用`.venv/bin/python`。精确复现验收在Windows Python 3.13.7进行；其他操作系统的二进制一致性未签署。'
    revised_note='首行`python -m venv .venv`仅用于创建环境，创建时使用Python 3.13.7；此后所有Windows命令均显式使用`.venv\\Scripts\\python.exe`，无需激活环境。Linux等环境将该解释器路径统一替换为`.venv/bin/python`。精确复现验收在Windows Python 3.13.7进行；其他操作系统的二进制一致性未签署。'
    assert new.count(original_note)==1;new=new.replace(original_note,revised_note)
    assert not re.search(r'(?m)^python (?:train|predict)\.py',new)
    assert '`python -m unittest' not in new
    # Strip only revised interpreter guidance to verify all other text unchanged.
    reverse=new.replace(revised_note,original_note)
    for original,revised,_ in replacements:reverse=reverse.replace(revised,original)
    assert reverse==readme,'README_SCOPE_CHANGED'
    newzip=D/'submission_code.zip'
    with zipfile.ZipFile(newzip,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for inf in infos:z.writestr(copy.copy(inf),new.encode('utf-8') if inf.filename=='README.md' else old[inf.filename])
    with zipfile.ZipFile(newzip) as z:
        assert z.testzip() is None and z.namelist()==[i.filename for i in infos]
        revised={i.filename:z.read(i) for i in z.infolist()}
    changed=[n for n in old if old[n]!=revised[n]];assert changed==['README.md']
    assert len(old)==25 and newzip.stat().st_size<5_000_000_000
    comparisons=[{'path':n,'old_sha256':sha(old[n]),'new_sha256':sha(revised[n]),'old_bytes':len(old[n]),'new_bytes':len(revised[n]),'unchanged':old[n]==revised[n]} for n in old]
    save('MEMBER_SHA256_COMPARISON.json',{'old_B_commit':BASE,'members':25,'same_member_order_and_names':True,'only_changed_member':'README.md','unchanged_members':24,'records':comparisons})
    manifest={'sha256':sha(newzip.read_bytes()),'bytes':newzip.stat().st_size,'members':25,'CRC':'PASS','less_than_5GB':True,'members_sha256':{n:sha(revised[n]) for n in revised},'contains_original_data':False}
    save('NEW_CODE_PACKAGE_MANIFEST.json',manifest)
    (U/'README.md').write_bytes(new.encode());(U/'README_PREVIOUS.md').write_bytes(old['README.md'])
    diff=''.join(difflib.unified_diff(readme.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='previous/README.md',tofile='FIX01/README.md'));(U/'README_ONLY.diff').write_bytes(diff.encode())
    save('README_COMMAND_CHECK.json',{'status':'PASS','static_only':True,'bootstrap':'python -m venv .venv (Python 3.13.7)','Windows_runtime_interpreter':'.venv\\Scripts\\python.exe','Linux_runtime_interpreter':'.venv/bin/python','pip_install_command_uses_same_venv':True,'train_commands':1,'predict_commands':2,'synthetic_command':1,'remaining_bare_train_predict_test_commands':0,'unchanged_arguments_and_outputs':True,'reverse_replacements_recover_exact_original_README':True,'replacements':counts,'runtime_training_or_prediction_executed':False,'new_model_fits':0,'new_preprocessor_fits':0})
    counts={'task':'A2B-033-R11-FIX-01','role':'账户B执行与交付','model_fits':0,'preprocessor_fits':0,'fit_entries':0,'fit_failures':0,'fit_retries':0,'inference_runs':0,'new_result_ZIPs':0,'training_entry_points_invoked':False,'verification':'build script uses stdlib ZIP/hash/text operations only; previous fit ledgers preserved byte-identical; no importing or loading ML models','prior_step2_model_fits':2,'prior_step2_preprocessor_pipeline_fits':2,'cumulative_A2B033_model_fits_unchanged':7,'cumulative_A2B033_preprocessor_pipeline_fits_unchanged':7};save('FIT_COUNTS.json',counts)
    preserve={'checked_existing_files':len(before),'all_existing_files_unchanged':all(p.exists() and sha(p.read_bytes())==h for p,h in before.items()),'old_code_ZIP_preserved':sha(oldzip.read_bytes())=='75943e9244606400d3addd218589069a51519fc2a69af96f8f4633c6f15e241f','result_ZIP_sha256':sha(resultzip.read_bytes()),'result_ZIP_bytes':resultzip.stat().st_size,'result_ZIP_unchanged':True,'model_member_unchanged':old['models/B0_prime.joblib']==revised['models/B0_prime.joblib'],'model_sha256':sha(old['models/B0_prime.joblib']),'private_policy_member_unchanged':old['runtime_policy.json']==revised['runtime_policy.json'],'private_policy_sha256':sha(old['runtime_policy.json']),'all_algorithm_source_members_unchanged':all(old[n]==revised[n] for n in old if n.endswith('.py')),'requirements_unchanged':old['requirements.txt']==revised['requirements.txt'],'old_fit_ledgers_unchanged':True,'old_frozen_sources_config_environment_not_modified':True};assert preserve['all_existing_files_unchanged'];save('PRESERVATION_CHECK.json',preserve)
    review_raw=subprocess.check_output(['git','show',REVIEW+':docs/handoff_20261019_A2B033_STEP2_CODEX_REVIEW_V1/RESULT_CODEX.json'],cwd=C);review=json.loads(review_raw);assert review['reviews_commit']==BASE and review['upload_approval_ready'] is False
    (U/'RECEIVED_REVIEW_CODEX.json').write_bytes(review_raw)
    save('SOURCE_RECEIPT.json',{'old_B_commit':BASE,'review_commit':REVIEW,'review_source_sha256':sha(review_raw),'R11_commit':'012e9fe50efac3f051b48804bc724e39b703cc93','user_authorization_source':'current user message, archived verbatim in AUTHORIZATION_FIX01.md','task_scope':'README interpreter chain only, zero fit, preserve old artifacts, no platform upload','task_approval_is_not_P1_closure':True})
    authorization='''# A2B-033-R11-FIX-01 用户授权原文

来源：本聊天当前用户消息（2026-10-19，Asia/Shanghai），用户直接授权；不是另造Claude指令存档。

> 批准执行 A2B-033-R11-FIX-01。
>
> 仅统一README中的虚拟环境解释器命令，保留旧包并另存新版代码包，更新成员清单、SHA256、隐私扫描及交付记录。
>
> 模型、result.zip、私有配置和算法源码必须保持不变；模型及预处理拟合次数均为0，不重训、不上传平台。
>
> 完成后发布固定提交并更新交付索引，交账户A2/Codex只读复核，不自行关闭P1或认定允许上传。
''';(U/'AUTHORIZATION_FIX01.md').write_bytes(authorization.encode())
    save('FIX_PLAN.json',{'task':'A2B-033-R11-FIX-01','only_change':'README explicit virtual environment interpreter for train, predict and synthetic commands, plus interpreter guidance','new_code_ZIP_separate_version_directory':True,'preserve_old_ZIP':True,'members_must_change':['README.md'],'all_other_24_members_must_be_identical':True,'models_and_preprocessors_fit_budget':0,'training_or_inference_commands_must_not_run':True,'no_platform_upload':True,'CODEX-033-S2-01':'P1 awaiting independent readonly recheck; B does not close','HIST-DTYPE':'P1 unchanged','do_not_claim_new_clean_training_reproduction':True})
    result={'task':'A2B-033-R11-FIX-01','role':'账户B执行与交付','status':'README_ONLY_FIX_READY_FOR_INDEPENDENT_READONLY_REVIEW','base_B_commit':BASE,'review_commit':REVIEW,'old_code_ZIP':{'sha256':sha(oldzip.read_bytes()),'bytes':oldzip.stat().st_size,'preserved':True},'new_code_ZIP':{'sha256':manifest['sha256'],'bytes':manifest['bytes'],'members':25,'less_than_5GB':True,'CRC':'PASS'},'changed_members':['README.md'],'unchanged_members':24,'model_sha256':preserve['model_sha256'],'model_unchanged':True,'result_ZIP':{'sha256':preserve['result_ZIP_sha256'],'bytes':preserve['result_ZIP_bytes'],'unchanged':True},'private_config_unchanged':True,'algorithm_source_unchanged':True,'requirements_unchanged':True,'model_fits':0,'preprocessor_fits':0,'new_inference_runs':0,'new_clean_training_reproduction':False,'inherited_original_clean_reproduction_120_rows_exact':True,'inherited_linter':'PASS; result.zip byte-identical; not rerun on real inputs for this documentation change','hard_gates_B':'Inherited original step2 source and independently reviewed evidence; no new model/data processing in FIX01','CODEX-033-S2-01':'P1 OPEN_PENDING_A2_CODEX_READONLY_RECHECK','HIST-DTYPE':'P1 UNKNOWN unchanged under prior exception','upload_approval_ready':False,'platform_uploads':0,'Codex_review':'PENDING','Codex_decision_row':'不适用'};save('RESULT_FIX01.json',result)
    (D/'SHA256SUMS.json').write_bytes(enc({'submission_code.zip':{'sha256':manifest['sha256'],'bytes':manifest['bytes']},'unchanged_result_zip':result['result_ZIP']}))
    (R/'README_NEW_SHA256.json').write_bytes(enc({'sha256':sha(new.encode()),'old_sha256':sha(old['README.md'])}))
    print(json.dumps({'only_changed_member':changed,'unchanged_members':24,'new_code_ZIP_sha256':manifest['sha256'],'new_code_ZIP_bytes':manifest['bytes'],'model_fits':0,'preprocessor_fits':0,'protected_existing_files':len(before)}))
if __name__=='__main__':main()
