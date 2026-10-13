# 95+ 方向评估（独立方案研究账户）

署名：**独立方案研究账户：95+方向评估**。2026-10-13。不是 A2 审核通过，也不是 B 执行记录；本轮没有任何真实拟合。

**结论：** 目前没有可信的 95 路径，但也没有证明 95 不可能。水平误差与形状误差大致各占一半，单一机制覆盖不了 95 所需的 64% 平台损失削减。

- **首选：** 锚点月 M 信息锚定（先过零拟合检验 D0/D2）
- **备选：** 停产月感知的两段式预测（先过 D1）
- **暂缓：** ExtraTrees absolute_error

最先投入的资源应是零拟合诊断 D0–D4。

| 文件 | 内容 |
|---|---|
| [RESEARCH_DIRECTION_REVIEW.md](RESEARCH_DIRECTION_REVIEW.md) | 瓶颈判断、三条路线、资源建议 |
| [PRIOR_EXPERIMENT_COMPARISON.md](PRIOR_EXPERIMENT_COMPARISON.md) | 既往实验对照与查重 |
| [PRIMARY_EXPERIMENT_DRAFT.md](PRIMARY_EXPERIMENT_DRAFT.md) | 首选实验草案（待用户批准，尚未执行） |
| [EVIDENCE_AND_UNKNOWNS.json](EVIDENCE_AND_UNKNOWNS.json) | 证据等级、假设与未知项 |
| [PROMPT_FOR_ACCOUNT_B_PENDING_APPROVAL.md](PROMPT_FOR_ACCOUNT_B_PENDING_APPROVAL.md) | 可转发 B 的执行 Prompt（待用户批准） |
| [synthetic/](synthetic/) | 纯合成推导：损失几何、停产月判据 |
| [reference/](reference/) | 阶段 0 诊断参考实现与 12 项合成测试 |
| [SOURCE_RECEIPT.json](SOURCE_RECEIPT.json) | 读取的固定来源及字节摘要 |
| [SHA256SUMS.json](SHA256SUMS.json) | 本目录文件摘要 |

复测（只用合成数据）：
- `python -I synthetic/loss_geometry.py out1.json`
- `python -I synthetic/zero_decision_synthetic.py out2.json`
- 在 reference/ 内运行 `python -E -B -m unittest test_diagnostics_reference`

依赖 numpy。
