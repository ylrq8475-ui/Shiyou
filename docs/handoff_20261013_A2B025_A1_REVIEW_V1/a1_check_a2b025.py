"""账户A1（Claude）对 B 的 A2B-025 匿名交付做独立只读核对。

只读取 B 交付目录中的匿名 JSON 与 A024 公开 FINAL_RESULT.json；不读赛事数据、不拟合。
用法：
  python -I a1_check_a2b025.py <B交付目录 docs/handoff_20261013_A2B025_B_ORACLE_V1>
         <A024 FINAL_RESULT.json> <A1计划目录 docs/handoff_20261013_A2B025_PLAN_CLAUDE_A1_TO_B_V1> <输出JSON>
"""
import hashlib
import json
import os
import sys
import zipfile

CHECKS = []


def check(name, ok, **detail):
    CHECKS.append({"name": name, "passed": bool(ok), **detail})


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main(bdir, a024_final, a1dir, out):
    load = lambda n: json.load(open(os.path.join(bdir, n), encoding="utf-8"))
    # 1 字节身份
    m = load("SHA256SUMS.json")
    bad = [k for k, v in m.items() if sha(os.path.join(bdir, k)) != v["sha256"]
           or os.path.getsize(os.path.join(bdir, k)) != v["bytes"]]
    extra = sorted(set(os.listdir(bdir)) - set(m) - {"SHA256SUMS.json"})
    check("B_outer_manifest", not bad and not extra, entries=len(m), mismatches=bad, unlisted=extra)
    plan_sha = sha(os.path.join(bdir, "PLAN_A2B025.json"))
    check("B_uses_unmodified_A1_plan", plan_sha == sha(os.path.join(a1dir, "PLAN_A2B025.json"))
          == "e3021e14a547da9d5278b3ebbe0d26b4bdc8d732e27e0c706ad2f3a3ae31fdf4", plan_sha256=plan_sha)
    z = zipfile.ZipFile(os.path.join(bdir, "REVIEW_BUNDLE.zip"))
    check("B_bundle_crc_and_paths", z.testzip() is None and
          all(not n.startswith("/") and ".." not in n for n in z.namelist()), members=len(z.namelist()))
    same = all(hashlib.sha256(z.read("A1/" + f)).hexdigest() == sha(os.path.join(a1dir, f))
               for f in ("PLAN_A2B025.json", "PROMPT_FOR_ACCOUNT_B.md", "reference/a2b025_oracle.py",
                         "reference/test_a2b025_oracle.py", "SHA256SUMS.json"))
    check("B_bundle_A1_reference_byte_identical", same)
    src = z.read("actual_execution_source/run_a2b025.py").decode("utf-8")
    check("B_source_calls_unmodified_diagnose",
          "oracle.diagnose(pairs)" in src and "verify_reference()" in src and "A1_REFERENCE_CHANGED" in src)

    # 2 事件与预算
    ev = load("FIT_EVENTS.json")
    r = load("FINAL_RESULT.json")
    keys = ["preprocessor_entered", "preprocessor_completed", "model_entered", "model_completed"]
    check("events_contiguous_and_ordered",
          [e["sequence"] for e in ev] == list(range(1, len(ev) + 1))
          and [e["time"] for e in ev] == sorted(e["time"] for e in ev), events=len(ev))
    check("budget_monotone_and_closed",
          all(all(ev[i]["budget"][k] <= ev[i + 1]["budget"][k] for k in keys) for i in range(len(ev) - 1))
          and all(ev[-1]["budget"][k] == r["budget"][k] for k in keys))
    b = r["budget"]
    check("budget_within_plan",
          b["model_completed"] == b["model_entered"] == 5 and b["preprocessor_completed"] == b["preprocessor_entered"] == 5
          and b["fault_retries"] == b["C1_fits"] == b["full_fits"] == b["saved_models"] == 0, budget=b)

    # 3 复现门：独立按井加权重算
    ent = [e for e in ev if e["event"] == "model_fit_entered"]
    comp = [e for e in ev if e["event"] == "fold_completed"]
    n = [e["validation_wells"] for e in ent]
    fs = [e["official_score"] for e in comp]
    w = sum(s * k for s, k in zip(fs, n)) / sum(n)
    check("folds_partition_81_wells", sum(n) == 81 and all(e["training_wells"] + e["validation_wells"] == 81 for e in ent),
          validation_wells=n)
    check("well_weighted_oof_equals_reported", abs(w - r["stage1"]["official_oof"]) < 1e-10, recomputed=w,
          simple_fold_mean=sum(fs) / 5)
    check("reproduction_gate_1e-9", abs(r["stage1"]["official_oof"] - 73.71410733861434) <= 1e-9
          and [round(x, 6) for x in fs] == [71.453314, 77.536429, 75.129241, 64.626864, 79.965989])
    fx = [s for s in json.load(open(a024_final, encoding="utf-8"))["research"] if s["stage"] == "fixed_replay"][0]["arms"]["B0"]
    d = max(abs(a - c) for a, c in zip(fx["fold_scores"], fs))
    check("equals_A024_public_fixed_replay", fx["official_score"] == r["stage1"]["official_oof"] and d < 1e-12,
          max_fold_absdiff=d)

    # 4 神谕与决策
    o = r["stage2"]
    check("oracle_baseline_equals_replay", abs(o["baseline_oof"] - r["stage1"]["official_oof"]) < 1e-10)
    dec = "MAY_OPEN_NEW_PREREGISTRATION" if o["level_oracle_oof"] >= 90 else "CEILING_BELOW_95_KEEP_CURRENT_MODEL"
    check("decision_follows_locked_rule", dec == o["decision"] and o["decision_threshold"] == 90.0, decision=dec)
    check("best_scalar_not_below_level", o["best_scalar_oracle_oof"] >= o["level_oracle_oof"])
    c = load("STAGE0_COUNTS.json")["cohorts"]
    check("stage0_counts_nested",
          all(c[k]["wells"] >= c[k]["record_present"] >= c[k]["finite"] >= c[k]["finite_positive"] for k in c),
          counts={k: [c[k][x] for x in ("wells", "record_present", "finite", "finite_positive")] for k in c})

    # 5 解释用算术（推断，不是门禁）
    L = lambda s: 1 - s / 100
    interp = {}
    for k in ("level_oracle_oof", "best_scalar_oracle_oof", "shape_oracle_oof"):
        red = 1 - L(o[k]) / L(o["baseline_oof"])
        interp[k] = {"oof": o[k], "gain_vs_B0": o[k] - o["baseline_oof"], "loss_reduction": red,
                     "platform_if_same_relative_loss_cut": 100 * (1 - (1 - 0.862003) * (1 - red))}
    interp["note"] = "平台外推假设平台损失按OOF同比例下降；10井平台样本与81井OOF分布不同，这只是量级参考"
    res = {"author": "账户A（新接手）独立审核与交付 / A1（Claude）", "task": "A2B-025 readonly review",
           "real_fits": 0, "real_data_read": 0, "checks": CHECKS,
           "passed": sum(x["passed"] for x in CHECKS), "total": len(CHECKS), "interpretation_arithmetic": interp}
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(res["passed"], "/", res["total"])
    return 0 if res["passed"] == res["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:5]))
