"""Independent arithmetic and evidence binding; never opens raw data or models."""
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
B = ROOT / "sources/B"
CHECKS = []

def load(name): return json.loads((B / name).read_bytes())
def sha(data): return hashlib.sha256(data).hexdigest()
def check(name, passed):
    CHECKS.append({"name": name, "passed": bool(passed)})
    if not passed: raise AssertionError(name)
def close(a, c, tolerance=1e-12): return math.isclose(float(a), float(c), rel_tol=0, abs_tol=tolerance)
def content(name):
    if name == "SYNTHETIC_LOG.txt": return (ROOT / "sources_exact/B" / name).read_bytes()
    return (B / name).read_bytes()

def main():
    receipt = json.loads((ROOT / "SOURCE_RETRIEVAL_CODEX.json").read_bytes())
    result, plan = load("RESULT_A2B027_STAGE0.json"), load("PLAN_STAGE0.json")
    lock, source = load("IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json"), load("SOURCE_RECEIPT.json")
    events, counts, fields = load("EVENTS.json"), load("FIT_COUNTS.json"), load("F0_FIELD_RESULTS.json")
    privacy, manifest = load("PRIVACY_SCAN_RAW.json"), load("SHA256SUMS.json")
    check("30 fixed public B files received by Git identity", receipt["B_files"] == 30 and receipt["B_git_blobs_match"])
    instruction = (ROOT / "sources/Claude/INSTRUCTION_ORIGINAL.md").read_bytes()
    check("R4 exact user SHA256", sha(instruction) == "523dbf070126f03592e39714076a67ba4295837cf89f2317746b7c9c693a6e62")
    check("R4 source receipt identity", source["R4"]["sha256"] == sha(instruction))
    for row in manifest["files"]:
        name = PurePosixPath(row["path"]).name; data = content(name)
        check("SHA and bytes: " + name, sha(data) == row["sha256"] and len(data) == row["bytes"])
    check("manifest covers 29 nonself files", len(manifest["files"]) == 29)
    for name, digest in lock["sources"].items():
        if (B / name).is_file(): check("prediagnostic identity: " + name, sha(content(name)) == digest)
    check("plan locked exactly", lock["plan_sha256"] == sha(content("PLAN_STAGE0.json")))
    check("source receipt locked exactly", lock["source_receipt_sha256"] == sha(content("SOURCE_RECEIPT.json")))
    check("model budget zero", plan["budget"]["model_fit_entries"] == 0 and result["model_fits"] == 0)
    check("preprocessing budget exactly 5", plan["budget"]["preprocessor_fit_entries"] == 5 and result["preprocessor_fits"] == 5)
    check("counter dictionary result binding", result["fit_counts"] == counts)
    for name in ("model_fit_attempted", "model_fit_completed", "preprocessor_fit_failed", "forbidden_preprocessing_attempts", "model_weights_loaded", "model_weights_saved", "synthetic_SVD_calls"):
        check("counter zero: " + name, counts[name] == 0)
    check("preprocessor counter closure", counts["preprocessor_fit_entered"] == counts["preprocessor_fit_completed"] == 5)
    check("event order", [e["sequence"] for e in events] == list(range(1, 16)))
    check("16 synthetic tests before reading data", events[0]["event"] == "synthetic_checks_passed_before_competition_data" and events[0]["tests"] == 16)
    check("lock before numerical work", events[1]["event"] == "identity_structure_and_plan_locked" and all(v == 0 for v in events[1]["fit_counts"].values()))
    entered = [e for e in events if e["event"] == "F1_training_SVD_entered"]
    completed = [e for e in events if e["event"] == "F1_training_SVD_completed"]
    check("exactly five enters and completions", len(entered) == len(completed) == 5)
    for n, (start, finish) in enumerate(zip(entered, completed), 1):
        check(f"fold {n} paired", start["fold"] == finish["fold"] == n and start["sequence"] + 1 == finish["sequence"])
        check(f"fold {n} counter", start["fit_counts"]["preprocessor_fit_entered"] == n and start["fit_counts"]["preprocessor_fit_completed"] == n-1 and finish["fit_counts"]["preprocessor_fit_completed"] == n)
        check(f"fold {n} time", datetime.fromisoformat(lock["time"]) < datetime.fromisoformat(start["time"]) < datetime.fromisoformat(finish["time"]))
    for event in events:
        check(f"event {event['sequence']} zero model entries", event["fit_counts"]["model_fit_attempted"] == event["fit_counts"]["model_fit_completed"] == 0)
    check("event end counts match", events[-1]["fit_counts"] == counts)
    for name in ("test_labels_read", "external_training_data_used", "pretrained_models_used"):
        check("prohibition: " + name, result[name] is False)
    for name in ("test_predictions_generated", "formal_packages_created", "platform_submissions"):
        check("zero: " + name, result[name] == 0)
    check("Dalpha actually missing, not zero", all(result[name] is None for name in ("Dalpha_score", "Dalpha_delta", "Dalpha_losses")))
    check("Dalpha P1 not silently downgraded", any(row["id"] == "A027-OOF-SOURCE" and row["grade"] == "P1" for row in result["open_unknowns"]))
    check("HIST DTYPE exception retained", "UNKNOWN" in result["historical_dtype"] and "nonblocking" in result["historical_dtype"])
    check("epsilon and delta locked before scores", result["epsilon"] == result["delta"] == plan["epsilon"] == plan["delta"] == 1e-6)
    structure, split = load("STRUCTURE_GATES.json"), load("SPLIT_REFERENCE.json")
    check("81 wells / 972 rows / 325 features", (structure["train_complete_wells"], structure["train_rows"], structure["features"]) == (81, 972, 325))
    check("split exact", structure["fixed_split_sha256"] == split["outer_split_sha256"] == lock["split_sha256"])
    check("seed and fold count exact", split["seed"] == 20260916 and split["folds"] == 5)
    check("test RCYL excluded", structure["test_target_columns_parsed"] == 0 and structure["test_history_tables_parsed_without_RCYL"] == 10)
    check("well and cutoff gates", structure["well_overlap"] == structure["cutoff_audit"]["future_sensitive_feature_count"] == 0)
    reference = load("REFERENCE_PANEL_CONTRACT.json")["contract"]
    check("panel identity contract", reference["panel_identity"] == structure["frozen_panel_identity"] == lock["panel_identity"])
    check("feature order count", len(reference["feature_order"]) == 325)
    dictionary = load("FIELD_DICTIONARY.json")
    definitions = {name: (meaning, unit) for name, meaning, unit in dictionary["fields"]}
    check("29 dictionary fields", len(definitions) == len(fields["fields"]) == 29)
    expected = {"RCYL": ("日产油", "t"), "RCYL1": ("日产液", "t"), "YY": ("油压", "MPa"), "TY": ("套压", "MPa"), "PL": ("理论排量", "m³/d"), "BX": ("泵效", "%"), "SXDL": ("上电流", "A"), "XXDL": ("下电流", "A"), "CCJHWND": ("采聚浓度", "mg/l"), "CCJND": ("采碱浓度", "mg/l"), "CCBHJND": ("采表浓度", "mg/l"), "CCYND": ("采出液粘度", "mPa.s")}
    for name, meaning in expected.items(): check("official meaning/unit: " + name, definitions[name] == meaning)
    for row in fields["fields"]:
        check("field dictionary binding: " + row["field"], row["official_dictionary_matched"] and (row["official_meaning"], row["official_unit"]) == definitions[row["field"]])
        check("field missing/zero unknown: " + row["field"], row["missing_zero_meaning"].startswith("UNKNOWN"))
    combos = fields["combinations"]; passing = 0
    for row in combos:
        if row.get("coverage") is None:
            check("unavailable not zero: " + row["id"], row["passes"] is False)
            continue
        check("coverage complete: " + row["id"], row["complete_well_denominator"] == 81 and close(row["coverage"], row["valid_complete_wells"]/81))
        check("coverage all: " + row["id"], row["all_train_denominator"] == 88 and close(row["all_train_coverage"], row["valid_all_train_wells"]/88))
        expected_pass = row["M_minus_1_available"] and row["coverage"] >= .8
        check("coverage gate: " + row["id"], row["passes"] == expected_pass)
        passing += expected_pass
    check("F0 pass count", passing == fields["F0_combo_pass_count"] == result["F0_combo_pass_count"] == 5)
    check("no injection inference", result["F0_injection_assessment"]["official_injection_rate_fields"] == 0 and result["F0_injection_assessment"]["produced_not_injected"] and not result["F0_injection_assessment"]["CRM_or_LSTM_implemented"])
    shape = result["F1_shape_counts"]
    check("mutually exclusive shapes total", shape["上升"] + shape["下降"] + shape["稳产"] == 81)
    check("zero shape separate", 0 <= shape["含0值"] <= 81)
    check("SVD validation well count", sum(row["validation_wells"] for row in result["F1_SVD_records"]) == 81)
    for row in result["F1_SVD_records"]:
        check("SVD isolation " + str(row["fold"]), row["training_wells"] + row["validation_wells"] == 81 and row["training_validation_well_intersection"] == 0 and row["basis_fits"] == 1 and row["K_reuse"] == [1,2,3,4])
    for k in range(1, 5):
        summary = result[f"F1_K{k}_summary"]
        check(f"K{k} score from well-mean loss", close(result[f"F1_oracle_K{k}"], 100*(1-summary["weighted_losses"]["m1_to_12"])))
        check(f"K{k} summary binding", result[f"F1_oracle_K{k}"] == summary["official_score"] == events[-1][f"F1_oracle_K{k}"])
    beta = result["Dbeta_counts"]; historical = beta["complete_cohort_historical_events"]
    check("historical count closure", historical["prior_segments"] == historical["qualified_events"] + historical["rejected_nonconsecutive_or_missing"] + historical["rejected_refracture"] == 65)
    for h in (1, 2):
        labels = beta[f"incomplete_new_m{h}_labels"] + historical[f"new_m{h}_labels"]
        check(f"Dbeta month {h} arithmetic", labels == 32 and beta["denominator"] == 81 and close(result[f"Dbeta_increase_m{h}"], labels/81))
    check("Dbeta train only", beta["incomplete_wells"] == 7 and beta["test_history_counted"] is False)
    gamma = result["Dgamma_details"]
    check("Dgamma variance ratio", close(result["Dgamma_share"], gamma["common_variance_ddof0"]/gamma["pooled_variance_ddof0"]))
    check("Dgamma correlation binding", result["Dgamma_lag1"] == gamma["Dgamma_lag1"] and -1 <= gamma["Dgamma_lag1"] <= 1)
    check("Dgamma pair and month counts", gamma["adjacent_common_month_pairs"] == gamma["eligible_common_months"]-1 == 70)
    text = instruction.decode("utf-8")
    locked_rows = ["| " + " | ".join(row) + " |" for row in plan["decision_table"]]
    report = content("REPORT_B.md").decode("utf-8")
    for row in locked_rows:
        check("R4 decision row exact: " + row.split("|")[1].strip(), row in text and row in report)
    check("F1 actual gray interval", max(result[f"F1_oracle_K{k}"] for k in (1,2,3)) < 90 and result["F1_oracle_K3"] >= 85)
    check("Dgamma fails both locked criteria", result["Dgamma_share"] < .3 and result["Dgamma_lag1"] < .5)
    check("privacy coverage exact set", {row["path"] for row in privacy["records"]} == {row["path"] for row in receipt["files"] if row["label"] == "B"})
    check("privacy 30 unique records", privacy["published_files"] == privacy["scan_records"] == len(privacy["records"]) == len({r["record_id"] for r in privacy["records"]}) == 30)
    for row in privacy["records"]:
        name = PurePosixPath(row["path"]).name
        check("privacy zero-hit: " + name, row["result"] == "PASS" and row["credential_or_private_path_hits"] == sum(row["private_marker_hits"].values()) == 0)
        if row["sha256"] is not None: check("privacy byte binding: " + name, sha(content(name)) == row["sha256"] and len(content(name)) == row["bytes"])
        else: check("privacy self-binding stated: " + name, name in {"PRIVACY_SCAN_RAW.json", "SHA256SUMS.json"} and "same checker" in row["scan_method"])
    check("privacy no exemptions", privacy["exemptions"] == 0 and privacy["all_pass"])
    header = report.split("\n\n\n# ")[0]
    for field in ("任务编号/阶段", "角色", "分支", "完整提交号", "目录路径", "结果文件路径", "关键数字", "硬门禁结论", "UNKNOWN", "对应决策表行", "所依据的 Claude 指令存档提交号"):
        check("B registration: " + field, field in header)
    check("B decision row not self-signed", "对应决策表行（仅 Codex 填写；B 写不适用）：不适用" in header)
    binding = load("RESULT_SNAPSHOT_BINDING.json")
    check("snapshot binding", sha(content("RESULT_A2B027_STAGE0.json")) == binding["result_sha256"] and len(content("RESULT_A2B027_STAGE0.json")) == binding["result_bytes"])
    check("final B fixed in index", receipt["B_commit"] == "a0e762a87352877dde179dc505797c0d1638a757")
    for row in result["integrity"].items():
        name, value = row
        if name != "protected_files_checked": check("B integrity assertion: " + name, value is True)
    for path in B.glob("*.py"): compile(path.read_text(encoding="utf-8"), str(path), "exec")
    check("all six B Python sources compile", len(list(B.glob("*.py"))) == 6)
    payload = {"B_commit": receipt["B_commit"], "instruction_commit": receipt["R4_commit"],
               "checks": CHECKS, "checks_passed": len(CHECKS), "all_passed": True,
               "F0_combo_pass_count": passing, "F1_oracle_K1_to_K4": [result[f"F1_oracle_K{k}"] for k in range(1,5)],
               "Dalpha_status": "UNKNOWN P1 - not executed", "Dbeta_additional_m1_and_m2": [32,32],
               "Dbeta_ratio": 32/81, "Dgamma_variance_ratio_recomputed": gamma["common_variance_ddof0"]/gamma["pooled_variance_ddof0"],
               "Dgamma_lag1_source": "bound B result, code inspected and independent synthetic formula checked; real calendar series not supplied",
               "B_model_fits_from_bound_records": 0, "B_preprocessing_fits_from_bound_records": 5,
               "A_model_fits": 0, "A_preprocessing_fits": 0, "A_real_SVD_calls": 0,
               "A_raw_data_read": False, "A_private_marker_scan_repeated": False,
               "original_real_field_counts_and_F1_scores_not_independently_recomputed": True,
               "unpublished_preparation_helper_not_called_by_reviewed_real_entry": "prepare_stage0.py",
               "B_dir_and_original_input_immutability_is_B_bound_execution_evidence_not_A_remote_filesystem_access": True}
    with (ROOT / "AGGREGATE_AND_IDENTITY_REVIEW_CODEX.json").open("x", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2); output.write("\n")
    print(json.dumps({"checks_passed": len(CHECKS), "B_public_files": 30, "model_fits_A": 0, "preprocessor_fits_A": 0}))

if __name__ == "__main__": main()
