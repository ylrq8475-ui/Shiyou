# A1 复测说明

依赖：Python 3.13，numpy 2.4.3，pandas 2.3.3，scikit-learn 1.9.1（与 B 的锁相同）。只使用虚构数据和公开匿名聚合，真实拟合 0。

1. 克隆 https://github.com/ylrq8475-ui/Shiyou，然后运行
   `python -I check_fixed_sources.py <clone> ../SOURCE_RECEIPT_A.json`，应输出 32 个文件、无不符。
2. 从提交 519b00da… 取出 ANONYMOUS_REVIEW_BUNDLE.zip（SHA256 c7415aec…99e4d）并解压，把 `source/` **复制**到一个新的空目录。从提交 65115714… 取出 docs/handoff_20261012_A2B024_B/FINAL_RESULT.json。
3. 运行 `python -I a1_independent_checks.py --source <复制的source> --final FINAL_RESULT.json --out out.json`，应输出 20 / 20。
4. 在复制的 source 目录内运行 `python -E -B -m unittest test_deployment test_platform_contract`，应为 31 项 OK。
5. 私有比对（仅限持有两个 result.zip 的授权方，本地运行）：
   `python -I compare_result_zips.py <旧result.zip> <新result.zip>`。脚本只打印匿名计数和规范化摘要；A1 的结果见 ../PRIVATE_ARTIFACT_IDENTITY_A.json。
