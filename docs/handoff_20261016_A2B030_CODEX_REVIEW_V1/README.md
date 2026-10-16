# 账户A2：A2B-030 R6零拟合独立审核

先读REPORT_CODEX.md，证据边界见EVIDENCE_NOTES_CODEX.md，机器结果为RESULT_CODEX.json。

只包含匿名聚合、方法及来源摘要；没有赛事CSV、私有配置、模型权重或逐井结果，不含ZIP。

纯合成复核需numpy、pandas、PyYAML。按SOURCE_IDENTITY_CODEX.json的固定40位提交/路径取得公开方法与聚合文件，保持sources/B030、sources/shared_R5、sources/instructions分组路径。不得运行真实run_experiment.py或隐私扫描main；它们需要私有输入或会训练。可在新的A目录运行：

```powershell
python -B run_synthetic_review.py
python -B audit_records.py
```

两个入口输出使用新文件，不覆盖既有检查记录；已存在结果时请另建工作目录。合成prepare仅用人工井、人工月份、人工数值，真实B入口未执行。

本包的初始审核快照与登记补记版仅增加快照身份，数字、方法和结论不变。最终实际提交由用户收到的固定链接、回取验证和handoff-index末尾记录绑定。
