# 复现说明（本轮不执行任何额外拟合）

账户B执行与交付。原始数据、私有配置、模型权重不在GitHub。执行人须拥有本地数据授权；使用已锁定公开src与受控私有配置，不能为复现另改门槛。当前实验已完成，不要自动重跑。

先在独立环境安装ENVIRONMENT_LOCK所列依赖；FM使用独立FM_ENVIRONMENT_LOCK。按PREREG_A2B029锁定的单一revision下载权重至本地，核对SHA256并完成仅合成的fm_worker --probe。还原SOURCE_RECEIPT对应公开源码与授权数据身份。两个目录脚本保持同级，030目录准备FIELD_DICTIONARY_N1、PLAN_R6、received/INSTRUCTION_ORIGINAL_R6.md；028目录准备received中的参考合同、切分与参数锁、A027_SOURCE_RECEIPT、INSTRUCTION_ORIGINAL_R5.md及预注册文件。

```powershell
python -I run_experiment.py --authorized --project-src <original_src> --config <private_frozen_config> --archive <authorized_archive> --manifest <original_manifest> --output <new_nonexisting_output> --fm-python <isolated_FM_python> --fm-model <frozen_local_model_folder> --diagnostics-src <030_scripts_folder> --diagnostics-output <new_nonexisting_030_output>
```

必须先通过原面板及结构检查再锁实施身份；B0不符即全部停止。上限模型20、预处理20，无重试。--output存在即拒绝，避免无意重复已成功折。公开交付不含自动恢复/缓存逐行OOF；重新复现须有独立授权，不能因下载本材料自动视作获准。单独test_experiment.py、test_030.py只用合成数据，拟合0。正式训练/预测入口train.py条件本轮未触发，没有部署工件。
