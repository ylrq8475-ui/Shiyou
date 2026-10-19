# A2B-033 B0′：ExtraTrees月度产油量预测

账户B执行与交付。用户按R11明确越过“至少4/5折为正”门槛后，授权此独立提交包；原步骤1仍是弱信号，不改写为通过。当前包不代表已获平台上传或最终指定授权。

算法为原A2B-013 ExtraTrees：81口完整训练井、972行、325项预处理前特征。numeric中位数填补及缺失指示、StandardScaler、categorical编码仅在训练数据拟合。400棵树、min_samples_leaf=6、max_features=0.75、random_state=20260916、n_jobs=-1；其余原始参数见MODEL_PARAMETERS.json和冻结方法源码。所有lag、rolling、trend保持按原观测记录定义，未增加日历重索引、层位、方案、扩样、校准、融合或外部数据。

唯一研究改动：特征和未经填补的原始last RCYL尺度s统一用NY<T0的同井历史，训练T0=M+1，故截止M；测试T0为官方模板第1个月。s仅当原值有限且大于0时采用，否则1。目标log1p(RCYL/s)，逆变换expm1后乘s，预测裁剪非负；目标仍M+1..M+12。模板窗口内所有动态值不解码、不进入pandas或特征流程。模板键先单独投影并核验身份，输出继承原始日期字符串、键和顺序。截止依据[Codex T4](https://github.com/ylrq8475-ui/Shiyou/blob/ce76e2ba0c3296f22f18a67bf212c05091b14573/docs/handoff_20261019_A2B032_T4_AND_T1T3_CODEX_V1/REPORT_CODEX_T4.md)。

参数与范围来源：[R10](https://github.com/ylrq8475-ui/Shiyou/blob/55adffb975204493cdc75567de8d74fc82dd3a73/docs/handoff_20261019_A2B033_CLAUDE_INSTRUCTIONS_R10/INSTRUCTION_ORIGINAL.md)、[步骤1](https://github.com/ylrq8475-ui/Shiyou/blob/e846e2094ced5a71e3550294a15432388664cd5a/docs/handoff_20261019_A2B033_B_V1/REPORT_B.md)、[R11](https://github.com/ylrq8475-ui/Shiyou/blob/012e9fe50efac3f051b48804bc724e39b703cc93/docs/handoff_20261019_A2B033_CLAUDE_INSTRUCTIONS_R11/INSTRUCTION_ORIGINAL.md)。未根据平台分数调整预测。Python 3.13.7，全部依赖与版本见requirements.txt；训练BLAS/OpenMP=1，树内部并行，推理按确定顺序归约。

在解压后的代码根目录，建立独立环境并安装依赖：

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Linux等环境使用`.venv/bin/python`。精确复现验收在Windows Python 3.13.7进行；其他操作系统的二进制一致性未签署。

从官方原始数据从头训练再推理，无需修改代码、手工填数据或访问原工程/缓存：

```text
python train.py --data_dir "D:/official_data" --output "./trained"
python predict.py --data_dir "D:/official_data" --model "./trained/B0_prime.joblib" --output "./result.zip"
```

如只需加载本包已训练模型进行推理，一条命令：

```text
python predict.py --data_dir "D:/official_data" --output "./result.zip"
```

`--data_dir`可为赛事原始结构的数据目录，也可为原始赛事ZIP；不需要解压或复制原始数据。`--output`：train.py指定新模型目录，predict.py指定result.zip路径。输出路径必须未存在，避免覆盖或重复训练。目录包含原赛事相对结构，严格按随包私有runtime_policy.json配置的文件角色解析；该配置随正式私有包提供，不是隐藏文件。也可显式用`--policy`指定该文件。训练可选`--ledger`指定共享计数文件、`--stage`指定审计阶段；本轮实际两次全量训练共享计数器，失败不重试。运行前确保有对应训练授权，已成功完成的本轮阶段不要重复执行。

文件：train.py全量训练；predict.py只读合法历史、加载模型、推理、输出及linter；core.py特征与数据边界；csv_projection.py字节级键投影；fit_ledger.py逐次拟合计数；src/oil_uplift/为原方法模块；FROZEN_SOURCES.json保留10模块原始字节身份并在新目录缺少src时恢复；models/B0_prime.joblib含模型与预处理器；models/MODEL_RECEIPT.json校验模型；runtime_policy.json为本地赛事配置与输入身份，不上传GitHub；STEP2_AUTHORIZATION.json保留用户偏离门槛的授权。MODEL_PARAMETERS.json、ENVIRONMENT_REFERENCE.json提供参数和环境来源。test_033.py是零真实拟合的边界与预算合成检查，执行`python -m unittest -v test_033`。

result.zip根目录10个WELL_ID.csv，共120行，严格3列WELL_ID,NY,RCYL。推理入口禁止任何模型或学习型预处理拟合，并检查键、日期、顺序、重复、有限非负、平铺ZIP及CRC。正式包与模型、预测结果仅本地交付，匿名GitHub材料不包含私有配置、原始数据、权重或逐井预测。历史dtype身份仍UNKNOWN，依既有R5例外不阻止本轮，未回填旧证据。
