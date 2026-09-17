# 中国石油算法挑战赛：化学驱过程中压裂引效增油效果预测

本代码包用于离线训练并预测压裂后连续 12 个月的日产油量 `RCYL`。它不下载外部数据、预训练权重或其他网络资源。赛事原始数据不包含在压缩包内，只能在获准的本地环境中读取。

## 当前提交模型

试投版本为 `v7_safe_plus_layer`：

- 使用锚点月及以前的井史特征和层位特征；
- `plan_first__` 特征数为 0，排除了首次方案时间泄漏；
- 不使用现有非严格嵌套校准，预测倍率固定为 1.0；
- 验证采用按 `WELL_ID` 分组的确定性五折；
- 固定五折未校准官方 OOF 为 `76.413676`。这是内部验证分数，不是榜单成绩。

锚点使用用户批准的数据推断规则 `data_inferred_latest_record_v1`：两个匿名候选取值按月度独立事件处理，选择最后一条候选记录所在月，预测从下一自然月开始。同月出现多条候选记录时程序会报错。该规则尚未得到主办方书面确认，应把它保留为独立版本因素。

## 环境安装

已验证 Python 3.13.7。建议在代码包根目录创建独立环境：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pip install -e .
python -m pytest -q -p no:cacheprovider
```

Linux 使用 `.venv/bin/activate`，其余命令相同。

## 一键重新训练并生成结果

确认当前机器符合赛事数据授权后运行：

```powershell
python reproduce_submission.py --data-dir <官方数据目录> --output-dir reproduction_output --authorized
```

脚本会依次完成匿名锚点候选分析、私有运行配置构造、完整训练、推理和结果打包。输出文件为：

```text
reproduction_output/result.zip
```

训练生成的私有配置、日志和模型只保存在当前本地代码目录，不应上传或公开。

## 分步运行

如需分别训练和推理，先运行候选分析与私有配置生成：

```powershell
$env:COMPETITION_DATA_ACCESS_ACK = "I_AM_AUTHORIZED"
python scripts\analyze_anchor_candidates.py --raw-dir <官方数据目录> --project-dir . --authorized
python scripts\prepare_private_runtime_config.py --raw-dir <官方数据目录> --project-dir . --candidate-code CSLB_012 --candidate-code CSLB_032 --experiment-id trial_safe_plus_layer --safe-plus-layer --authorized
```

再执行：

```powershell
python predict.py --data_dir <官方数据目录> --output reproduction_output\prediction_files --mode retrain --config configs\private_data_inferred_trial_safe_plus_layer.yaml
python validate_submission.py --config configs\private_data_inferred_trial_safe_plus_layer.yaml --submission reproduction_output\prediction_files
```

`predict.py --mode load` 可加载本地训练工件重新推理，但代码包本身不携带模型权重；复现默认走完整训练路径。

## 输出约束

`result.zip` 根目录直接放置每口测试井的 CSV。每个文件严格包含 `WELL_ID, NY, RCYL` 三列；日期和行顺序继承官方测试目标模板；预测值必须有限、非负。代码不会自动上传赛事平台。

官方加权损失按 12 个月使用未经归一化的 `1 / 2^t` 权重，所有井等权平均。实现位于 `src/oil_uplift/scoring.py`。

## 数据边界

普通日志和报告不得打印样本行、真实井号、逐井记录或原始类别值。代码包排除原始数据、私有配置、模型、预测文件、私有日志及既有压缩包。项目仍保留完整训练与加载权重两条路径，但当前提交代码包以重新训练复现为准。
