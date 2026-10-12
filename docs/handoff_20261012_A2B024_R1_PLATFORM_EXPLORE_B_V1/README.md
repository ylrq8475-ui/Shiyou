# A2B-024 R1平台探索部署交接

账户B执行与交付。已完成用户选择的R1探索全量训练、私有保存和本地部署验收。真实模型/预处理各2次，无CV重跑。原研究确认失败保持，旧模型未替换，平台未上传。用户明确不等待A后续复核；本轮没有A部署签署。

**重要：10口测试井全部走B0，当前R1测试预测等于本次全量B0；不能据训练回退组路由收益承诺平台提分。**

REPORT_B.md为完整报告，DEPLOYMENT_ACCEPTANCE_B.json为匿名验收，MODEL_REGISTRY.json为探索工件登记。公开ANONYMOUS_REVIEW_BUNDLE.zip只供只读审阅，不含模型、真实预测、私有配置或原始数据，不能作为赛事提交包。正式两个ZIP已在执行端本机私有目录交付用户。

source/保存公开可审阅的推理与特征代码；故意不提供私有模型，其不能独立生成真实预测。真实独立可运行的完整包在本机submission_code.zip中，已解压端到端复测通过。

合成复测：在所列依赖环境下，从匿名包source目录运行python -E -B -m unittest test_deployment test_platform_contract，只使用虚构数据，真实拟合0。
