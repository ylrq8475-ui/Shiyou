# 管线入口、边界与审查范围

解开匿名源码ZIP，原目录结构为 source/。使用Python3.13.7及ENVIRONMENT_LOCK.json的全部版本。安装示例先用受检Python创建 `.venv`，后续统一使用 `.venv\Scripts\python.exe`（Linux为`.venv/bin/python`），不得混用裸解释器。私有策略配置只由已授权本地材料提供，SHA见DATA_CONTRACT。

```powershell
.venv\Scripts\python.exe source/train.py --config variant.json --data_dir <官方数据目录或原ZIP> --policy <本地私有策略JSON> --output <新的私有模型目录>
.venv\Scripts\python.exe source/predict.py --config variant.json --data_dir <官方数据目录或原ZIP> --policy <同一私有策略JSON> --model <该目录/model.joblib> --output <新的私有result.zip>
.venv\Scripts\python.exe source/evaluate.py --config variant.json --data_dir <官方数据目录或原ZIP> --policy <本地私有策略JSON> --output <新的匿名聚合运行目录>
```

当前缺少真实 Codex 管线放行凭据，以上训练、评估与推理入口在读数据和拟合前拒绝搜索/部署操作。这不是已经执行了部署或完整提交包验收。B侧基准专用入口仅放行BASELINE_ALLOWLIST所列的两份配置，不能借 benchmark 名字增加候选。CODEX凭据须绑定PIPELINE_LOCK摘要和真实40位审核提交；B不自行制作通过凭据。

共同调用链：strict config → source lock → private policy identity → legal_history → frozen history feature definitions → raw legal scale → train-fold-only preprocessing/learner → official metric。T0−1主截止、M−1历史截止均由legal_history执行；新尺度和R1–R5也只接收已截断的值。M−1使用预测前合法前缀中的实际末次事件段M，而非假定始终是T0−2。事件段S/M仅从T0前合法事件元数据确定，M−1统计仍严格截止M−1。

原325特征、lag/rolling/trend定义保留；历史函数属于冻结库。库中旧的测试加载/定位函数没有被共同入口调用：测试入口只走core.test_keys_and_history。其先投影WELL_ID、NY并核对已冻结模板键摘要，再构造仅NY<T0的内存CSV；窗口动态字节不交给pandas。改变模板身份键会阻断，不把键改变也解释为应当预测不变。

推理按井独立调用；预处理仅transform；模型与预处理fit/fit_transform被拒绝。标准ET预测顺序求和确定。TabPFN若未来激活，单行query且必须有实际权重、版本v2、许可证署名与独立性证据；当前未激活。没有按标识或缺失模式选择预测记录，没有跨测试井统计或调参。

配置允许的ET旋钮：400/800，leaf2/4/6/10，max_features .3/.5/.75/1；seed20260916。新目标尺度：最后合法原始RCYL；截止月及前2个日历月有限非负值均值；本次事件段S前3个日历月均值（缺任何一月则回退）；直接log1p（scale1）。均值无有效正值或原始尺度非正/非有限时回退1。R1–R5沿用R12；缺月/零分母为NaN。G仍禁用，不能把旧Q1 UNKNOWN改成放行。

LightGBM小网格已定义为num_leaves7/15/31、learning_rate .03/.05、n_estimators400/800、min_child_samples10/20；CatBoost默认仅depth4/6、固定种子；多输出ET沿用允许ET网格。它们的源码分支存在不代表已执行或已验收。外部资源尚未下载/激活，Chronos离线适配尚未完成；本阶段不宣称搜索空间全部实现、全部可运行或外部模型已通过。

融合等权固定；加权网格步长0.1在每个外层训练侧另做井级内层五折，权重选择不接触外层验证标签，不复用包含外层验证影响的其它外层OOF来调权。嵌套训练会计入未来R13账本，当前基准没有融合拟合。排名、候选数量和完整版本选择遵守R13；配置不能更改官方指标、时间守卫和分组方案。

当前锁记录真实Python构建及全部依赖，前后版本一致；未来每个完整变体运行前仍须保存其实际环境并核对，环境改变后不得混用此前折结果。历史dtype缺口继续UNKNOWN；本轮有新的分数前类型、行序、标签、特征和切分指纹，不冒充历史加载身份。
