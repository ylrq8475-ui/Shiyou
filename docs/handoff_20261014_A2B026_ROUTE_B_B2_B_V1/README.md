# A2B-026 路线B B-2匿名复现材料

账户B执行与交付。入口run_b2.py只做训练井OOF，不输出测试预测，不保存模型，不生成ZIP。

在固定提交的完整仓库checkout内运行，保留原src/目录。Python3.13.7及全部依赖版本见requirements-b2.txt。公开SOURCE_RECEIPT.json绑定18份原仓库源码与私有输入摘要，私有输入本身不随代码发布。

先做无拟合检查：`python -B -m unittest -v test_route_b`（在本目录运行）。

获授权本地真实复现命令（输出必须是新的空路径；25次森林模型拟合、20次完整ColumnTransformer拟合，子步骤依原Pipeline正常执行，不另计为完整预处理器）：

```powershell
python -B run_b2.py --archive <AUTHORIZED_DATA_ZIP> --manifest <FROZEN_RAW_MANIFEST_JSON> --config <FROZEN_PRIVATE_CONFIG_YAML> --project-src ../../src --history-lock REFERENCE_PANEL_CONTRACT.json --prereg-parameters PREREG_PARAMETERS.json --claude-original CLAUDE_INSTRUCTION_ORIGINAL_R3.md --claude-commit 088a71ae8760a57272f68cc2cb538b0a8eecc288 --codex-result CODEX_ITEM11_AND_ITEM04_RESULT.json --output <NEW_EXPERIMENT_OUTPUT_DIR> --authorized
```

`--archive`原赛事归档，仅读取，不解压；`--manifest`原逐文件字节清单；`--config`原始冻结配置，不修改路径；`--project-src`已有仓库src/；`--history-lock`匿名原面板身份和特征顺序；`--output`本轮新输出目录，存在即拒绝运行；可用重复的`--protected-root`增加本地旧工件只读完整性核验。

程序先检查固定队列/顺序/特征/窗口/尺度/切分，保存环境及实现锁；基线五折须复现73.71410733861434±1e-9，失败即停止。成功基线对象只留内存复用，然后内层公式τ及五折分类。已有成功折不从磁盘恢复，不自动重新训练；任何运行失败重试预算0。

油井标识、月份、标签、概率、预测、逐行OOF均不持久化。原数据、私有配置、权重和提交包不在交付中。独立审核不能把“脚本可运行”当成追加真实复现批准。

隐私证据：PRIVACY_COVERAGE_MAP.md逐文件对应PRIVACY_SCAN_RAW.json。SHA256SUMS.json按原始字节绑定所有其他文件；清单自身由固定Git提交与外部回取凭证绑定。隐私扫描记录自身由清单绑定，两个元数据文件均检查最终序列化字节，未以自引用哈希伪造身份。
