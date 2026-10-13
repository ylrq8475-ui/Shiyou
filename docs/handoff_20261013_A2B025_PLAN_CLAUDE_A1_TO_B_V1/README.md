# A2B-025 计划与B执行Prompt（账户A1（Claude）起草）

**标记：账户A1（Claude）。** 2026-10-13 新接手的独立审核账户A，模型为 Claude；署名“账户A（新接手）独立审核与交付”。A1 只起草计划，不执行真实训练。

**把 [PROMPT_FOR_ACCOUNT_B.md](PROMPT_FOR_ACCOUNT_B.md) 全文发给账户B即可。**

- PLAN_A2B025.json：训练前锁定的计划（阶段 0 只读计数、阶段 1 固定 B0 五折 5 次拟合、阶段 2 神谕诊断；阈值 90）
- reference/：参考实现与 15 项纯合成测试，运行 `python -E -B -m unittest test_a2b025_oracle`
- SHA256SUMS.json：本目录文件摘要

更正：固定 B0 五折只需 5 次拟合，不是 10 次。
