【交付登记卡】

|字段|内容|
|---|---|
|任务编号/阶段|A2B-035/R17 B0实际上传包提前审核二材料|
|角色|账户B执行与交付|
|分支|codex/a2b035-r17-b-20261020|
|完整提交号（40位）|b038bd2eef9d87cca80adefd74bf793590e61d55（单一结果快照；完整附件提交由索引绑定）|
|目录路径|docs/handoff_20261020_A2B035_R17_B0_AUDITII_B_V1|
|结果文件路径（单个JSON）|docs/handoff_20261020_A2B035_R17_B0_AUDITII_B_V1/RESULT_B0_AUDITII17.json|
|所依据Claude指令存档提交号|7f44d70aa53410a2d072d69874003f3a8946adbb（R17）；不冲突的R13–R16继续有效|
|所依据Codex签署|b299828899812d2921e5a1da0ea865bf97b4beb5（R16两包/Native增量）；9cc17638b8743131d6595e8671f7b7051f8b2686（当前上传B0包→86.2003关闭）；共用核心3001037a7d465117fd8062e5cbc6b2d168575fef|
|关键数字|B0 A榜86.2003（用户报）；本次新从头复现模型/预处理1/1，ZIP逐字节一致；10文件120行；B平台上传0|
|硬门禁结论|泄漏/错位/井级隔离/指标：继承已审源码并在本轮真实复现、边界合成和linter范围通过（B自报）；审核二待Codex|
|UNKNOWN与未关闭项|审核二P1：等Codex判定最终包是否可指定；平台编号/时间/状态UNKNOWN；历史dtype P1用户例外仍未关闭|
|对应决策表行|仅Codex填写；B不自行认定最终包可指定或融合包可上传|

对象为用户实际上传的B0重建包，code SHA a75ce0e1820001ef2e854a0cee6540a04caa5b1ecadec3d3c433f30ab42e420a，result SHA 2b4f57169d653d0ca5fc994d2822f6e167e72c5696a1220f83f7c1eaac4a1df1。两包原字节保持，未重新打包。

本次新建R17隔离目录，复制已审21依赖环境并核验新prefix、Python3.13.7及实际全版本，再从实际code ZIP新解压运行train.py --config variant.json，从官方原始训练数据新拟合1次，不读包内模型；predict明确指向新工件。复现result.zip逐字节等于实际上传参考，linter为10文件120行、WELL_ID/NY/RCYL、无重复键及非有限负数、模板键和日期文本原样，CRC通过。绑定回执、新旧模型摘要、环境、命令阶段时长及源码身份均随包供只读复核，原始行和私有路径不发布。

原已审的主训/独立复训1+1回执作为来源参照保留，本次新增审核二从头复现另计1次，不重复冒算旧拟合，也不掩盖新增。新边界合成使用与正式B0代码相同字节的base源；固定两档融合测试只是测试工具附属，不把融合候选误作B0。

全部其他搜索已按R17停止（含默认Tab，首折验证未完成）；42项Native结果保留。原R16跟进已暂停，旧heartbeat不再授权恢复研究。本B0终审材料独立冻结，不等F70/F50是否通过。B0“当前最终候选”不是B代替用户完成平台最终指定；Codex需独立输出“B0最终包是否可指定：是/否”。

固定来源：[R17原文](https://github.com/ylrq8475-ui/Shiyou/blob/7f44d70aa53410a2d072d69874003f3a8946adbb/docs/handoff_20261020_A2B035_CLAUDE_INSTRUCTIONS_R17/INSTRUCTION_ORIGINAL.md)、[两包已审](https://github.com/ylrq8475-ui/Shiyou/blob/b299828899812d2921e5a1da0ea865bf97b4beb5/docs/handoff_20261020_A2B035_R16_CODEX_V1/REPORT_CODEX.md)、[绑定关闭](https://github.com/ylrq8475-ui/Shiyou/blob/9cc17638b8743131d6595e8671f7b7051f8b2686/docs/handoff_20261020_A2B035_R16_PLATFORM_CODEX_V1/REPORT_CODEX.md)。
