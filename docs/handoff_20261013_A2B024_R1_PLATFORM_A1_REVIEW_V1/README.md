# A2B-024 R1 平台探索与 86.2003 报分：A1 独立只读审核

账户A（新接手）独立审核与交付。2026-10-13，Asia/Shanghai。

**结论：** 本次 R1 包与旧 A2B-013 包的 120 个预测值逐字节相同，只有日期补零不同。所以两次都是 86.2003 是预期结果，不是提分。原 A2B-024 R2 确认失败维持。当前框架几乎到不了 95+。

- [REPORT_A.md](REPORT_A.md)：完整审核报告
- [COLLABORATION_REPLY_A.md](COLLABORATION_REPLY_A.md)：供用户转交 B 的协作回复
- [EVIDENCE_LEVELS_A.json](EVIDENCE_LEVELS_A.json)：来源及证据等级
- [UNVERIFIED_ITEMS_A.md](UNVERIFIED_ITEMS_A.md)：风险与未核验项
- [SOURCE_RECEIPT_A.json](SOURCE_RECEIPT_A.json)：32 个固定来源文件的字节摘要
- [PRIVATE_ARTIFACT_IDENTITY_A.json](PRIVATE_ARTIFACT_IDENTITY_A.json)：四个私有 ZIP 的摘要与匿名比对结果（原文件不公开）
- [A1_CHECK_RESULTS.json](A1_CHECK_RESULTS.json)：A1 自编 20 项检查结果与 95+ 上限算术
- [a1_checks/](a1_checks/)：独立检查程序
- [A1_ANONYMOUS_REVIEW_BUNDLE.zip](A1_ANONYMOUS_REVIEW_BUNDLE.zip)：匿名复测包
- [SHA256SUMS.json](SHA256SUMS.json)：本目录各文件摘要

本目录不含原始数据、私有配置、真实井号、逐井预测、逐行 OOF 或模型权重。
