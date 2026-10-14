【交付登记卡】  
任务编号/阶段：A2B-026／阶段0收尾＋路线B预注册定稿R2（B-2未启动）  
角色：B 交付  
分支：codex/a2b026-b-closeout-route-b-r2-20261014  
完整提交号（40 位）：0f4f2295f971fb3d9ff82f31bb5eb2e5b74889f9（结果固定快照；最终发布提交另见回取凭证）  
目录路径：docs/handoff_20261014_A2B026_B_CLOSEOUT_ROUTE_B_R2  
结果文件路径（单个 JSON）：docs/handoff_20261014_A2B026_B_CLOSEOUT_ROUTE_B_R2/RESULT_B.json  
关键数字（按决策表变量逐项列出，变量名与决策表一致）：OOF 分数差：UNKNOWN；分数差：UNKNOWN（同一变量，B-2未执行）；原参考基线73.71410733861434；发布24／历史扫描21／遗漏3／补扫24通过；模型拟合0；预处理拟合0  
硬门禁结论：泄漏：通过／错位：通过／井级隔离：通过／指标：通过（仅继承阶段0有限审核；未来B-2四项均UNKNOWN）  
UNKNOWN 与未关闭项：STAGE0-11，P2，缺Codex对追加覆盖证据的独立签署；B2-IMPLEMENTATION，P1，未来train.py及四项运行门禁未实施，阻断B-2；B-2尚无另行用户批准  
对应决策表行（仅 Codex 填写；B 写"不适用"）：不适用

# A2B-026 阶段0收尾与路线B预注册R2

账户B执行与交付。本轮完成已有成果核对和缺项修订，模型拟合0次、预处理拟合0次。路线A不执行阶段1；路线B只完成B-1，B-2尚未获单独启动批准。本文件不替代独立Codex审查。

旧交付已有24份逐文件补扫，全部通过；历史21份仅有聚合记录，选择集合依据扫描时写入顺序重建，不冒充原始逐文件日志。遗漏文件为PRIVACY_RECOVERY.json、PUBLICATION_PRIVACY_CHECK.json、SHA256SUMS.json，均已覆盖；没有扫描豁免。本R2复用已完成的原始输出并逐字核对绑定，不重复原诊断。

最新要求的缺项已经补齐：新B专用分支与统一版本目录、REPORT_B首部登记卡、用户最新四行决策表原文、单个结果JSON和明确计数记录。另发现旧预注册阈值网格偏离原路线B定义，现恢复τ=(1−ℓ+)/(2−ℓ+)；ℓ+仅由内层验证折的正值损失估计，不用整体OOF或外层OOF选阈值。

精确零标签、模型全部参数、325列截止M−1、原五折及seed 20260916已写入PREREG_ROUTE_B.md和PREREG_PARAMETERS.json。维持同折B0非置零输出逐值不变，并纳入误置零成本。未来B-2建议预算25模型拟合、20预处理拟合，仍须用户另行批准；本轮一律0。

全部新增文件位于本R2目录。f482原24文件、0f4f已发布补充文件和旧计划保留原字节，不覆盖模型、配置、原数据或正式ZIP。发表前对本目录每份文件检查隐私并记录字节SHA；发表后回取验证实际Git字节及只新增文件的差异。

来源：[原阶段0](https://github.com/ylrq8475-ui/Shiyou/blob/f482b55d403b8cd36e1a6e30d46a4c976b11baf4/docs/handoff_20261014_A2B026_B_STAGE0_V1/REPORT_B.md)；[独立Codex阶段0报告](https://github.com/ylrq8475-ui/Shiyou/blob/5fabbd4eaff275ce4997c70fd0abaa9f168f6edc/docs/handoff_20261014_A2B026_CODEX_STAGE0_REVIEW_V1/REPORT_CODEX.md)；[路线B原定义](https://github.com/ylrq8475-ui/Shiyou/blob/3256382fb56efecf37f54b4ce3bd4287ffe1f71c/docs/handoff_20261013_95PLUS_DIRECTION_RESEARCH_V1/RESEARCH_DIRECTION_REVIEW.md)；[Prompt V2登记规则](https://github.com/ylrq8475-ui/Shiyou/blob/48642f2d9e1d0e05cfbb7c42d905f18f366f811e/docs/handoff_20261014_THREE_ACCOUNT_PROMPTS_V2/DELIVERY_REGISTRATION_RULES.md)。

## 请用户转交Codex的限定审核请求

请只审核本R2追加交付：24文件/21历史声明的对应与重建等级、遗漏3文件的原始补扫及哈希绑定、新目录完整性和隐私覆盖、预注册与3256382原定义及本次用户决策表是否一致。逐项给出第11项PASS/FAIL/UNKNOWN，并在独立报告首部按V2登记卡填写自身提交与被审B提交。

Codex只负责独立审查，不接替B实现或训练，不修改Claude方案、不选新候选、不提交平台。本轮不要求真实训练复现；B-2尚未产生新分数，不能填写收益决策行。审核结束由用户转交Claude作下一步判断。第11项须经Codex判为“通过”，且用户另行批准B-2，之后方可启动B-2；其他实际结构门禁仍须在评分前满足。

没有官方唯一解释本身不列为阻塞P0。当前锚点、特征截止和目标窗口不因此自动改变；实际泄漏、目标错位、井级隔离与官方指标仍是硬门禁。历史dtype身份缺口仍UNKNOWN，不以本次文档补造历史证据。
