# 账户A2：A2B-027阶段0／R4独立审核

主报告：REPORT_CODEX.md。唯一结果入口：RESULT_CODEX.json。

被审B固定提交：a0e762a87352877dde179dc505797c0d1638a757。来源R4：b383fbc3cc7b4c5a382970ecd6234d7b2dcb3c47；原文SHA已核对。V3规则保留，第三方项目禁令变更以R4及本轮用户说明为准；本轮本身仍无外部数据/预训练模型工作。

结论为部分同意，不是全部通过。F0计数和D-β达到数值条件；F1落在未触发既定动作的区间；D-γ未达；D-α缺输入未执行，P1不擅自降级。F0语义及取得时间、历史dtype继续UNKNOWN。没有训练授权或新平台成绩。

A完成44项纯合成检查、307项身份与聚合算术检查。真实数据和B远端磁盘未读取，真实诊断未再执行，实际模型/预处理/SVD拟合均0。失败的A测试夹具及来源换行问题见EXECUTION_NOTES_CODEX.md，不混为B缺陷。

复核方法：按SOURCE_RETRIEVAL_CODEX.json从固定B提交接收公开方法及JSON到sources/B，再运行 `python -E -B -X utf8 run_synthetic_review.py --run-label NEW_RUN` 及 `python -E -B -X utf8 audit_records.py`。接收器需要独立review_git中的固定B树；原字节测试日志由base64入口核对，见接收程序。输出文件已存在会阻断，复测请用新的A目录；不得运行B真实入口、追加模型拟合或重新执行5次数值SVD。

发布仅为匿名代码/聚合证据，不含数据、私有配置、模型权重、逐井标签/预测或真实OOF。不生成ZIP。最终固定提交及索引以原字节回取记录为准。

署名：账户A2（新接手）独立审核与交付。
