"""Prepare a new reproducible workspace from the anonymous flat delivery.

Default is synthetic checks only. --execute-authorized-review explicitly runs
the 20-fit protocol; never use this flag without separate review authorization.
"""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
def main(a):
    here=Path(__file__).resolve().parent;other=Path(a.diagnostics_directory);work=Path(a.workspace)
    if work.exists():raise RuntimeError('NEW_WORKSPACE_REQUIRED_NO_REFIT')
    b=work/'B028029';d=work/'B030';(b/'received').mkdir(parents=True);(d/'received').mkdir(parents=True)
    for source,dest in [(here,b),(other,d)]:
        for p in source.iterdir():
            if p.is_file():shutil.copyfile(p,dest/p.name)
    for original,name in [('SOURCE_RECEIPT_A027.json','A027_SOURCE_RECEIPT.json'),('CLAUDE_INSTRUCTION_ORIGINAL_R5.md','INSTRUCTION_ORIGINAL_R5.md'),('REFERENCE_PANEL_CONTRACT.json','REFERENCE_PANEL_CONTRACT.json'),('SPLIT_REFERENCE.json','SPLIT_REFERENCE.json'),('PREREG_PARAMETERS.json','PREREG_PARAMETERS.json')]:shutil.copyfile(here/original,b/'received'/name)
    shutil.copyfile(other/'CLAUDE_INSTRUCTION_ORIGINAL_R6.md',d/'received/INSTRUCTION_ORIGINAL_R6.md')
    for p in [b/'test_experiment.py',d/'test_030.py']:
        out=subprocess.run([sys.executable,'-I',str(p)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if out.returncode:raise RuntimeError('SYNTHETIC_FAILED')
    if not a.execute_authorized_review:
        print(json.dumps({'workspace_prepared':True,'synthetic_passed':True,'model_fits':0,'preprocessor_fits':0}));return
    if not all([a.project_src,a.config,a.archive,a.manifest,a.fm_python,a.fm_model]):raise RuntimeError('AUTHORIZED_LOCAL_INPUT_ARGUMENTS_REQUIRED')
    command=[sys.executable,'-I',str(b/'run_experiment.py'),'--authorized','--project-src',a.project_src,'--config',a.config,'--archive',a.archive,'--manifest',a.manifest,'--output',str(work/'execution_028029'),'--fm-python',a.fm_python,'--fm-model',a.fm_model,'--diagnostics-src',str(d),'--diagnostics-output',str(work/'execution_030')]
    sys.exit(subprocess.call(command))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--diagnostics-directory',required=True);p.add_argument('--execute-authorized-review',action='store_true')
    for name in ('project-src','config','archive','manifest','fm-python','fm-model'):p.add_argument('--'+name)
    main(p.parse_args())
