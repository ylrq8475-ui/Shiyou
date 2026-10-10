# A2B-021 账户 A 独立审计与交付

日期：2026-10-10。账户 B 执行训练，账户 A 完成本轮有限范围独立只读复核，身份不交换。

本目录仅新增 A 的报告、匿名复核证据和脚本。以用户指定的 B 提交 f3764bc 为基点发布独立 `codex/` 分支；不修改 B 交接、核心代码、模型、ZIP 或仓库主分支，不自动合并。

结论：40 项合成通过，4,141 项完整性/算术/事件/资格检查通过；六个研究方案全部失败，维持停止，无升级候选。A 没有训练真实模型。业务 P0 和历史 dtype UNKNOWN 保留。

阅读顺序：

1. [完整独立报告](REPORT_A.md)
2. [给 B 的协作回复](COLLABORATION_REPLY_A.md)
3. [下一步研究建议，非执行授权](NEXT_STEP.md)
4. [匿名复核结果](A_INDEPENDENT_REVIEW.json)、[数据分析补充](A_DATA_FINDINGS.json)及[合成日志](A_SYNTHETIC_TESTS.log)
5. [问题清单](AUDIT_QUEUE.md)、[有限范围签署](FINAL_SIGNOFF.md)
6. [A 完整匿名交付包](A2B021_ACCOUNT_A_REVIEW_BUNDLE_20261010.zip)、[公开清单](PUBLICATION_MANIFEST.json)及[隐私检查](PUBLICATION_PRIVACY_CHECK.json)

B 原交付见 [受检目录](https://github.com/ylrq8475-ui/Shiyou/tree/f3764bcc58337f9a4d86def44d5d6da9fc87ab95/docs/handoff_20261010_A2B021_B)。A 包不重复打包 B 的 353 项证据；它们可从此固定版本取得。

`independent_review.py` 是 A 的无训练复核入口，`derive_data_findings.py` 仅推导匿名聚合。输入布局为同级 `bundle/`（B 原 ZIP 解压）及 `received/`（B 原公开文件）。运行会新建结果，已存在结果时拒绝覆盖，应使用新的独立运行目录。受控入口阻止真实 sklearn fit 和已完成训练 execute；不得运行 B 的 `--execute`。

`receive_evidence.py` 供原机器 A 在已授权只读范围内接收固定提交、扫描本地私有标记，原始标记只驻留内存。没有赛事访问授权时不得运行该接收器；纯合成与聚合复核无需赛事数据。

中文报告交付前按自然化技能校对，未更改数字或技术结论。所有发布材料经本地隐私复扫，不含原始数据、私有配置内容、逐井标签/预测、OOF、模型权重或凭据。A 完整 ZIP 是审计交付包，不是 result.zip 或 submission_code.zip。
