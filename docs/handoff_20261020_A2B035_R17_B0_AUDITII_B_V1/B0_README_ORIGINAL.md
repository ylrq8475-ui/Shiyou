# A2B-035 R15 B0重新打包（不上传）

账户B执行与交付。原A2B-013 ExtraTrees400、leaf6、max_features0.75、seed20260916。原81井972行325特征；井史截止事件段末月M之前一个完整月，原始最后观测RCYL有限且正时作尺度，否则1；不向前搜索更早的正值。目标log1p(RCYL/s)，预测expm1乘s后裁非负。无校准融合、层位方案、扩样或外部数据。未改变lag/rolling/trend或官方指标。

Python3.13.7，完整依赖锁见requirements.txt，实际版本运行前核对。首次用该版本Python创建环境，此后统一使用该环境解释器：
```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe train.py --data_dir D:/official_data --output ./new_model
.venv\Scripts\python.exe predict.py --data_dir D:/official_data --model ./new_model/model.joblib --output ./result.zip
```
直接加载本包权重只需最后一条命令，省略--model时默认models/model.joblib。--data_dir接受官方原始目录或原ZIP，保持原相对结构；--output为新的训练目录或结果ZIP。无须修改代码或原配置。runtime_policy.json仅供本地正式包，绑定特征、队列和模板；旧路径不用来定位输入。

source/base是原字节共用源码，source/b0_entry.py按R15明确授权只重建原B0；根train.py和predict.py为入口。训练只读训练CSV；推理逐井，模板原键/日期/行序继承；模板窗口内非键值不解码、不进特征，不拟合测试数据。输出10个WELL_ID.csv、120行、WELL_ID/NY/RCYL三列，自动CRC、键与非负有限值检查。权重、私有策略和结果ZIP不上传GitHub。本包不上传平台、不自动替换现有模型。

## 配置接口补充

train.py和predict.py均接受--config variant.json，默认读取随包variant.json；仅允许本完整版本的冻结配置，其他内容评分前即拒绝。此补充仅加入参数验证，不改变模型、私有策略、算法核心或result.zip，拟合0次；旧代码包保留。
