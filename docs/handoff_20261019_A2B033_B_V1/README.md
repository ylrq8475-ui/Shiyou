# A2B-033 方法与复核说明（未形成提交包）

账户B执行与交付。算法：基于历史月度特征的ExtraTrees多步油量预测，log1p(RCYL/s)目标；s取截止T0−1时未经填补的last RCYL，非有限或非正回退1。400棵树，min_samples_leaf=6，max_features=0.75，seed20260916；原325列，按井五折，折内填补/编码。T4依据ce76e2ba0c3296f22f18a67bf212c05091b14573；R10依据55adffb975204493cdc75567de8d74fc82dd3a73。

本轮OOF+2.618511，但只有3/5折改善，未通过全部保留门槛。因此未全量训练、未保存权重、未创建RELEASE_GATE.json、未生成result.zip或submission_code.zip、未建立干净复现环境；没有平台上传。

Python3.13.7；全部推理/训练依赖的精确版本见requirements.txt；完整本轮环境见ENVIRONMENT_LOCK.json。core.py恢复FROZEN_SOURCES.json中的原src并验证字节；fit_ledger.py控制逐次进入、完成、失败停止和7次上限。csv_projection.py只投影模板键和合法前缀。run_oof.py是本轮实际实验入口；train.py/predict.py是未触发步骤2的预备入口。原始数据、私有策略和权重不在公开目录。

只读复核可将方法文件复制到一个新空目录的source子目录，在该source中执行：

```text
python -m unittest -v test_033.py
```

这只运行合成检查，不训练真实模型。真实OOF已经成功完成，不可在本轮重复执行。既有实验布局的实际命令接口为：

```text
python run_oof.py --archive <官方原始ZIP> --manifest <冻结清单JSON> --original-config <冻结私有配置YAML>
```

实验布局：run_oof.py和PLAN_R10.json位于独立实验根；方法文件在source；私有运行策略在private/runtime_policy.json；R10原文在received。上式仅供追溯，不是新增拟合授权。先有预算和本机访问授权，才可真实复测。

未触发的步骤2接口设计如下（本轮禁止执行；没有RELEASE_GATE会阻断）：

```text
python train.py --data_dir <官方数据目录或原ZIP> --output <新的模型目录> --policy <随私有代码包提供的runtime_policy.json>
python predict.py --data_dir <官方数据目录或原ZIP> --model <模型目录/B0_prime.joblib> --output <新的result.zip路径> --policy <同一runtime_policy.json>
```

--data_dir指定官方原始结构；--output分别指定新模型目录或结果ZIP，不依赖外部缓存；策略原拟包含在私有包中，不作为公开隐藏依赖。完整包当前不存在，以上设计不能代替真实验收。模板键/日期/顺序原样继承；预测应有限非负；CSV平铺ZIP根；predict禁止任何fit。参数门槛均来自R10及已锁A2B-013，无看分数后调整。

后续若重新授权阶段2，需要明确处理本轮一致性未达门槛；B不会自行创建放行标志。源码、登记卡和全部负/正折结果保留供Codex独立复核。
