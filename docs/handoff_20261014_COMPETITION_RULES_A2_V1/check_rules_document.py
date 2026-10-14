"""Check this rule compilation using text coverage and synthetic arithmetic only."""
from __future__ import annotations

import hashlib
import json
import math
import re
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCUMENT = ROOT / "比赛规则要求_详细版.md"


def synthetic_official_loss(target: list[float], prediction: list[float]) -> float:
    if len(target) != 12 or len(prediction) != 12:
        raise ValueError("exactly twelve horizons are required")
    if any(not math.isfinite(v) for v in target + prediction):
        raise ValueError("non-finite synthetic values are not accepted")
    if any(v < 0 for v in prediction):
        raise ValueError("negative synthetic submission is invalid")
    return math.fsum(2.0 ** (-t) * abs(p - y) / (abs(p) + abs(y) + 1e-6)
                     for t, (y, p) in enumerate(zip(target, prediction), 1))


class SyntheticMetricTests(unittest.TestCase):
    def test_all_zero(self):
        self.assertEqual(synthetic_official_loss([0.0] * 12, [0.0] * 12), 0.0)

    def test_epsilon_and_first_weight(self):
        self.assertEqual(synthetic_official_loss([0.0] * 12, [1e-6] + [0.0] * 11), 0.25)

    def test_order(self):
        early = synthetic_official_loss([0.0] * 12, [1.0] + [0.0] * 11)
        late = synthetic_official_loss([0.0] * 12, [0.0] * 11 + [1.0])
        self.assertEqual(early / late, 2048.0)

    def test_unnormalized_sum(self):
        actual = synthetic_official_loss([0.0] * 12, [1.0] * 12)
        self.assertAlmostEqual(actual, (4095.0 / 4096.0) / (1.0 + 1e-6), places=15)

    def test_bad_outputs(self):
        for bad in (-1.0, float("nan"), float("inf")):
            with self.subTest(bad=str(bad)), self.assertRaises(ValueError):
                synthetic_official_loss([0.0] * 12, [bad] + [0.0] * 11)

    def test_twelve_required(self):
        with self.assertRaises(ValueError):
            synthetic_official_loss([0.0] * 11, [0.0] * 11)

    def test_wells_equal_not_folds_equal(self):
        groups = [[100.0, 100.0], [0.0]]
        equal_wells = sum(sum(group) for group in groups) / sum(map(len, groups))
        equal_folds = sum(sum(group) / len(group) for group in groups) / len(groups)
        self.assertAlmostEqual(equal_wells, 200.0 / 3.0)
        self.assertNotEqual(equal_wells, equal_folds)


def create_json(path: Path, value: object) -> None:
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise RuntimeError("Existing document coverage differs; use a new version")
        return
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")
    require = {
        "12项原口径全部列出": all(len(re.findall(r"\| " + f"C{i:02d}" + r" \|", text)) == 1 for i in range(1, 13)),
        "目录0至15全部存在": all(re.search(r"^## " + str(i) + r"\. ", text, re.M) for i in range(16)),
        "协作请求和回复完整": all(name in text for name in ("【协作请求】", "【协作请求结束】", "【协作回复】", "【协作回复结束】", "回滚方法", "给用户的建议")),
        "公式包含epsilon与对井平均": all(part in text for part in ("10^{-6}", r"\frac{1}{2^t}", r"\frac{1}{N}\sum", "不归一化")),
        "官方与项目外部数据政策分开": all(part in text for part in ("官网现行条款", "本项目用户约束更严格", "一概禁止所有外部训练数据")),
        "新旧FAQ和处罚区别明确": all(part in text for part in ("已下架", "平台上传失败", "次日起2个自然日", "取消全部成绩", "只交预测")),
        "A榜B榜与资格完整": all(part in text for part in ("其中5口", "全部10口", ">75", "前10名", "70%", "30%")),
        "数据生命周期与知识产权": all(part in text for part in ("完整删除数据集", "永久、免费的使用许可", "其他商业赛事", "合法授权")),
        "正式输出与代码复现": all(part in text for part in ("WELL_ID,NY,RCYL", "result.zip", "submission_code.zip", "完整训练", "小于5GB", "4—6位小数")),
        "实际时点和语义证据边界": all(part in text for part in ("版本化项目解释", "M−1", "不应持续作为自动停止", "未来信息泄漏")),
        "V3与索引不伪造审核": all(part in text for part in ("登记规则1", "登记规则6", "reviews_commit", "不伪造")),
        "尚未获得条款明确列出": all(part in text for part in ("尚未见到", "隐私协议", "决赛细则", "未来公告")),
        "代码围栏成对": text.count("```") % 2 == 0,
        "标题后有空行": all(i + 1 < len(text.splitlines()) and text.splitlines()[i + 1] == "" for i, line in enumerate(text.splitlines()) if line.startswith("#")),
        "全部GitHub文档链接为40位提交": all(re.fullmatch(r"[0-9a-f]{40}", commit) for _, commit in re.findall(r"https://github\.com/ylrq8475-ui/Shiyou/(blob|tree)/([^/]+)/", text)),
    }
    table = re.findall(r"^\| (\d+) \| 1/(\d+) \| ([0-9.]+) \|$", text, re.M)
    require["12期权重数值逐行正确"] = len(table) == 12 and all(int(t) == i and int(d) == 2 ** i and Decimal(v) == Decimal(1) / Decimal(2 ** i) for i, (t, d, v) in enumerate(table, 1))
    require["公开文档无凭证模式"] = not re.search(r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AccessKeyId=|Signature=", text)
    results = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SyntheticMetricTests))
    require["独立合成指标算术"] = results.wasSuccessful()
    if not all(require.values()):
        raise RuntimeError("Rule compilation checks failed: " + ", ".join(key for key, passed in require.items() if not passed))
    payload = DOCUMENT.read_bytes()
    create_json(ROOT / "RULE_COVERAGE.json", {
        "type": "documentation_coverage_not_competition_or_model_compliance_signoff",
        "author": "账户A2（新接手）独立规则整理与交付", "document": DOCUMENT.name,
        "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "lines": len(text.splitlines()),
        "checks": require, "checks_passed": sum(require.values()), "synthetic_metric_tests": results.testsRun,
        "user_original_requirements_covered": [f"C{i:02d}" for i in range(1, 13)],
        "read_competition_data": False, "read_private_config": False, "model_fits": 0, "preprocessing_fits": 0,
        "full_well_identifier_scan_not_performed": True,
        "manual_privacy_review_complete": True,
        "all_unseen_or_future_rules_coverage_claimed": False,
        "no_B_findings_closed_by_this_compilation": True})
    print(json.dumps({"checks_passed": sum(require.values()), "synthetic_tests_passed": results.testsRun,
                      "document_bytes": len(payload), "document_lines": len(text.splitlines())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
