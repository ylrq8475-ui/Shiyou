# A2B-035 R14 账户B管线增量交付

本批状态：实现与只读/合成核验完成，真实训练0；等待Codex增量签署。结果唯一入口为RESULT_R14_PREPARATION.json，报告见REPORT_B.md。

解开R14_INCREMENT_REVIEW_ANONYMOUS.zip会得到source/、configs/、PLAN_R14.json与external_probe.py，不含私有配置/数据/模型。现有已授权私有策略通过命令参数提供，SHA必须与锁一致。请使用已有的Python3.13.7及source/base/requirements.txt锁定依赖；不得运行run_r14.py来代替只读审核。

仅复测合成检查（拟合0）：
```powershell
python -B source/check_r14.py --policy <existing-private-runtime-policy.json> --output <new-synthetic-result.json>
```
审核后B执行真实研究的入口（当前会因无增量签署而阻断）：
```powershell
python -B source/run_r14.py --data_dir <authorized-original-archive.zip> --policy <existing-private-runtime-policy.json> --output <new-experiment-directory>
```
实际Codex签署文件为source/INCREMENT_APPROVAL.json，包含role=Codex、can_search=true、increment_lock_sha256=`81d77e8147910352ee29c68d46911a6d00026ff051e325b81624234af6de461a`、review_commit=实际40位审核提交、allowed_scope={"H":true,"T":true}。此处仅描述接口，B未伪造签署。外部准入与该H/T签署分别记录；原外部分支仍禁用。

source/train.py和source/predict.py提供--config、--data_dir、--policy、--output，预测另加--model；全量与正式包复现尚未执行，不将本次合成检查当作最终包验收。external_probe.py须在新的外部隔离环境运行，目前因共用sklearn原生模块被策略阻止而未完成；处理后预计仅合成模型/预处理各2次，逐次计数，不与真实竞赛拟合混记。
