# Prompt：B（执行）—— A2B-026 阶段 0

> **用户转发本 Prompt，即视为批准阶段 0（零拟合诊断）。阶段 1 不在本次批准范围内。**

你是账户 **B**，负责执行。Claude 负责方案与指令，Codex 负责审核，用户是唯一协调人。完成后把结果交给用户转给 Codex，不直接联系其他账户。

## 来源

提交 `3256382fb56efecf37f54b4ce3bd4287ffe1f71c`，目录 `docs/handoff_20261013_95PLUS_DIRECTION_RESEARCH_V1`：
- PRIMARY_EXPERIMENT_DRAFT.md（阶段 0 一节）；
- reference/diagnostics_reference.py、reference/test_diagnostics_reference.py；
- SHA256SUMS.json：执行前核对以上文件。

## 步骤

1. 运行参考实现的 12 项合成测试，必须全部通过，期间禁止任何真实拟合。
2. **D0**：检查截止为 M 时，特征生成器的列集是否与现有 325 列同名同序；在训练和测试两侧做截止不变性审计（删去 ≥M+1 的记录后特征不变）。只报告计数。
3. **D1**：对 81 口完整训练井调用 `zero_month_mass`。
4. **D2**：对 M 与 M−1 都 >0 的训练井调用 `compare_anchors`；另报告测试 10 口井中两者都 >0 的井数。
5. **D4**：对 81 口完整训练井调用 `smooth_oracle_scores`。
6. 按 `DECISION` 字典写出各项判定，不得调整阈值。

## 约束

- 模型拟合 0 次，预处理拟合 0 次，并留有计数记录。
- 原始数据只读、不复制。
- 只写匿名聚合，不写井号、月份、原值、逐井标签或预测。
- 不改锚点或目标窗口；不训练；不打包；不提交平台。

## 交付

在 B 专用新 codex/ 分支和版本目录发布：
- REPORT_B.md；
- 阶段 0 结果 JSON（含各项判定）；
- 计数与隐私扫描记录；
- SHA256 清单。

回取并按字节核对后，给出固定提交号，交由用户转给 Codex。
