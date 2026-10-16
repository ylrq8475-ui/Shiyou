# 零拟合复测入口

账户B执行与交付。环境版本见ENVIRONMENT_LOCK.json；仅pandas/numpy/PyYAML及标准库，不导入模型库，不加载权重。

```text
python -m unittest -v test_audit.py
python run_audit.py --archive <原赛事ZIP> --manifest <冻结逐文件清单JSON> --config <冻结私有配置YAML> --template-receipt <既有READONLY_INPUT_READY.json> --scoring-source <冻结工程src/oil_uplift/scoring.py> --output <不存在的新目录>
```

必须具有目标机器与AI环境的数据读取授权。私有文件不在GitHub；缺少时只核对脚本、合成和聚合，不能替代真实复算。

脚本先写分数前身份/读取锁；原包100项SHA逐一校验，不解压。WELL_ID与NY原序哈希用于验证恢复的模板键，不读取测试目标空值。未通过键哈希立即停止，不能改用RCYL筛选。原始数据仅从ZIP内存读取，测试窗口内动态列永远不解码。读取账本仅总计，禁止添加逐井日志。

冻结scoring.py仅提供无拟合的官方指标核对；用其相邻源码包oil_uplift及exceptions.py满足导入。真实P1/P2/P3与该指标差都应为0（容差1e-12）；不要运行其他训练入口。

PLAN_R9先于本次计数与分数；P3仅在ALIGN_MATCH为否时运行，不能通过P3结果更改定义。复测输出只允许匿名聚合，新目录不覆盖旧成果。无全量训练、预测包或平台操作。
