# 计算入口与复测

账户B执行与交付。本轮未授权接收方自动训练，B已经完成5次真实SVD，不应为补表重复运行。

1. 零拟合合成检查：将diagnostic_core.py和test_diagnostics.py放同目录，使用已锁Python环境，执行 `python -B -m unittest -v test_diagnostics`。16项纯数值/结构检查，不调用SVD或模型。
2. 全部实际执行方法在run_stage0.py。依赖原项目公开src/oil_uplift及锁定环境；SOURCE_RECEIPT.json列18个源码身份，原公开来源提交213b1b465c61d799371e2b4326ebc71922c4f7ee。train_reader.py与route_b_core.py是此前B2固定版本的精确依赖副本，只用于只读归档解析与身份函数；不会启动B2或调用其中预算类，真正预算由本轮入口统一拦截。
3. 如另行获准真实复测，先在独立目录放置上述方法、PLAN_STAGE0.json、FIELD_DICTIONARY.json和SOURCE_RECEIPT.json；建received/，放本交付的REFERENCE_PANEL_CONTRACT.json、SPLIT_REFERENCE.json，并从R4固定提交按原字节取得INSTRUCTION_ORIGINAL_R4.md。入口会验证这些身份，不下载真实数据。原项目src由本机已授权副本提供。
4. 调用：`python -B run_stage0.py --project-src <已核对原源码的src目录> --archive <获授权原始归档路径> --manifest <冻结清单路径> --config <冻结私有配置路径> --output <不存在的新结果目录> --authorized`。CLI不需要修改私有配置或旧路径。源码不含数据，原始归档只读，不提取CSV，不写逐行输出。输出目录已存在则拒绝重复运行。
5. D-α纯计算方法在diagnostic_core.cross_residual_adjust，但真实入口因固定OOF未持久化没有调用它；没有预置预测或用全量模型代替OOF。需要另行决定后在内存获得同身份OOF，当前不提供逐行文件或自动补训入口。

数值约定：F0完整队列分母81，同时列88井辅助覆盖；F1 SVD无加权、训练中心化，四个K共用基；D-β两来源相加后除81；D-γ所有88井合法历史，ddof0，日历相邻差分和自相关。PLAN_STAGE0.json为分数前选择的细节，未将不明确细节伪装为官方定义。

公开依赖可从对应固定Git提交回取核对，私有配置、原始清单及赛事CSV仅由用户在已授权本机提供。未附包、模型、逐井映射、实际年月或预测。
