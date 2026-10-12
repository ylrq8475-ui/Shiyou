# A2B-024 R2 替代账户A实际执行审核 v1

账户A（替代接手）独立审核与交付。

结论见 [REPORT_A.md](REPORT_A.md)，转交回复见 [COLLABORATION_REPLY_A.md](COLLABORATION_REPLY_A.md)。同意确认失败后停止，不保留 R1、不升级。只读审核不等于真实训练复现。

本目录仅新增匿名审核材料，旧 A/B、main、冻结成果不变。B实际执行来源固定在65115714d49d17122989195910b119264bd93880；接手来源固定在e71c3e17e1c411ee0144d89a50ea394352c21f66。完整来源见SOURCE_RECEIPT_A.json。

自包含包：A2B024_A_SUCCESSOR_READONLY_REVIEW_v1.zip。解压后在已有Python环境运行：

```text
python -B retest_a.py --out <新的审核输出目录>
```

算术程序只使用Python标准库；合成检查需要已有numpy和pandas。本次验证环境为Python3.13.7、numpy2.4.3、pandas2.3.3。不安装依赖、不联网、不加载模型、不运行训练、不读取私有数据。复测入口先核验内层清单及嵌入的B公开匿名包摘要，再把B包安全解压到临时目录，仅运行A算术程序及14+26+19纯合成。临时目录由标准库清理，输出目录必须不存在。B包中的训练代码只作审阅证据，不会导入或执行。

仅复算聚合时，可先安全解压B匿名包，然后运行：

```text
python -B independent_audit.py --bundle <B匿名包解压目录> --out <结果JSON路径>
```

check_upstream_a.py是额外的Git只读核验程序，需本地仓库已包含固定A23提交；它只读Git blob和ZIP中的公开源码，核对摘要与固定回放，不导入上游代码。使用--repo、--bundle、--out指定本地路径；--out只写公开源码副本和匿名结果。

INNER_SHA256SUMS.json覆盖复测包内所有其他文件，UPLOAD_SHA256SUMS.json覆盖目录全部其他交付文件（包括ZIP与内层清单），各清单不含自身。交付回取按实际完整提交号核对原始字节、长度、文件集合及仅新增本目录的提交范围；回取记录由交付端单独保存，避免清单/提交号自引用。

PRIVACY_CHECK_A.json说明扫描范围及限制。没有原始CSV、私有配置原文、真实井号映射、逐井标签/预测、逐行OOF或权重。仅源码中的列名WELL_ID及明确标记的虚构测试标识符不属于真实井号。未独立核验事项详见UNVERIFIED_ITEMS_A.md，历史dtype仍UNKNOWN。
