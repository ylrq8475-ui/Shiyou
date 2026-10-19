# A2B-035管线问题清单

## CODEX-035-PIPELINE — P1 — 已关闭，限本版内部ET范围

对象：B提交4fbe466d0ca7a7cbcd9d1639e2a200f20e1de47b，PIPELINE_LOCK SHA ce1ab047d126f2586993dc8d2b05aef5f1b9871c59b626d6927d8803904713d1。

关闭依据：442项来源/回执/聚合复算、32项源码级合成测试，固定双基准误差0；具体范围及未重新训练的证据限制见REPORT_CODEX.md。仅放行内部ET、多输出ET及其等权或内层融合，base325/base325_R；不是外部/G准入、不是最终提交审核。

## EXT-035 — P1 — UNKNOWN，禁用分支

位置：models035.py::resource_gate/estimator_for、RESOURCE_RELEASES.json；Chronos未实现。

缺口：实际许可证/署名、外部权重版本及SHA、离线与真实适配器独立性证据。不得以ET合成结果代替TabPFN或零样本模型验收。

影响：仅外部分支。修复/验证：按R13提供真实资源及专项测试记录；共用代码改变时重新绑定代码审核。未启用分支不阻断内部ET。

## G-031 — P1 — UNKNOWN，禁用分支

位置：guard035.py::history_features，GEOLOGY_DISABLED_PENDING_ACTUAL_CODEX_Q1_WHITELIST。

缺口：实际Q1字段白名单及可用性放行。当前硬阻断有效，不因R13列出G选项自动允许。

## PLATFORM-035-PROVENANCE — P2 — 待澄清

位置：PLATFORM_LEDGER_PUBLIC.json，第二条uploaded_*与packet_identity_source、exact_uploaded_config_binding字段。

问题：两个SHA与审核包一致，但A提供的是仅供核对的参考SHA，不能因此确认实际上传身份。B如有另一会话明确实际上传声明或回执，应补来源定位；否则改为reviewed_artifact参考，uploaded_*继续UNKNOWN。

影响：平台台账可信度及后续S_v版本选择；不影响共用管线和双基准，当前S_v为UNKNOWN的处理正确。

建议验证：核对原始用户措辞或提交回执与实际两个ZIP摘要；保留真实来源级别，不把同SHA当平台回取证据；不为补台账训练。

## ENV-035-RUNTIME — P2 — 后续运行记录要求

位置：guard035.py::verify_source_lock、ENVIRONMENT_LOCK.json，未来各版本实际运行记录。

问题：锁文件字节一致不自动证明当前解释器/安装包与锁一致。本轮STARTED及环境记录相互绑定且基准精确复现，无现存基准失败证据。

建议：后续运行保留实际环境摘要，变更依赖/外部模型环境时不混用旧折；最终包核验真实环境。非当前ET放行阻断项。

## HIST-DTYPE — P1 — UNKNOWN，继承既有用户例外

历史加载身份链不回填；本次新特征/类型/行序指纹是当前证据，不是历史摘要。
