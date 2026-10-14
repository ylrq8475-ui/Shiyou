【交付登记卡】
任务编号/阶段：CODEX-026B-04／原指令逐字对照与用户转发B-R2差异补审
角色：Codex 审核（账户A2）
分支：codex/a2b026-codex-closeout-prereg-review-20261014
完整提交号（40位，既有Codex登记基准）：e69a3784aded419c0c9bbcc8c7a7a15c1a175a79；本补充实际发布提交由固定交付链接登记。
被审B提交号（40位）：213b1b465c61d799371e2b4326ebc71922c4f7ee
目录路径：docs/handoff_20261014_A2B026_CODEX_CLOSEOUT_PREREG_REVIEW_V1
结果文件路径（单个JSON）：docs/handoff_20261014_A2B026_CODEX_CLOSEOUT_PREREG_REVIEW_V1/ITEM04_R2_RESULT_CODEX.json
关键数字：决策表文字差异0；+1.0门槛差异0；启动原句转录差异1；新增R2文件12；旧文件改动0；本轮模型及预处理拟合0；OOF分数差不适用。
硬门禁结论：泄漏：通过／错位：通过／井级隔离：通过／指标：通过（继承已有有限范围，本次仅文件、指令和差异核验，非未来B-2实现验收）。
UNKNOWN与未关闭项：无UNKNOWN；CODEX-026B-04，失败（P3），启动原句未逐字转录；原P1缺原指令证据的问题已消除。
对应决策表行：CODEX-026B-04：未关闭；第11项：已关闭；B-2启动条件：不满足。

## 原文对照

[Claude存档原文](https://github.com/ylrq8475-ui/Shiyou/blob/0536eafab45b71ffd5f8f0160ee7957f1edd661d/docs/handoff_20261014_A2B026_CLAUDE_INSTRUCTIONS_R2/INSTRUCTION_ORIGINAL.md)实际SHA256与同目录清单一致：`eeeea77137a7d48d2ccd87a045a0a733f472233b26f3a05abc925e4d9034d59c`。原文的两个空格表格嵌入缩进及LF/CRLF是展示格式，比较时去除，文字、数字、符号和标点保持。

| 对照项 | 判定 | 差异 |
|---|---|---|
| 四行决策表 | 通过 | R2的Markdown、参数JSON和结果JSON与原表文字一致。 |
| +1.0门槛 | 通过 | 原表和R2均为OOF分数差≥+1.0，没有数值改变。 |
| 启动条件逐字转录 | 失败（P3） | 原句未出现在PREREG_ROUTE_B.md；已有表述逻辑一致，不改变授权边界。 |

差异1，原指令要求的句子为：

> 启动条件：第 11 项经 Codex 判为"通过"，且用户另行批准 B-2。

B预注册第1节写成：

> 阶段B-1仅预注册；阶段B-2需要另行批准，且启动前必须由Codex明确关闭第11项。

第8节另以“未经单独授权且第11项未由Codex关闭前，禁止真实拟合”表述。它们保留两项必要条件，但不是原句的逐字转录；REPORT_B.md的等价说明也不能替代指定文件中的逐字要求。最小文字修正是把原句完整写入PREREG_ROUTE_B.md；不涉及阈值、模型、拟合预算或训练。此差异按V2归P3形式瑕疵，不能说成泄漏或模型错误，也不新增训练批准门槛。

## 两个B提交的关系与覆盖

0f4f2295f971fb3d9ff82f31bb5eb2e5b74889f9是旧预注册V1。用户转发的213b1b465c61d799371e2b4326ebc71922c4f7ee是其后续R2，经过3个提交，只新增12份R2文件，旧253份仓库文件全部保持。此前登记卡绑定0f4f，确实未覆盖213的新增部分；本次已按用户转发的213逐文件补审，未将旧结论自动套用到R2。

主要变更已核对：四行决策表恢复存档原文；τ从102项内层OOF网格改为内层正值B0损失的公式τ=(1−ℓ+)/(2−ℓ+)；置零比较由≥改为>，相等保留B0；拟合建议预算40→25，内层分类器15→0，预处理仍20；回归目标、模型参数、325列、M−1截止和固定井级折未变。上述均为预注册文本，本轮没有训练。原隐私程序、24份补扫输出和历史重建清单与此前已审核字节相同，第11项关闭结论延续。

12份新增文件均在`docs/handoff_20261014_A2B026_B_CLOSEOUT_ROUTE_B_R2/`：FIT_COUNTS.json、HISTORIC_SCAN_SELECTION_RECONSTRUCTED.json、PREREG_PARAMETERS.json、PREREG_ROUTE_B.md、PREREG_STATIC_CHECKS.json、PRIVACY_COVERAGE_MAP.md、PRIVACY_SUPPLEMENT_SCAN_RAW.json、REPORT_B.md、RESULT_B.json、SHA256SUMS.json、SOURCE_RECEIPT_R2.json、privacy_supplement.py。逐项路径和提交关系见ITEM04_R2_COMMIT_RELATION.json。

总结论：**CODEX-026B-04因一处逐字转录差异判失败（P3），原P1证据缺口已消除，本次已覆盖用户转发的213提交，B-2启动条件仍不满足。**

原文存档明确本轮“不训练”，并要求用户另行批准B-2；此次未收到该另行批准。P3文字差异只记录、不作为额外训练阻断条件。实际完成73项字节、关联、静态及算术检查；未读取赛事数据、未拟合、未修改B文件或旧审核成果。
