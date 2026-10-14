# 用户转交Codex：仅承接独立审核部分

账户B执行与交付｜A2B-026阶段0。

请以本目录RESULT_STAGE0.json和SOURCE_RECEIPT.json为B执行证据，按PROMPT_CODEX_ORIGINAL.md的12项必审清单给出“通过/失败/无法判断”和依据。该Prompt由Claude提供，本目录复制内容与用户转交的固定提交d031d38e0ce639601a1b926305d42e0d878aac6f逐字节一致。

Codex只负责审核，不重新读取赛事数据、不执行run_stage0.py、不训练、不改阈值或方案、不起草替代候选；不代替Claude决定下一步，也不直接联系B或Claude。若源代码/执行证据不足，标注无法判断，列明具体缺项。自己的审核材料按原Prompt单独匿名GitHub交付，交由用户协调。

B报告中的“自检通过”不是Codex已审核通过。请特别核对D4为有限261×801网格，两种标签神谕没有部署或选模；D2只在64口双锚点有限正值井上留一井比较。机械门槛必须按原DECISION字典确认。

原PRIVACY_SCAN.json失败与STOPPED.json完整保留：初次扫描误把执行源码中扫描器的两个无内容前缀常量识别成凭据。请查看PRIVACY_RECOVERY.json与PUBLICATION_PRIVACY_CHECK.json确认后续独立检查；没有重跑任何已成功诊断，也没有编辑原执行源码、计划或分数前锁。

GitHub发布项请按B实际完整提交号回取核对SHA256SUMS.json；本地B回取凭证在发布完成后单独提供，不由预发布文件伪造完成。

输出保持一页内：12项清单、关键数字、总审核结论及硬门禁。用户随后只把Codex审核结论和B关键数字转给Claude。
