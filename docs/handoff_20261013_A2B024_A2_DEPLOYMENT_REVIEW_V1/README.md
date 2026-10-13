# 账户A2：R1探索部署与同分原因审核

账户A（新接手）独立审核与交付。2026-10-13。

主要发现：实际新旧结果的120个CSV预测全部相同，仅日期补零；最新附包与B交付身份匹配。原研究确认失败维持，探索另获用户授权；回退分支未覆盖当前测试井（B记录）。新增独立推理工程有效，但没有当前R1完整从头训练入口，列P1。

REPORT_A.md给出事实、来源边界、失败原因与未来单一机制建议；COLLABORATION_REPLY_A.md供用户转交。匿名证据含实际附件的汇总比较、独立算术、合成与身份记录，不含实际附件、模型、井号或预测值。

复测：在全新A目录放本包脚本与SOURCE_SPEC.json，用现有合适Python先运行`-E -B receive_public_sources.py`，只下载固定公开匿名证据；再运行`independent_evidence_a2.py`、`run_synthetic_a2.py`及`test_independent_a2.py`。后两者需要numpy/pandas/scikit-learn/joblib等已匹配环境，不安装依赖、不拟合、不加载真实模型。输出采用新文件，不覆盖旧结论。

附包比较与包内元数据程序分别是inspect_attachments.py、package_metadata_a2.py；再次执行需要本地获授权的新旧私有附件。它们不解压或反序列化权重，只在内存比较并输出匿名计数，公共证据不能恢复原始预测。

本轮A2：31项B合成及15项自编合成通过，1198项独立算术/身份一致性检查通过，拟合/真实模型加载0。实际平台报分来源及缺项见SCORE_LEDGER_A2.json；风险见AUDIT_QUEUE_A2.md。未修改冻结成果、升级、重新打正式包或上传平台。
