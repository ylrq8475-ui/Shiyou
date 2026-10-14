"""Bind V3 registration to the completed fixed-source item-04 comparison."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'CODEX026B04_R2_SCOPE_REVIEW_20261014'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rules=ROOT/'sources/rules';instruction=ROOT/'sources/instruction'
for n,h in json.loads((rules/'SHA256SUMS.json').read_bytes()).items():
    if sha(rules/n)!=h:raise RuntimeError('V3_RULE_BYTE_HASH_MISMATCH')
if sha(instruction/'INSTRUCTION_ORIGINAL.md')!=json.loads((instruction/'SHA256SUMS.json').read_bytes())['INSTRUCTION_ORIGINAL.md']:
    raise RuntimeError('INSTRUCTION_ARCHIVE_BYTE_HASH_MISMATCH')
prior=json.loads((OLD/'ITEM04_R2_RESULT_CODEX.json').read_bytes())
published=json.loads((OLD/'ITEM04_R2_SHA256SUMS.json').read_bytes())
if sha(OLD/'ITEM04_R2_RESULT_CODEX.json')!=published['files']['ITEM04_R2_RESULT_CODEX.json']['sha256']:
    raise RuntimeError('PREVIOUS_PUBLISHED_COMPARISON_CHANGED')
if prior['reviewed_B_commit']!='213b1b465c61d799371e2b4326ebc71922c4f7ee' or prior['instruction_commit']!='0536eafab45b71ffd5f8f0160ee7957f1edd661d':
    raise RuntimeError('REVIEW_OR_ARCHIVE_IDENTITY_MISMATCH')
if prior['instruction_sha256']!=sha(instruction/'INSTRUCTION_ORIGINAL.md'):
    raise RuntimeError('ARCHIVED_ORIGINAL_CHANGED')
result={k:v for k,v in prior.items() if k!='check_results'}
result.update(registration_version='Prompt V3',rules_commit='0536eafab45b71ffd5f8f0160ee7957f1edd661d',
              Claude_instruction_archive_commit='0536eafab45b71ffd5f8f0160ee7957f1edd661d',
              comparison_evidence_commit='3c288e69e9ba2c43058a07ee53ccd810eba695f7',
              previous_comparison_file_sha256=sha(OLD/'ITEM04_R2_RESULT_CODEX.json'),
              current_scope='same item only; registration and index added; no repeat real-data checks or fits',
              index_record_role='Codex',index_reviews_commit=prior['reviewed_B_commit'],
              all_V3_rule_manifest_entries_verified=True,index_record_append_order='after report publication and byte verification')
with (ROOT/'ITEM04_V3_RESULT_CODEX.json').open('x',encoding='utf-8') as out:json.dump(result,out,ensure_ascii=False,indent=2)
print(json.dumps({'source_verified':True,'reviewed_B_commit':prior['reviewed_B_commit'],'item_status':prior['item_status'],
                  'issue_level':prior['issue_level'],'closed':prior['CODEX_026B_04_closed'],'B2_start_conditions_satisfied':False},ensure_ascii=True))
