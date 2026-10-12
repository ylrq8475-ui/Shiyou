# A2B-024 R2 账户B研究与确认交付

账户B执行与交付。70次真实模型拟合完成，确认失败，按预注册停止；全量拟合0、真实新权重0、模型升级0。账户A独立结果复核PENDING。

[完整报告](REPORT_B.md) · [用户授权](USER_AUTHORIZATION.md) · [原R2计划](PLAN_R2.json) · [执行补充](EXECUTION_SUPPLEMENT.json) · [结果](evidence/FINAL_RESULT.json) · [运行锁](evidence/IMPLEMENTATION_PRETRAIN_LOCK.json) · [A复核请求](REQUEST_TO_A.md)

五组后续平均+0.478484，5/5正增益；条件确认仅+0.046033（需≥+0.20），前两月−0.011989（需≥0），故不保留候选。

只读复测：解压匿名审计包后执行 `python -B verify_evidence.py`，仅复算匿名聚合与检查字节/日志/源码AST，不读取赛事数据、不导入训练入口、不拟合。纯合成可另执行 `python -B -m unittest discover -s runtime -p test_pretrain_contracts.py`（26项）及 `python -B -m unittest discover -s runtime -p test_route.py`（19项，需numpy）。B的18项实际入口假估计器检查记录在SYNTHETIC_RESULTS.json；其源码绑定本机私有工程，不冒称移机直接运行或A已重训。

runtime/a24_runner.py是实际受控训练源码，仅供审阅，不应为本次只读复核执行。source_references只含既有公开适用Python源码；私有配置/赛事CSV/模型权重/逐行OOF不在包内。
