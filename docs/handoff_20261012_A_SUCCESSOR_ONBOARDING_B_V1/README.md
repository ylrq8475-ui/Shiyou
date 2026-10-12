# 替代账户A接手入口｜2026-10-12

账户B执行与交付；本轮仅整理接手资料，不执行账户A审核。用户要求更换独立审核账户，并继续使用现有GitHub仓库匿名交付。本包帮助新账户恢复上下文，不代表新账户A已经审核或验收。

**用户只需把[完整启动Prompt](PROMPT_FOR_NEW_ACCOUNT_A.md)发给新账户。** 新账户继续担任账户A，账户B身份和训练端不变。首项任务是对已完成的A2B-024 R2真实执行进行独立只读复核，不重训。

[上下文与历史](CONTEXT_AND_HISTORY.md) · [本轮审核清单](A2B024_REVIEW_CHECKLIST.md) · [账户A交付规则](GITHUB_DELIVERY_RULES_A_V1.md) · [范围与授权](ROLE_AND_SCOPE.md) · [只读恢复入口](bootstrap_readonly.py) · [资料原字节来源](SOURCE_PROVENANCE.json) · [匿名交接包](NEW_ACCOUNT_A_CONTEXT_BUNDLE.zip) · [包摘要与检查](DELIVERY_VERIFICATION.json)

当前实验固定来源：`65115714d49d17122989195910b119264bd93880`，原研究目录`docs/handoff_20261012_A2B024_B`；[原实验报告](https://github.com/ylrq8475-ui/Shiyou/blob/65115714d49d17122989195910b119264bd93880/docs/handoff_20261012_A2B024_B/REPORT_B.md)。方案审核来源：旧A提交`3272d3b86e2e7c0433b137ced6ee35b7cfb3aaca`，仅接受方案与纯契约，未验收后来的真实训练。

已完成研究60次及确认10次；五组平均+0.478484、5/5正增益；确认仅+0.046033且前两月−0.011989，未达保留条件，停止，全量/真实保存均0。新账户应独立判断证据与停止决定，不能把此B摘要当自己的审核结论。

原始数据、私有配置、模型权重、真实井号、逐行OOF不在交接包内。首次匿名复核无需转移赛事数据。Python路径和原工程目录均是历史来源，不可假定新账户所在机器拥有同一路径。

只读恢复：下载本目录的bootstrap_readonly.py后执行`python -B bootstrap_readonly.py --out <新建的独立目录>`。它只下载指定固定提交的匿名审计ZIP、校验原始字节及安全成员路径、解压匿名文件并运行匿名聚合检查；不导入训练入口、不访问原始赛事数据、不安装库、不拟合、不上传。原A024审计ZIP SHA256为`c26a1c87c0fdb4d96b4a3251aa13702ab7aeb258517edd2614029cf0d2393d50`。

新A审核完成后按本轮用户要求发布匿名报告到现有仓库，署名“账户A（替代接手）独立审核与交付”。GitHub登录和写权限在其实际环境核验；无需另建仓库、共享令牌或传递旧聊天。
