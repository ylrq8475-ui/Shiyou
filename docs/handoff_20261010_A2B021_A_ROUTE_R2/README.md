# A2B-021 账户 A 收尾与路线补充

账户 A 独立审计与交付，2026-10-10。

最新 B 提交是接收收尾，新增训练 0 次。A 核对收尾身份与接收记录后，复算了误差组的井数分母，并审查下一阶段研究方向。

- [路线评判](ROUTE_REVIEW_A.md)
- [给 B 的协作回复](COLLABORATION_REPLY_A.md)
- [下一项只读诊断建议规格](NEXT_DIAGNOSTIC_SPEC.md)
- [匿名独立复核证据](ROUTE_REVIEW_EVIDENCE.json)
- [完整匿名交付包](A2B021_A_ROUTE_REVIEW_20261010_R2.zip)
- [交付清单](PUBLICATION_MANIFEST.json)

主要判断：训练输入诊断可作为下一项有限任务，但特征数量、叶支持和损失份额都不足以确认最大误差源。普通组损失占比 60.74% 与其井数占比 61.73% 接近；该分母补充限制了上一轮优先级建议的解释范围。反复使用同批 OOF 的选择偏差需要在下一计划中明确记录。

本次不重跑已验收测试、不训练模型、不改变既有停止决定。事件语义和预测生成时点 P0、历史 dtype UNKNOWN 继续保留。此交付不授权新训练、升级或赛事提交。

受检 [B 收尾固定提交](https://github.com/ylrq8475-ui/Shiyou/tree/2c677b28a9060874b872716bab3b389ae4f2dd7f/docs/handoff_20261010_A2B021_B_CLOSEOUT)；此前 [A 完整实验复核](https://github.com/ylrq8475-ui/Shiyou/tree/13e25c5ee43ef9a3e5f7498c8969867d6388c89f/docs/handoff_20261010_A2B021_A)。原材料保持原样，本补充在新目录和分支发布。
