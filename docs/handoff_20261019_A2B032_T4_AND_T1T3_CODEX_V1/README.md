# A2B-032：T4判定与T1–T3独立审核

账户A2（新接手）独立审核与交付，2026-10-19，Asia/Shanghai。

- REPORT_CODEX_T4.md / RESULT_CODEX_T4.json：规则判定，无被审B对象，reviews_commit为不适用。
- REPORT_CODEX_T1T3.md / RESULT_CODEX_T1T3.json：实际覆盖B最终提交094ebcd2b6b323849fce9c5cb1daf3e6b9228b41。
- SOURCE_IDENTITY_CODEX.json、OFFICIAL_SOURCE_VERIFICATION_CODEX.json、AGGREGATE_REVIEW_CODEX.json：公开来源、官方来源及聚合核对。
- SYNTHETIC_RESULT_CODEX_R2.json / SYNTHETIC_LOG_CODEX_R2.txt：35项纯合成测试，原始赛事数据读取和拟合均0。
- AUDIT_QUEUE.md：当轮问题与范围；EVIDENCE_NOTES_CODEX.md：证据等级和限制。

T4有条件允许同井合法模板前历史至T0−1，并不允许窗口内字段或训练。T1–T3按锁定表第一行处理；ALIGN_MATCH为否不能单独证明真实目标错位。没有新的模型或平台分数，不追认旧研究通过。

## 仅复核公开材料和合成的操作

将本目录保存到新的独立审计目录，不在B工程内运行。先执行hydrate_public_sources.py，它只按固定提交回取27份公开匿名文本、核对SHA256和Git blob，并保存到本目录sources；不读取赛事数据。然后运行：

```text
python -X utf8 -B run_synthetic.py
python -X utf8 -B audit_aggregate_records.py
```

新输出写入verification_output/并使用排他新建，不与随包交付的既有报告冲突；若已经运行过，改在新的审计目录复核，不覆盖已有证据。不运行B的run_audit.py真实入口或privacy_check.py私有入口。需要numpy和pandas；本轮复测使用Python 3.13.7、numpy 2.4.3、pandas 2.3.3。此流程不是逐井真实结果复算。

公开材料逐项扫描结果见PRIVACY_SCAN_CODEX.json。没有原始数据、私有配置、真实井号或逐井结果、权重；不转载B的真实结果包。Git author/committer为Account A2 - Successor Independent Audit，仅标注逻辑审核角色；不冒称使用另一个GitHub登录账户或签名认证。

登记卡标明首个结果快照；最终登记版由固定报告链接及handoff-index条目绑定，两者不混同。清单不自包含循环摘要，清单自身由固定Git blob和外部回取凭证绑定。
