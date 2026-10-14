"""Bind completed readonly evidence into one finite-scope decision JSON."""
import ast, hashlib, importlib.metadata, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'sources/B'))
import route_b_core as core
records=json.loads((ROOT/'RECORD_AUDIT_CODEX.json').read_bytes())
tests=json.loads((ROOT/'SYNTHETIC_REVIEW_CODEX.json').read_bytes())
modules=json.loads((ROOT/'PUBLIC_MODULE_IDENTITY_CODEX.json').read_bytes())
result=json.loads((ROOT/'sources/B/RESULT_B2.json').read_bytes())
params=json.loads((ROOT/'sources/B/PREREG_PARAMETERS.json').read_bytes())
instruction=(ROOT/'sources/Claude/INSTRUCTION_ORIGINAL.md').read_text(encoding='utf-8')
if not tests['passed'] or tests['real_fit_attempts'] or records['checks_passed']!=744 or modules['verified']!=18:raise RuntimeError('READONLY_EVIDENCE_INCOMPLETE')
if core.TABLE not in instruction or core.TABLE!=params['decision_table_original']:raise RuntimeError('ORIGINAL_DECISION_TABLE_MISMATCH')
if core.BASELINE!=params['baseline_reference_OOF'] or core.TOLERANCE!=1e-9 or core.EPSILON!=1e-6:raise RuntimeError('FROZEN_NUMERIC_CONSTANT_MISMATCH')
compiled_sources=list((ROOT/'sources/B').glob('*.py'))+list((ROOT/'sources/project_src/oil_uplift').glob('*.py'))
for path in compiled_sources:
    ast.parse(path.read_text(encoding='utf-8-sig'))
help_result=subprocess.run([sys.executable,'-E','-B','run_b2.py','--help'],cwd=ROOT/'sources/B',capture_output=True,text=True,encoding='utf-8',timeout=30)
if help_result.returncode or '--history-lock' not in help_result.stdout:raise RuntimeError('EXPERIMENT_CLI_HELP_FAILED')
with (ROOT/'CLI_HELP_CODEX.txt').open('x',encoding='utf-8') as out:out.write(help_result.stdout)
requirements=dict(line.split('==') for line in (ROOT/'sources/B/requirements-b2.txt').read_text().splitlines() if line.strip())
deps=[]
for name,version in requirements.items():
    try:actual=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:actual='NOT_INSTALLED_IN_A_RUNTIME'
    deps.append({'name':name,'B_locked_version':version,'A_version':actual,'same':actual==version})
