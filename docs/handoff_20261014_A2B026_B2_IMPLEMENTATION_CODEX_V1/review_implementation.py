"""Read a fixed public Git tree and existing public records; never import B code."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(r'C:\Users\Admin\petroleum_uplift_audit_A\CODEX_A2B026_CLOSEOUT_PREREG_REVIEW_20261014\publication_git')
B_COMMIT = '213b1b465c61d799371e2b4326ebc71922c4f7ee'
CLAUDE_COMMIT = '0536eafab45b71ffd5f8f0160ee7957f1edd661d'
PREFIX = 'docs/handoff_20261014_A2B026_B_CLOSEOUT_ROUTE_B_R2/'
CHECKS = []

def check(name, ok):
    CHECKS.append({'name': name, 'passed': bool(ok)})
    if not ok:
        raise RuntimeError(name)

def git(*args):
    result = subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError('PUBLIC_GIT_READ_FAILED')
    return result.stdout

def read(path):
    return git('show', B_COMMIT + ':' + path)

def write_new(name, value):
    with (ROOT / name).open('x', encoding='utf-8') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write('\n')

def locations(tree, function_names):
    return {node.name: node.lineno for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in function_names}

def main():
    check('fixed_B_commit_available', git('rev-parse', B_COMMIT).decode().strip() == B_COMMIT)
    manifest = json.loads(read(PREFIX + 'SHA256SUMS.json'))
    entries = manifest['files']
    for item in entries:
        check('manifest_path_inside_R2_' + item['path'], item['path'].startswith(PREFIX))
        data = read(item['path'])
        check('B_manifest_' + item['path'], len(data) == item['bytes'] and
              hashlib.sha256(data).hexdigest() == item['sha256'])
    result = json.loads(read(PREFIX + 'RESULT_B.json'))
    params = json.loads(read(PREFIX + 'PREREG_PARAMETERS.json'))
    files = git('ls-tree', '-r', '--name-only', B_COMMIT).decode().splitlines()
    route_python = [p for p in files if p.startswith(PREFIX) and p.endswith('.py')]
    check('R2_only_privacy_python_not_B2_implementation', route_python == [PREFIX + 'privacy_supplement.py'])
    check('B_declares_implementation_pending', any(v['id'] == 'B2-IMPLEMENTATION' and v['priority'] == 'P1' for v in result['open_items']))
    check('B_declares_no_B2_start', result['counts']['B2_started'] is False)
    check('B_actual_model_and_preprocessing_counts_zero', result['counts']['model_fit_entries'] == 0 and result['counts']['preprocessor_fit_entries'] == 0)
    check('locked_budget_not_training_authorization', params['model_training_allowed_this_turn'] is False)
    budget = params['budget_proposed_for_separate_B2_approval']
    check('budget_25_models_20_preprocessors_zero_retries', budget['model_fit_entries_max'] == 25 and budget['successful_preprocessor_fits_max'] == 20 and budget['fault_retries_max'] == 0)
    check('future_B2_four_gates_not_implemented', set(result['future_B2_hard_gates'].values()) == {'UNKNOWN'})
    sources = {p: read(p) for p in ['train.py', 'src/oil_uplift/cli.py', 'src/oil_uplift/training.py']}
    trees = {p: ast.parse(data.decode('utf-8-sig')) for p, data in sources.items()}
    check('old_train_invokes_old_cli', 'main(["train", *sys.argv[1:]])' in sources['train.py'].decode())
    old_training = sources['src/oil_uplift/training.py'].decode()
    check('old_flow_has_automatic_full_fit', 'final_pipeline = _model_pipeline' in old_training and '_fit_pipeline(final_pipeline' in old_training)
    check('old_flow_has_weight_persistence', 'joblib.dump(artifact, artifact_path)' in old_training)
    check('old_flow_no_zero_classifier_or_tau', 'ExtraTreesClassifier' not in old_training and 'l_plus' not in old_training)
    fingerprints = [{'path': p, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for p, data in sources.items()]
    evidence = {
        'task': 'A2B-026 / B2-IMPLEMENTATION', 'role': 'Codex / account A2',
        'reviews_commit': B_COMMIT, 'Claude_instruction_archive_commit': CLAUDE_COMMIT,
        'status': 'UNKNOWN', 'priority': 'P1', 'closed': False,
        'scope': 'Fixed B-1 R2 delivery and its existing public training dispatch only. No B-2 implementation supplied.',
        'verified_checks': len(CHECKS), 'checks': CHECKS,
        'B_R2_manifest_entries_verified': len(entries),
        'B_R2_python_files': route_python, 'public_tree_files_checked': len(files),
        'legacy_entry_sources': fingerprints,
        'legacy_functions_lines': locations(trees['src/oil_uplift/training.py'], {'train_from_panel', 'run_training'}),
        'legacy_cli_main_line': locations(trees['src/oil_uplift/cli.py'], {'main'})['main'],
        'legacy_train_is_not_B2': True,
        'legacy_entry_risk': 'Old run_training performs full fitting and joblib persistence; do not invoke it as B-2.',
        'missing_evidence': ['Actual runnable B-2 train.py and algorithm modules', 'Implementation lock for the actual executable', 'Executed synthetic checks and fault injection tied to code SHA256', 'Fit-scope, label-source and stop-path observations'],
        'hard_gates_B2_implementation': {'leakage': 'UNKNOWN', 'alignment': 'UNKNOWN', 'well_isolation': 'UNKNOWN', 'metric': 'UNKNOWN'},
        'hard_gate_UNKNOWN_reason': 'Implementation evidence unavailable, not an observed data leakage or metric error. Parent evidence gap is P1.',
        'B_recorded_model_fit_entries': 0, 'B_recorded_preprocessor_fit_entries': 0,
        'A_actual_model_fits': 0, 'A_actual_preprocessor_fits': 0,
        'A_raw_data_read': False, 'A_B_code_imported_or_executed': False,
        'A_B_project_changed': False,
        'official_OOF_delta': None, 'new_scores_produced': False,
        'item_11': 'PASS_CLOSED_FROM_PREVIOUS_CODEX_REVIEW',
        'CODEX_026B_04': 'FAIL_P3_OPEN_SEMANTICALLY_UNCHANGED',
        'B2_real_training_authorized_this_turn': False,
        'decision_row': 'B2-IMPLEMENTATION：UNKNOWN（P1），未关闭；第11项：已关闭；B-2启动条件：不满足；OOF分数差：尚未产生，不套用收益行。'
    }
    write_new('IMPLEMENTATION_RESULT_CODEX.json', evidence)
    print(json.dumps({'checks_passed': len(CHECKS), 'manifest_entries': len(entries), 'implementation': 'UNKNOWN/P1', 'closed': False, 'A_model_fits': 0, 'A_preprocessor_fits': 0}))

if __name__ == '__main__':
    main()
