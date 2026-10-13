# 可直接发送给新账户A的审核Prompt

你是本项目新接手的独立审核账户A。此前A账户额度耗尽/更换，账户B仍负责训练执行；身份不交换。请从固定GitHub证据恢复上下文，不依赖旧聊天，完成最新平台探索部署及成绩来源的独立只读审核，并匿名交付。不要从头重做已结束实验，也不要仅回复收悉。

我授权你读取公开匿名材料，编写并运行独立聚合算术、源码检查与纯合成测试，完成后把匿名审计材料发布到 https://github.com/ylrq8475-ui/Shiyou。常规只读核验、必要实现及匿名交付无需逐项再次申请。本轮不授权真实模型或预处理拟合、候选搜索、改B冻结成果、模型升级、重新打正式包或平台提交。原始数据、私有配置和权重无需传输；另一机器的旧授权不自动构成本机私有材料访问授权。

一、阅读次序与固定来源

先读本Prompt同目录README.md、PLATFORM_SCORE_REPORT_B.json、SOURCE_AND_SCOPE.json及SHA256SUMS.json，记录本目录实际完整提交号。该目录是B交接，不是A审核结论。

1. 最新探索部署：提交519b00da7dc29bae0448c797ee2e74e3e3cc35b3，目录docs/handoff_20261012_A2B024_R1_PLATFORM_EXPLORE_B_V1。读README.md、REPORT_B.md、USER_AUTHORIZATION.md、AUTHORIZATION_SELECTION.json、DEPLOYMENT_PLAN.json、DEPLOYMENT_ACCEPTANCE_B.json、DEPLOYMENT_DEBUG_LOG.json、MODEL_REGISTRY.json、FORMAT_RULES_CHECK.json、STANDALONE_ACCESS_AUDIT.json、SYNTHETIC_RESULTS.json、UPLOAD_SHA256SUMS.json。
https://github.com/ylrq8475-ui/Shiyou/tree/519b00da7dc29bae0448c797ee2e74e3e3cc35b3/docs/handoff_20261012_A2B024_R1_PLATFORM_EXPLORE_B_V1
匿名只读包ANONYMOUS_REVIEW_BUNDLE.zip的SHA256为c7415aece02ea6cc360121f7498dd728d077bf71433aaee50937bbe89a499e4d。先核对外层与包内清单，只执行纯合成入口；匿名包不含真实模型，不能声称它可独立生成真实预测。

2. 完整前史接手包：提交e71c3e17e1c411ee0144d89a50ea394352c21f66，目录docs/handoff_20261012_A_SUCCESSOR_ONBOARDING_B_V1。读README.md、CONTEXT_AND_HISTORY.md、SOURCE_PROVENANCE.json、GITHUB_DELIVERY_RULES_A_V1.md。历史Prompt只作背景，后续授权和本次成绩记录优先，不照抄过期状态。
https://github.com/ylrq8475-ui/Shiyou/tree/e71c3e17e1c411ee0144d89a50ea394352c21f66/docs/handoff_20261012_A_SUCCESSOR_ONBOARDING_B_V1

3. A024原研究：提交65115714d49d17122989195910b119264bd93880，目录docs/handoff_20261012_A2B024_B，读REPORT_B.md、PLAN_R2.json、FINAL_RESULT.json、EXECUTION_SUPPLEMENT.json、MODEL_REGISTRY.json。
4. 上一接手A的实际有限只读复核：提交3b38c63514f6da6ef9469da54030c1eac40e1abd，目录docs/handoff_20261012_A2B024_A_SUCCESSOR_REVIEW_v1，读REPORT_A.md及COLLABORATION_REPLY_A.md。它复核原研究失败停止，不是后来部署的签署，也没有真实重训。

二、最新成绩的证据等级

用户于2026-10-13本轮消息报告“当前最新结果86.2003”。请将86.2003登记为用户报告的最新平台成绩，不能写成本地OOF、独立验证成绩或已证明提分。

早先用户也报告过86.2003。两次数值相同不能证明包相同、模型相同、预测相同或新模型优于旧模型；也不能把新报分自动合并成旧记录。当前缺少平台提交编号、实际提交时间、评测记录及实际上传ZIP哈希的独立绑定。对应本轮B交付包的预期身份为：
- result.zip：e41463cac0ec58827f240293a6a35385b27745a3354197efdcfa3d78ad72f796。
- submission_code.zip：540ace087ed37affc57a2d08774e163de4a14f0dec7f671c1a659f9bab7046eb。

这些摘要标识B交付文件，不等于平台已证明接收的文件。缺记录时保留UNVERIFIED，先完成其他审核，不把分数来源未独立核验当作停止全部工作的理由。只列必要的提交元数据缺项，不要求原始数据或私有内容。2026-10-12报告的“B未上传/未见成绩”是当时状态，与本次用户报分按时间分别记录，不伪改旧报告。

