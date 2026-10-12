# A2B-023 账户 A 独立审计与交付

复核日期 2026-10-12；B 交付固定提交 4ea326798ca1da0736cde4bc41f33b7ff8b58cf9，实验执行于 2026-10-10。

先读 REPORT_A.md、COLLABORATION_REPLY_A.md，再读 NEXT_STEP_PROPOSAL.md。结论是整体绝对 log 候选失败停止，但回退组正信号值得优先验证固定状态路由。不能把 A_ROUTE_SIGNAL.json 中的事后算术当成新候选已验证的分数。

只读入口 27 合成/759 聚合通过；A 自编 696 检查通过，A 无真实训练。身份绑定、B 远端声明与 A 实际验证范围在报告中分开。

复现匿名检查：固定 B 复测 ZIP 验证后解包到工具旁的 bundle 新目录，用 Python -E -B 依次运行 run_readonly_checks.py、independent_arithmetic.py、derive_route_signal.py。脚本独占创建报告；已有输出时新建目录，不覆盖原证据。A 首次聚合运行因 B 摘要字段名变化停止，未产生结果文件；改为从六组原始聚合数组计算后通过，没有改变统计口径或重训。

交付不含赛事数据、私有配置内容、真实井号、逐井结果、模型权重或凭据。审计 ZIP 不是正式赛事提交包。项目审计 skill 用于同边界比较、因果和事后解释边界；中文报告经 humanizer-zh 自然化校对，未改变事实或规则。
