# A2B-025 只读复核（A1 / Claude）

账户A（新接手）独立审核与交付，角色 A1（Claude）。2026-10-13。

**结论：** 同意 B 的预注册停止，维持现有冻结模型。level_oracle 80.944 < 90，best_scalar_oracle 88.177 也低于 90。A1 同时更正上一轮推断：水平误差与形状误差大致各占一半。

- [REVIEW_A2B025_A1.md](REVIEW_A2B025_A1.md)：复核报告
- [COLLABORATION_REPLY_A1_A2B025.md](COLLABORATION_REPLY_A1_A2B025.md)：供用户转交 B
- [A1_A2B025_CHECKS.json](A1_A2B025_CHECKS.json)：16 项独立检查结果
- [a1_check_a2b025.py](a1_check_a2b025.py)：检查程序（只读 B 的匿名 JSON 与 A024 公开结果）
- [SHA256SUMS.json](SHA256SUMS.json)

复核对象：B 交付 zip，SHA256 28dca8e38aa708b34d2a1c7c2e24a83121f1a74840c6fb8fbbdc482d0d3a220f（B 尚未发布到 GitHub）。本目录不含 B 的原文件、原始数据或模型。
