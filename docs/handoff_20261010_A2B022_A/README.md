# A2B-022 账户 A 独立审计与交付

先读 REPORT_A.md，再读 COLLABORATION_REPLY_A.md。B 固定来源提交为 5867edc93916e4228791e3d20327ff48a960537d，来源目录 docs/handoff_20261010_A2B022_B。

结论：匿名聚合与停止决定通过；C1 没有提分信号，不升级。下一步优先核对目标表示实验是否已有同边界结果，不继续微调删列，不等官方回复才研究。

A_READONLY_CHECKS.json 是 A 独立执行 B 的只读入口；A_INDEPENDENT_ARITHMETIC_V2.json 是 A 自编核验。V2 将指标 oracle 从既有 A 脚本内联为独立函数，复算仍为 705 项通过；不改变口径或 B 证据，旧 V1 留在 A 本地。

复核工具不读取逐井 OOF 或进行拟合。要重现匿名检查，将固定 B ZIP 验证后解包到工具旁的 bundle 新目录，用 Python -E -B 运行 run_readonly_checks.py 和 independent_arithmetic.py。两个脚本均独占创建输出，已存在时须另建目录，不能覆盖证据。run_readonly_checks.py 的合成序列化测试只在 A 接收副本下创建并清理合成临时文件。

本交付不含赛事数据、私有配置内容、真实井号、逐井结果、模型或正式提交包。A 的报告 ZIP 仅用于审计，不是 result.zip/submission_code.zip。中文报告按 humanizer-zh 作自然化校对；项目审计 skill 用于同边界比较和证据范围区分，没有新增业务规则。
