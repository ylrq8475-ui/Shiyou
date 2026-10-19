# A2B-033 Codex独立审核

账户A2（新接手）独立审核与交付，2026-10-19，Asia/Shanghai。

REPORT_CODEX.md为正式回函，RESULT_CODEX.json为单一机器结果；EVIDENCE_NOTES_CODEX.md说明真实执行记录、独立合成及聚合复算的区别。B对象固定为e846e2094ced5a71e3550294a15432388664cd5a，依据R10和既有T4，不重训、不更改门槛或目标。

结论：总OOF增量+2.618511，但仅3/5折改善，应维持弱信号停止。没有进入步骤2，没有本轮完整提交包可进入上传批准。不是判定已存在的ZIP格式失败，也不要求B现在补包。未更新平台成绩或指定最终模型。

## 公开材料及纯合成复核

在新的账户A审计目录保存本交付，然后运行：

```text
python -X utf8 -B hydrate_public_sources.py
python -X utf8 -B run_synthetic_review.py
python -X utf8 -B audit_records.py
```

hydrate只下载51份固定提交的公开匿名方法/聚合文本，核验原字节SHA256及Git blob；并验证解码10个已公开原模块。公共网络读取最多重试两次；已有缓存仅在字节身份相同时复用，不覆盖。这不是任何模型拟合重试。它不取得赛事原始CSV、私有配置、模型或逐井结果。测试依赖与B requirements.txt相同，本轮本机Python3.13.7、numpy2.4.3、pandas2.3.3、scikit-learn1.9.1。

新输出写入verification_output/，排他创建；不能覆盖既有证据或重复运行真实OOF。没有调用B的run_oof.py、train.py或predict.py的真实入口。B的测试导入预备源码，实际sklearn拟合入口被守卫阻断；计数器使用空回调/合成替身不是模型训练。

若本机无法直连公开raw主机，可将通过GitHub读取工具取得、按本清单固定提交和原字节校验的公开文本放入缓存，执行`hydrate_public_sources.py --public-cache <公开缓存sources目录>`；仍逐项校验SHA256和Git blob，不接受原始数据或私有配置。A本次另在新工作目录复测使用此公开字节缓存、同一受检解释器，不冒称B的模型包干净环境复现。

公开文件逐项扫描见PRIVACY_SCAN_CODEX.json。SOURCE_IDENTITY_CODEX.json与BASELINE_SOURCE_IDENTITY_CODEX.json只含公开方法和聚合文本的身份，不上传原始清单、候选原值、模型、预测包或私有策略。

Git作者与提交者标注Account A2 - Successor Independent Audit，仅代表逻辑审核角色；不冒称另一个GitHub登录身份或签名。登记卡明确初始结果快照与最终发布提交的区别；最终固定链接和索引绑定实际交付。清单自身由Git blob及回取证据绑定，不伪造循环摘要。
