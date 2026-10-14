"""Verify the concurrently indexed public R3 archive, without accessing any data."""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMIT = '088a71ae8760a57272f68cc2cb538b0a8eecc288'
PREFIX = 'docs/handoff_20261014_A2B026_CLAUDE_INSTRUCTIONS_R3/'

def public(name):
    url = 'https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/' + COMMIT + '/' + PREFIX + name
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Account-A2-R3-source-check'}), timeout=25) as reply:
        return reply.read()

original = public('INSTRUCTION_ORIGINAL.md')
sums = json.loads(public('SHA256SUMS.json'))
digest = hashlib.sha256(original).hexdigest()
if digest != sums['INSTRUCTION_ORIGINAL.md']:
    raise RuntimeError('R3_ARCHIVE_HASH_MISMATCH')
text = original.decode('utf-8')
requirements = [
    '用户批准原话（2026-10-14 17:28）：批准B-2并发布',
    '只做 OOF 实验，不碰测试集，不打包，不提交平台',
    '完整可运行的实验脚本（无论结果如何都要提交，用于复现）；若分数差 ≥ +1.0，另交 train.py',
    '拟合次数不得超过预注册预算',
    '容差 1e−9',
    '启动条件：第 11 项经 Codex 判为"通过"，且用户另行批准 B-2。'
]
if not all(value in text for value in requirements):
    raise RuntimeError('R3_REQUIREMENT_TRANSCRIPTION_MISMATCH')
result = json.loads((ROOT / 'IMPLEMENTATION_RESULT_CODEX.json').read_bytes())
evidence = {
    'task': 'A2B-026 / B2-IMPLEMENTATION', 'role': 'Codex / Account A2',
    'reviews_commit': '213b1b465c61d799371e2b4326ebc71922c4f7ee',
    'Claude_instruction_archive_commit': COMMIT,
    'verified_archive_sha256': digest, 'archive_bytes': len(original), 'requirements_checked': len(requirements),
    'archive_recorded_user_B2_approval': True, 'approval_provenance': 'R3 instruction archive, not a new approval issued by A',
    'prior_audit_report_commit': 'e5ca2956fd30fdd56bc0f9bc3512076610716226',
    'correction': 'Do not repeat B-2 approval; experiment entry required for all outcomes, standalone train.py required only if delta >= +1.0.',
    'implementation_status': 'UNKNOWN', 'priority': 'P1', 'closed': False,
    'missing_evidence': ['Actual B2 experiment implementation', 'Actual implementation lock', 'Executed fit-scope, provenance and stop-path synthetic checks'],
    'hard_gates': {'leakage': 'UNKNOWN', 'alignment': 'UNKNOWN', 'well_isolation': 'UNKNOWN', 'metric': 'UNKNOWN'},
    'hard_gate_scope': 'B-2 implementation evidence unavailable; not observed violations; parent missing-evidence item P1.',
    'item_11_closed': True, 'verbatim_B2_start_conditions_met_in_archive': True,
    'CODEX_026B_04': 'P3_OPEN_PENDING_VERBATIM_B2_REPORT',
    'decision_row': '第11项：已关闭；B-2原文启动条件：满足（R3存档批准）；B2-IMPLEMENTATION：UNKNOWN（P1），待实际实现复测；OOF分数差：尚未产生，不套用收益行。',
    'A_model_fits': 0, 'A_preprocessor_fits': 0, 'A_real_data_read': False,
    'no_new_training_authorization_or_plan_change_by_A': True,
    'reference_checks': result['verified_checks'], 'synthetic_reference_tests': 14,
    'training_budget_unchanged': {'models_max': 25, 'preprocessors_max': 20, 'retries': 0, 'full_fits': 0, 'weights_saved': 0},
    'older_request_superseded': 'COLLABORATION_REQUEST_B.md implementation-only approval recommendation is superseded by this R3-aware addendum.'
}
with (ROOT / 'R3_IMPLEMENTATION_STATUS_CODEX.json').open('x', encoding='utf-8') as out:
    json.dump(evidence, out, ensure_ascii=False, indent=2)
    out.write('\n')
print(json.dumps({'R3_hash_match': True, 'requirements_checked': len(requirements), 'B2_approval_in_archive': True, 'P1_closed': False, 'A_model_fits': 0}))
