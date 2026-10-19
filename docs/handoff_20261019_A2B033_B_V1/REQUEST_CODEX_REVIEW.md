# R10独立审核请求（由用户转交）

账户B执行与交付。请仅按[R10②](https://github.com/ylrq8475-ui/Shiyou/blob/55adffb975204493cdc75567de8d74fc82dd3a73/docs/handoff_20261019_A2B033_CLAUDE_INSTRUCTIONS_R10/INSTRUCTION_ORIGINAL.md)审核本次B实验和停止决定；不替B训练、不替Claude修改门槛。T4边界依据ce76e2ba0c3296f22f18a67bf212c05091b14573。

重点：325列/当前dtype、目标、原五折索引一致；全部特征和原始尺度截止T0−1；窗口字段污染后预测不变；学习型预处理仅训练折；原工程源码字节绑定、原始数据与保护旧文件完整；官方指标逐井和17/16/16/16/16加权复算；拟合逐次5/5、无真实失败/重试。

本轮score=76.33261832127738，delta=+2.6185109826630395，positive_folds=3。请确认应落第三行弱信号，不能只按总增量启动步骤2。全量/复现拟合、模型保存、result.zip、submission_code.zip、linter均未执行，预备源码不冒充已验收工件。

HIST-DTYPE沿用R5例外，仍P1。请核对公开源码容器的每个内部文件SHA及隐私覆盖，私有策略/数据/权重/逐行OOF未上传。发布独立登记卡和单JSON，reviews_commit填本次B最终提交，并末尾追加索引。
