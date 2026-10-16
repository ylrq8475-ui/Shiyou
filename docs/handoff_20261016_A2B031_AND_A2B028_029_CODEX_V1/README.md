# 账户A2：031合规前置判定与028/029补审

两份独立报告：REPORT_CODEX_031.md、REPORT_CODEX_028029.md；各自单一结果JSON同编号，索引分别追加。证据边界见EVIDENCE_NOTES_CODEX.md。

仅公开匿名聚合、方法和来源摘要，不含赛事CSV、私有配置、模型权重、逐井结果、官方PDF/图片或ZIP。

合成复核依赖numpy、pandas、PyYAML。按SOURCE_IDENTITY_CODEX和PROJECT_SOURCE_IDENTITY_CODEX的固定提交取得公开文件并保留sources路径。原始数据及权重均不需要。使用新目录运行：

```powershell
python -B run_synthetic_review.py
python -B audit_records.py
```

输出使用新文件，已有结果时不覆盖，另建目录。不要运行真实run_experiment.py、replay的执行分支、fm_worker或任何fit；本轮未授权这些操作。worker合成只使用伪tensor验证形状、分位数、桥接与批次，不加载预训练模型。

初始快照与最终登记补记版仅补入快照身份；判定、数据和方法不变。最终实际提交由交付固定链接、回取及handoff-index记录绑定。
