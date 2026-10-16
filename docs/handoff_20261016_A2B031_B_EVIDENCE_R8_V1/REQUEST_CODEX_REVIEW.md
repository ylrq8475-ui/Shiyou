# 同编号复核请求（由用户转交）

账户B执行与交付。依据 [R8原文](https://github.com/ylrq8475-ui/Shiyou/blob/252d421d4396c5e4119f03c772be239a9cdd1b7e/docs/handoff_20261016_A2B031_CLAUDE_INSTRUCTIONS_R8/INSTRUCTION_ORIGINAL.md) 的②，请对 A031-Q1-AVAILABILITY / A031-Q2-AVAILABILITY 同编号复核。只做您负责的独立合规核对，不替B训练，也不替Claude改方案。

请独立核对E1官方来源与原句、E2字段语义和建议白名单、E3四项条件/独立失败数/严格交集、E4当前同源与历史版本的区别，以及逐文件隐私证据。B自报N_Q2_all=0；不请求将条件放宽为“完工月不晚于事件末月”。

若Q1放行，给出最终静态字段白名单；若Q2放行，条件不得宽于R8 E3全部条件，给出确有事前设计依据的字段白名单。B建议的13项层位字段是属性推断，官方并未逐项确认历史时点。WELL_ID/XH是已知含义元数据，逐项排除而不伪称含义不明；请核验此展示处理。SFSBHD按束缚水物性提出，官方没有形成时点声明，请核验其版本适用性。

请发布独立登记卡及单JSON结果到新Codex目录，reviews_commit填写本次B最终提交，并追加handoff-index。UNKNOWN仍按不允许执行；资源到位和本补证完成不等于实验启动。只有独立复核放行后，B才依R7及最终白名单继续。历史dtype与业务解释不冒充已关闭。
