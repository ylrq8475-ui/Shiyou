# A2B-024 R2 账户B实际执行交付索引 V2

账户B执行与交付。研究60次及条件确认10次已完成；确认未达标，按预注册停止。全量拟合0、真实模型权重保存0、升级0，账户A实际实验独立复核PENDING。

五组研究平均增量+0.478484，5/5严格为正。确认增量+0.046033低于+0.20，前两月−0.011989低于0，不保留R1。63项合成和829项匿名审计检查通过。

- [完整研究报告](https://github.com/ylrq8475-ui/Shiyou/blob/ca3e0560099a1f408fd0da7e847fbb59e3dac416/docs/handoff_20261012_A2B024_B/REPORT_B.md)
- [账户A独立只读复核请求](https://github.com/ylrq8475-ui/Shiyou/blob/ca3e0560099a1f408fd0da7e847fbb59e3dac416/docs/handoff_20261012_A2B024_B/REQUEST_TO_A.md)
- [全部聚合结果](https://github.com/ylrq8475-ui/Shiyou/blob/ca3e0560099a1f408fd0da7e847fbb59e3dac416/docs/handoff_20261012_A2B024_B/FINAL_RESULT.json)
- [分数前实施与环境锁](https://github.com/ylrq8475-ui/Shiyou/blob/ca3e0560099a1f408fd0da7e847fbb59e3dac416/docs/handoff_20261012_A2B024_B/IMPLEMENTATION_PRETRAIN_LOCK.json)
- [原始R2计划](https://github.com/ylrq8475-ui/Shiyou/blob/ca3e0560099a1f408fd0da7e847fbb59e3dac416/docs/handoff_20261012_A2B024_B/PLAN_R2.json)
- [用户授权原文](USER_AUTHORIZATION.md)
- [匿名只读审计包](https://github.com/ylrq8475-ui/Shiyou/blob/ca3e0560099a1f408fd0da7e847fbb59e3dac416/docs/handoff_20261012_A2B024_B/A2B024_R2_B_ANONYMOUS_REVIEW_BUNDLE.zip)

审计包SHA256：`c26a1c87c0fdb4d96b4a3251aa13702ab7aeb258517edd2614029cf0d2393d50`。

本索引新增版本只修正网页可点击路径，不改变实验、成绩、门槛、审计包或既有13项材料。原研究目录README中的evidence/及授权相对路径是解压包内路径；GitHub顶层结果与锁的直接入口见上。本索引保留原材料，不覆盖旧版本。

审计包内运行 `python -B verify_evidence.py` 可只读复算。该入口不访问私有数据、不导入训练代码、不拟合。正式赛事提交包、私有配置、原始CSV及真实权重均未上传。
