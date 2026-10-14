# A2B-026阶段0：B零拟合诊断交付

账户B执行与交付｜2026-10-14｜待Codex独立审核。

Claude负责方案与指令，Codex仅负责审核，B负责执行与交付；用户是唯一协调人。旧账户署名只用于追溯历史。

- [B结果与自检报告](REPORT_B.md)
- [关键数字与机械判定](RESULT_STAGE0.json)
- [用户转给Codex的交接说明](HANDOFF_TO_CODEX.md)
- [Codex原12项必审Prompt](PROMPT_CODEX_ORIGINAL.md)
- [三账户分工规则](THREE_ACCOUNT_ROLE_RULES_V2.md)
- [分数前锁](PRE_DIAGNOSTIC_LOCK.json)、[固定来源](SOURCE_RECEIPT.json)、[拟合计数与事件](EVENTS.json)
- [公开材料隐私扫描](PUBLICATION_PRIVACY_CHECK.json)、[SHA256清单](SHA256SUMS.json)

只读合成复测：在独立副本中运行 `python -E -B -m unittest test_diagnostics_reference`。这只能核验12项虚构数据测试，不能独立复算真实81井的诊断。

run_stage0.py为实际B执行源码供静态审查；它依赖获授权本地工程与数据。Codex不运行真实入口，不训练、不修改方案。新模型、阶段1训练、正式打包及平台提交均0。
