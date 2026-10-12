# 实际源码审阅记录

账户A（替代接手）独立审核与交付。只读静态审阅；下列文件与函数基于固定包原字节。

|误差或风险来源|证据等级|影响阶段与方向|影响范围|复核位置/触发|混杂或限制|下一动作|状态|
|---|---|---|---|---|---|---|---|
|双臂井月、raw或拟合折错配|A源码审阅＋纯模块合成|错误路由可能任意改变分数|全部12月|a24_runner.py actual_identity、packet、run_family；各臂从自己的 view 建键/特征/dtype/raw摘要，pipeline._a24_fold_identity检查；pretrain_contracts.py拒绝错键与错身份并永久阻断|实际18项入口测试仅有B记录；A未访问真实预测数组|当前失败路径无需改动；未来入口变更保持故障注入|PASS（静态/纯模块）|
|目标泄漏和预测窗错位|A源码审阅＋B结构记录|虚高或错位评分|81井972行、325字段|a2b013_safe.py _safe_history_values传入M−1；multistep.py仅保留月份小于first_forecast_period；a2b013_safe.py目标取M+1..12；a24_runner.py keys由anchor_time+horizon生成|私有事件候选配置和真实数据未重读；业务语义为版本化假设|维持当前边界，实际泄漏仍阻断；不以缺官方唯一解释重开P0|PASS（静态），真实值未复测|
|跨井泄漏或漏折|A源码审阅＋事件核对|可虚高分数|七组35折|paired_experiment.py核对集合分区、井交集和每行OOF一次；a24_runner.py重复井隔离；7组均绑定锁中split摘要|摘要不能重新构造真实井分配|保留源哈希和原映射，不要求上传井号|PASS（静态/记录一致）|
|预处理使用验证数据|A源码审阅＋计数复算|可虚高分数|70条流水线|a24_runner.py fit_one内train[features]构造新流水线；pf核对输入与目标，mf核对实际变换输出；training.py median/scaler/encoder均在流水线内；两个臂均传全部训练折|计数钩子为源码证据，非A实机见证|不重训；之后代码改动保留实际x/y断言|PASS（静态）|
|目标或逆变换错误|A源码审阅＋A代数合成|改变学习和预测尺度|两臂全部训练井|a2b023_core.py target、inverse、fit_target_pipeline；training.py的目标/逆变换函数显示B0单次log及expm1×s，C1显式log/expm1；非双重log|s=1样本目标相等不证明回退值1是病因|本批停止，不据局部观察改阈值|PASS（静态/代数）|
|使用归一化权重或错误折平均|A独立公式＋聚合复算|能改变增益及停止门槛|七组21个方案总分|experiment_core.py well_arrays、:228 score_summary；scoring.py；A重写分母/epsilon/2^-t；17/16/16/16/16井加权折分|B月平均误差未由私有行重新生成；单折分数只与事件对照|采用INDEPENDENT_RESULT_A完整精度|PASS（聚合）|
|最低折分之差掩盖同折退化|A独立复算＋反例合成|可能错误放行|固定回放/确认|a24_control.py fixed_gate；pretrain_contracts.py fold_risk；分别计算两个量，确认均≥−1，固定仅约束前者|固定是已见切分；不能改计划追加门槛|保留−1.657512固定同折风险披露|PASS|
|组内分差冒充总体收益|A独立组损失重组|可夸大回退组改善|14回退井和67正尺度井|diagnostics.py group_report；a24_runner.py起贡献恒等式；确认组内+0.266334×14/81=+0.046033|每月回退贡献未单独提供原始数组，只有B断言与总体贡献向量|维持净贡献口径|PASS（聚合）|
|成功折重跑、失败后越预算|A源码审阅＋175事件重放＋纯状态机合成|增加选择机会或耗用未授权资源|研究60、确认10、全量0|a24_runner.py fit_one；pretrain_contracts.py FitBudget；a24_control.py Stages；execute确认门槛后才retain|本轮无真实故障；MemoryError只在B合成记录|确认失败即停止，不将剩余2次成功额度视作权限|PASS（已走停止路径）|
|低正尺度q25或标签切片反向用于路由|A源码审阅|可能形成事后选择|诊断分组|run_research.py prediction_states仅取训练折独立井；experiment_core.state_partition求训练q25；diagnostics标签切片不返回训练/路由；路由仅raw有限且>0|同81井反复研究的选择偏差仍在|不得把诊断改为新路由|PASS（静态）|
|失败后真实保存/升级|A源码审阅＋B记录|违反停止规则|全量模型|a24_runner.py确认通过才retain；FINAL_RESULT注册空、MODEL_REGISTRY无保存；INTEGRITY_RECHECK真实权重0|A未扫描远端磁盘；成功保存分支未独立执行|同意不保留；未来成功路径另审|PASS（停止决定），实机未验|
|历史dtype身份链缺口|继承UNKNOWN|限制历史身份等同声明|历史成果|本轮ordered_dtypes及panel摘要匹配仅覆盖本次锁|当前类型不能证明过去类型|保持UNKNOWN，不写回旧锁|UNKNOWN|

上游源码来自 A23 固定提交及匿名包；UPSTREAM_CHECK_A.json列出逐文件摘要。40份上游文件与当前12份绑定存在重叠，合计48个不同摘要，不能相加称52个不同来源。A24分数前锁共148项source_inputs，另外100项未在这两个公开源码集合中逐项恢复；范围包括历史脚本/文本/配置等，不等同于100份原始CSV。

执行入口依赖固定的B本机路径。此轮没有通过迁移路径、伪造依赖或启动--execute来扩大审核。B合成18项实际入口记录已审阅，未作为本人复跑。没有观察到已走失败停止路径上的新增P0/P1缺陷；报告保留证据可见性的限制。
