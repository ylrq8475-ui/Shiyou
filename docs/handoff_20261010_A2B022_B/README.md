# A2B-022 账户B匿名交接｜2026-10-10

账户B执行与交付；账户A独立复核PENDING。

输入诊断与唯一精确去重候选已完成。新对照60模型/60原预处理拟合（各30），候选未过门槛，停止，无保留模型、升级或正式提交。这里的60是两方案合计，不是每方案60。

阅读顺序：REPORT_B.md、MECHANISM_LEDGER.md、MODEL_COMPARISON.json、ERROR_ATTRIBUTION.json、FIT_ACCOUNTING.json、B2A_022_REVIEW_REQUEST.md，最后下载匿名复测ZIP及其SHA256。复测ZIP不含原始CSV、私有配置内容、井号、逐井预测/标签、OOF、模型权重或凭据。代码和运行摘要中的路径/哈希为身份元数据。

下载ZIP到新目录后，可使用隔离Python运行 `python -E -B review_only.py --bundle-root <解压目录>`；此入口只执行合成和匿名算术。普通源码中的run_experiment.py是审查对象，不能因收到本包再次执行--execute。

本轮解释器和依赖不同于历史的可能性已按实际锁记录；本轮同环境配对，不宣称历史dtype或业务语义已确认。固定及重复切分已被多轮使用，不称新的独立测试集。
