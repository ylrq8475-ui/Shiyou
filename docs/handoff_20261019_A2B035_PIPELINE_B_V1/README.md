# A2B-035：账户B共用管线与基准交付

主报告为 REPORT_B.md，单一结果为 RESULT_PIPELINE.json。R13 共用管线阶段已完成，搜索尚未启动，待 Codex 一次性独立审核。

固定五折：B0=73.71410733861434；B0′=76.33261832127738。两者与指定历史值之差均0。
五组重复均值：B0=72.47647400484871；B0′=75.39352260217446；配对平均增量=2.91704859732575。

PIPELINE_SOURCE_ANONYMOUS.zip 是匿名复测源码，不是赛事 submission_code.zip。它包含完整源码树和两份基准配置，不含赛事数据、私有策略配置、模型权重或预测。根目录同名源码供网页审查；可运行目录结构以ZIP内 source/ 为准。私人 runtime_policy.json 须由已授权接收方在本地提供，不从GitHub补齐。

本阶段只验证 ET 基准路径。LightGBM、CatBoost、TabPFN v2、Chronos 系列和 G 均未启用，见 RESOURCE_RELEASES.json；未把外部适配器的许可证、权重和独立性记为通过。
