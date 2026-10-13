"""Verify the fixed-commit sources read by A1: raw Git blob bytes, length, SHA256.
Usage: python -I check_fixed_sources.py <git clone of ylrq8475-ui/Shiyou> <SOURCE_RECEIPT_A.json> [--write]
"""
import hashlib, json, subprocess, sys

SOURCES = {
 "b5e54cb8b5c0408a5eb620ac3026ce7fe71e7477": ("docs/handoff_20261013_A2B024_PLATFORM_SCORE_B_TO_NEW_A_V1",
   ["README.md", "PLATFORM_SCORE_REPORT_B.json", "SOURCE_AND_SCOPE.json", "SHA256SUMS.json", "PROMPT_FOR_NEW_ACCOUNT_A.md"]),
 "519b00da7dc29bae0448c797ee2e74e3e3cc35b3": ("docs/handoff_20261012_A2B024_R1_PLATFORM_EXPLORE_B_V1",
   ["README.md", "REPORT_B.md", "USER_AUTHORIZATION.md", "AUTHORIZATION_SELECTION.json", "DEPLOYMENT_PLAN.json",
    "DEPLOYMENT_ACCEPTANCE_B.json", "DEPLOYMENT_DEBUG_LOG.json", "MODEL_REGISTRY.json", "FORMAT_RULES_CHECK.json",
    "STANDALONE_ACCESS_AUDIT.json", "SYNTHETIC_RESULTS.json", "UPLOAD_SHA256SUMS.json", "DELIVERY_VERIFICATION.json",
    "ANONYMOUS_REVIEW_BUNDLE.zip"]),
 "e71c3e17e1c411ee0144d89a50ea394352c21f66": ("docs/handoff_20261012_A_SUCCESSOR_ONBOARDING_B_V1",
   ["README.md", "CONTEXT_AND_HISTORY.md", "SOURCE_PROVENANCE.json", "GITHUB_DELIVERY_RULES_A_V1.md"]),
 "65115714d49d17122989195910b119264bd93880": ("docs/handoff_20261012_A2B024_B",
   ["REPORT_B.md", "PLAN_R2.json", "FINAL_RESULT.json", "EXECUTION_SUPPLEMENT.json", "MODEL_REGISTRY.json"]),
 "3b38c63514f6da6ef9469da54030c1eac40e1abd": ("docs/handoff_20261012_A2B024_A_SUCCESSOR_REVIEW_v1",
   ["REPORT_A.md", "COLLABORATION_REPLY_A.md"]),
 "d8bc8f198a7acf6cac9cb8753406d6b15579e993": ("reports", ["a2b013_safe_submission.md"]),
 "4464061826607b40acdeac2e0ff4700641dd4272": ("docs/handoff_20261009", ["MODEL_DETAILS.md"]),
}

def blob(repo, commit, path):
    return subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], capture_output=True, check=True).stdout

repo, receipt = sys.argv[1], sys.argv[2]
rows = []
for c, (d, files) in SOURCES.items():
    for f in files:
        b = blob(repo, c, f"{d}/{f}")
        rows.append({"commit": c, "path": f"{d}/{f}", "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
if "--write" in sys.argv:
    json.dump({"author": "账户A（新接手）独立审核与交付", "files": rows}, open(receipt, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("written", len(rows)); raise SystemExit(0)
exp = {(r["commit"], r["path"]): r for r in json.load(open(receipt, encoding="utf-8"))["files"]}
bad = [r["path"] for r in rows if exp.get((r["commit"], r["path"])) != r]
print(json.dumps({"files": len(rows), "mismatches": bad}))
raise SystemExit(1 if bad else 0)