checklist=[
    {'item':1,'status':'PASS','basis':'Cutoff/window/scale/group checks in locked actual source and B structure records; independent synthetic boundary and official metric checks passed.'},
    {'item':2,'status':'PASS','basis':'B same-code baseline 73.71410733861434 with zero difference; A independently recovered it from 17/16/16/16/16 well-weighted fold scores and official loss. No A retraining.'},
    {'item':3,'status':'PASS','basis':'Exact R2 parameter bytes; frozen model parameters checked at fit; no changed feature/target/split/tau/budget definition. Baseline-first reuse follows R3 and does not add fits.'},
    {'item':4,'status':'PASS','basis':'Tau independently recomputed from 15 inner-fold aggregates; actual callsite uses train.iloc[iva] and inner OOF, not outer validation labels; split SHA and seed match.'},
    {'item':5,'status':'PASS','basis':'104 events independently reconstructed: models25/preprocessors20, failed0/retry0/full0; only88 training CSVs parsed, test parsing/prediction0 per loader and records.'},
    {'item':6,'status':'PASS','basis':'Candidate minus same-run baseline is exactly0; all folds and contribution sums agree; fixed decision row delta<=0 applies.'},
    {'item':7,'status':'PASS','basis':'REPORT_B first body section quotes the R3 startup sentence verbatim; CODEX-026B-04 closed.'},
    {'item':8,'status':'PASS','basis':'CLI --help, Python source compilation,42 synthetic tests and18 module source identities checked; complete OOF script supplied. Conditional train.py requirement does not activate at delta0. No actual clean-room retraining claimed.'},
    {'item':9,'status':'PASS','basis':'31/31 exact file coverage, hashes/scan record IDs and zero-hit records bound; final metadata scanning mechanism and synthetic marker rejection checked. A did not access original private marker inventory.'},
    {'item':10,'status':'PASS','basis':'All B registration fields present; card snapshot09f74e is ancestor of indexed3926e and RESULT bytes unchanged; A publication/index must bind actual3926e.'}
]
output={'task':'A2B-026/路线B-B2','role':'Codex（账户A2）独立审核与交付','reviews_commit':'3926e2972da62c61eb318abaa670a5da776d62ec','Claude_instruction_archive_commit':'088a71ae8760a57272f68cc2cb538b0a8eecc288','rules_commit':'0536eafab45b71ffd5f8f0160ee7957f1edd661d',
        'checklist':checklist,'hard_gates':{'leakage':'PASS','alignment':'PASS','well_isolation':'PASS','metric':'PASS'},
        'hard_gate_evidence_scope':'Readonly source/identity/ledger/aggregate audit and synthetic checks; no independent real-data retraining or row-level OOF replay.',
        'key_numbers':{'baseline_reproduction':result['baseline_reproduced'],'baseline_difference':0.,'candidate_OOF':result['two_stage_OOF'],'OOF 分数差':0.,'分数差':0.,'validation_wells':81,'target_rows':972,'rows_routed_to_zero':0,'model_fits_B':25,'preprocessor_fits_B':20,'retries_B':0,'checks_passed':744,'synthetic_tests_passed':42,'public_files_B':31},
        'decision_row':'| 分数差 ≤ 0 | 路线 B 淘汰 |','CODEX_026B_04_closed':True,'item11_closed':True,
        'closed_items':[{'id':'B2-IMPLEMENTATION','priority':'P1','scope':'Only the locked completed OOF version3926e; not deployment/full training acceptance.'},{'id':'B2-CODEX','priority':'P1','scope':'This R3 ten-item independent readonly audit.'},{'id':'CODEX-026B-04','priority':'P3','scope':'Exact startup sentence now verified in B report first section.'}],
        'open_unknowns':[{'id':'HIST-DTYPE','priority':'P1','missing':'Original historical per-file loading dtype identity; new panel fingerprints and equal scores do not replace it. Existing exception does not close this historical issue.'},{'id':'PROCESS-PROBE','priority':'P3','missing':'CIM process inventory unavailable on B machine; only this execution identity and files audited, no claim about all hidden/remote processes.'}],
        'known_definition_changes':[],'execution_order_clarification':'R3 baseline-first uses five outer B0 objects in memory, followed by15 inner regressors and5 classifiers; no additional baseline fits.',
        'B_FAULT_PROBES_were_postrun':True,'B_fault_probe_scope':'Five actual-function/AST probes, not full real-run fault replay; their later timing is not silently promoted to prefit tests.',
        'reproducibility':{'help_passed':True,'public_modules':18,'python_files_compiled':len(compiled_sources),'A_dependencies':deps,'A_dependencies_matching_B':sum(x['same'] for x in deps),'full_clean_environment_numeric_reproduction_performed':False},
        'integrity_scope':{'old_public_blobs_A_verified':265,'new_B_files':31,'old_local_files_B_reported_unchanged':2972,'raw_input_and_private_configuration_A_independently_rehashed':False},
        'privacy_scope':'A verified public file bytes and B per-file scan bindings plus synthetic scan behavior; no original marker inventory read by A.',
        'score_provenance':{'current_research_OOF':'B execution records supported by A aggregate/math/source/ledger checks','platform86_2003':'Historical user-reported platform score only; not this experiment result and not independently queried','new_platform_submission':False},
        'score_interpretation':'Locked zero-routing combination made no OOF changes; no zero loss recovered. Not evidence that all zero-state mechanisms are unpredictable; not causal attribution to tau, class sparsity or classifier alone.',
        'A_actual_model_fits':0,'A_actual_preprocessor_fits':0,'A_raw_data_read':False,'B_or_frozen_results_modified':False,
        'summary':'部分同意B的完成与淘汰判定：本轮十项及四硬门禁通过，增量0，按原表淘汰；当前版本实施P1和原句P3关闭，历史dtype P1及进程查询P3仍UNKNOWN。'}
with (ROOT/'RESULT_CODEX.json').open('x',encoding='utf-8') as out:json.dump(output,out,ensure_ascii=False,indent=2);out.write('\n')
print(json.dumps({'checklist_passed':10,'hard_gates':'PASS','delta':0,'closed':['B2-IMPLEMENTATION','B2-CODEX','CODEX-026B-04'],'open':['HIST-DTYPE P1','PROCESS-PROBE P3'],'A_fits':0,'dependencies_matching_B':output['reproducibility']['A_dependencies_matching_B']}))