三、必须区分原研究与探索部署

原A024 R2：研究60次拟合后五组平均增量+0.478483932139153、5/5正向。条件确认种子20271012再10次，总增量+0.046032970630236036未达到+0.20，前两月增量−0.011988860385711564未达到0，按原计划FAILED并停止，原阶段全量保存0。平台86.2003不能追认这些门槛通过。

随后用户明确免除等待A的前置要求并选择“R1探索”，另行授权固定双臂全量训练、私有保存、部署验收与正式本地包。B记录新增模型/预处理各2次，B0/C1各全量一次，CV重跑0，新增候选0，拟合失败/重试0，旧模型未替换。这是单独探索用途授权，不是绕写原研究PASS。审核授权与工件阶段是否分开；不要把旧计划的停止规则误读为用户永远不能另行授权探索，也不要将探索授权扩展为模型升级或平台上传。

R1固定整井路由：原始last RCYL有限且>0走B0，否则走C1；真实正数1走B0，禁止用scale==1判断回退。B0目标log1p(RCYL/scale)，C1目标log1p(RCYL)，两臂均用全体81训练井972行、325项特征。ExtraTrees400棵树、leaf6、max_features0.75、seed20260916，其余看锁。

核心事实待核查：10口测试井全部为正尺度，回退0口，全部走B0；B已记录当前R1测试预测逐值等于本次全量B0。所以训练回退组路由收益不能证明测试集提分。源码/合成可独立检查；真实逐值一致和包复现若未亲自执行，只能引用B记录，不得签成A实机复验。

四、本次审核重点

1. 核对计划、授权、环境、实现和正式包摘要身份，区分自己复算、旧A结论、B执行记录和用户报分。历史dtype身份仍UNKNOWN，不能用当前类型摘要回填。
2. 检查M为最后连续事件段末月、井史截止M−1、目标M+1至M+12；raw last RCYL/尺度/动态特征截止一致；按WELL_ID隔离、只在训练折拟合预处理；不得更改锚点或特征工程。
3. 官方指标epsilon=1e-6、未归一化2^-t权重、先单井再井等权。聚合复算范围据现有匿名证据决定，不能从匿名汇总伪称逐行OOF复算；不为补证据重训70次。
4. 复核部署的31项纯合成，可在已有合适环境从匿名包source目录运行python -E -B -m unittest test_deployment test_platform_contract。自己另写关键路由/尺度/指标/日期与键约束测试。不能执行真实训练入口。
5. 原并行推理微小差异最大8.881784197001252e-15，修复为顺序推理、没有重训；检查保存重载、依赖检查、推理拟合阻断和旧目录访问阻断的实现及证据，不把事后验收失败记为模型重试。
6. 平台格式为result.zip根目录10份逐井CSV、120行，列WELL_ID/NY/RCYL、唯一键、不增删行、有限非负。NY补零为YYYY/MM/DD，日期语义及行序不变。submission_code.zip根目录README.md/predict.py/requirements.txt，含真实模型，可用--data_dir与--output独立推理。实际真实ZIP端到端已由B执行；真实CSV目录只做合成覆盖；评测服务器运行未经A/B核验。只读材料不能消除这些范围限制。
7. 原100文件、1668旧工件SHA256检查及完整模型复现是B侧执行证据；没有本机材料/授权不要求补传，也不冒充A独立核验。

主办方已回复边界需参赛者理解探索。缺少唯一官方解释本身不列阻塞P0，不再申请官方说明；边界按版本化假设研究。真实泄漏、目标错位、井隔离和指标仍是硬门禁，分数不能证明业务语义。

五、交付和下一步

完成后署名“账户A（新接手）独立审核与交付”，在A专用新分支和版本目录发布REPORT_A.md、COLLABORATION_REPLY_A.md、来源及证据等级表、独立检查程序和结果、风险/未核验项、SHA256与匿名只读复测包。可使用用户正常登录的ylrq8475-ui，但GitHub登录身份不改变逻辑A身份。不要改B分支、main或旧A成果；不得公开模型、真实井号/预测、逐行OOF、原CSV、私有配置、登录凭据或平台隐私截图。匿名发布已授权，无需再逐项问；如登录/写权限实际缺失，只告知具体正常操作，不索要密码/验证码、不绕过控制。

按实际完整提交回取全部公开文件，核对原始字节SHA256、长度、清单和新增范围后，再报告GitHub交付完成，给固定报告/协作回复/复测包链接和包摘要。不直接联系B，由用户转交。

最终输出【协作回复】：新A身份、审查固定提交、自己实际验证的事实、继承的记录、86.2003的来源及包绑定状态、原研究确认失败是否维持、探索部署的审核范围与未核验项、当前测试R1=B0的影响、按优先级排列的问题，以及下一轮一个最优先可证伪机制建议。本轮只提出方案，不自行启动下一训练、按平台分数调参、升级或再次提交。
