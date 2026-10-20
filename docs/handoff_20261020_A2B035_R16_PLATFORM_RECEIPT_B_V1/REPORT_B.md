【交付登记卡】

|字段|内容|
|---|---|
|任务编号/阶段|A2B-035/R16 两已审完整版本平台回执补充与台账|
|角色|账户B执行与交付|
|分支|codex/a2b035-r16-b-20261020|
|完整提交号（40位）|d88142539fbc2407e67dae0e61de0379c3b55cae（单一结果快照；最终附件提交由索引绑定）|
|目录路径|docs/handoff_20261020_A2B035_R16_PLATFORM_RECEIPT_B_V1|
|结果文件路径（单个JSON）|docs/handoff_20261020_A2B035_R16_PLATFORM_RECEIPT_B_V1/RESULT_PLATFORM_RECEIPT16.json|
|所依据Claude指令存档|441966be673da9083505168077a4d6ac63805e90（R16）；ee2fa7a97530b57cc4a0aaa2a0bfd22530ed3937（R13）；0f2804776957cefa6c3bab573a403f0cfb86d33e（R14）；9482ad9bb2a0bc64519e6a9effc8adbfee14173a（R15）|
|所依据Codex复核|b299828899812d2921e5a1da0ea865bf97b4beb5，两完整包已审可交用户手动评测；本次新增平台回执绑定待Codex判定|
|关键数字|用户报B0=86.2003、B0+W=80.8854，W−B0=−5.3149；本机四ZIP哈希复核4/4通过；两结果ZIP各10文件120行；本次模型/预处理拟合0/0；B平台上传0|
|硬门禁结论|泄漏/错位/井级隔离/指标：继承Codex已审两完整版本范围通过。本次仅记分、算术与本机文件只读检查，不重新评估或训练|
|UNKNOWN与未关闭项|提交编号、提交时间和状态UNKNOWN；平台报分未由B直接获取。PLATFORM-B0-BINDING已由Codex在9cc17638b8743131d6595e8671f7b7051f8b2686关闭，限当前实际上传B0包→用户报分86.2003；历史原上传包字节UNKNOWN；HIST-DTYPE P1继承用户例外，不回填|
|对应决策表行|B不填写独立审核行；已接收Codex实际关闭判定9cc17638b8743131d6595e8671f7b7051f8b2686，不自动最终指定|

**发布前新增接收：** Codex已在[固定复核](https://github.com/ylrq8475-ui/Shiyou/blob/9cc17638b8743131d6595e8671f7b7051f8b2686/docs/handoff_20261020_A2B035_R16_PLATFORM_CODEX_V1/REPORT_CODEX.md)关闭PLATFORM-B0-BINDING，范围限“当前R16实际上传B0包→用户报告86.2003”。B已逐项核对四哈希、分数和S_v并记入私有台账V3；提交编号/时间/状态仍UNKNOWN。主结果JSON保留先前单一结果快照原字节，其中待Codex状态由CODEX_PLATFORM_CLOSURE_RECEIVED.json这份后续接收记录明确更新；不回写快照或冒称B自行关闭。下文待审措辞对应原快照时的已知状态。

用户本轮转交Claude对“实际上传文件”的只读SHA256核对，原文保存在USER_FORWARDED_RECEIPT.md。B0使用上传名submission_code3.zip/result3.zip，B0+W使用submission_code4.zip/result4.zip。四个摘要与既有B交付、Codex已审摘要及本机重新计算完全匹配。重命名不改变ZIP原字节。B另在现有本机结果ZIP上只读核对：各10份CSV、120行，每文件12行、列名WELL_ID/NY/RCYL、键无重复、数值有限非负、ZIP完整性通过；未写逐井行或预测。

|完整版本|用户报告A榜|匹配版本重复CV均值|按报分与上传文件SHA回执计算的S_v|
|---|---:|---:|---:|
|B0重建|86.2003|72.47647400484871|79.338387002424355|
|B0+W|80.8854|72.6793269415761|76.78236347078805|

R13公式为S_v=0.5×A榜+0.5×重复CV均值。W相对B0的报分差−5.3149、重复CV差约+0.202853、S_v差约−2.556024。此两完整版本中B0排序较高。分数证据仍为用户报告；实际上传文件SHA依据用户转交Claude只读核验，B已与本机原字节比对，不宣称B独立登录平台核验分数、提交时间或历史日志。

按分数前锁定的四位小数规则，登记“历史 86.2003 与 B0 预测一致”。本次证据具体关联当前实际上传B0包与86.2003；不把同分扩写成历史原始上传ZIP逐字节同一，也不证明官方边界语义。用户要求Codex据此关闭PLATFORM-B0-BINDING，B只提交证据并保留待Codex判定。没有提交编号、时间、状态则原样保留UNKNOWN，不以记录时间替代提交时间。

W在本地重复CV略有改善而平台报分下降，是观察到的差异；本对比不能识别降分的单一因果机制，不据此更改预测、追加候选或自动最终指定。R16默认TabPFN及融合继续原授权，本次不改变其参数、环境、预算和期限，不重训、不重推、不打包、不上传平台。

原台账及上一份仅报分的私有版本原字节均保留，新私有V2只追加两条回执记录。前一份仅报分的匿名草稿在用户补证前未发布，原样留存本机；GitHub只发布本次完整补充版。不发布正式ZIP、权重、私有配置、真实井号、月份、原值、逐井标签或预测。

固定来源：[R16指令](https://github.com/ylrq8475-ui/Shiyou/blob/441966be673da9083505168077a4d6ac63805e90/docs/handoff_20261020_A2B035_CLAUDE_INSTRUCTIONS_R16/INSTRUCTION_ORIGINAL.md)、[两完整包复核](https://github.com/ylrq8475-ui/Shiyou/blob/b299828899812d2921e5a1da0ea865bf97b4beb5/docs/handoff_20261020_A2B035_R16_CODEX_V1/REPORT_CODEX.md)、[既有重复CV与包来源](https://github.com/ylrq8475-ui/Shiyou/blob/42a5c66406f56af86520c3d65eb71d1fbb616fea/docs/handoff_20261020_A2B035_R15_CLOSEOUT_B_V1/RESULT_R15_CLOSEOUT.json)、[原B包回执交付](https://github.com/ylrq8475-ui/Shiyou/tree/6ab552ef1cb007b13f0bc350957b7b82037f1348/docs/handoff_20261020_A2B035_R16_FIRST_B_V2)。
