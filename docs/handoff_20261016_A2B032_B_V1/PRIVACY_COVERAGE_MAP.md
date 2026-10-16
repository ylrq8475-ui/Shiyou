# A2B-032/R9发布文件逐项隐私覆盖

账户B执行与交付。每份发布文件均有本轮扫描记录，无扫描豁免。原始证据见PRIVACY_SCAN_RAW.json的record_id。
真实标记仅在内存：88口训练历史标记及由原清单文件名绑定得到的10口测试标记、实际训练日期和月份、私有候选；不读取方案/层位原值。本轮不读取方案/层位值，也不将其作为本次标记穷尽匹配来源。已知私有标记仅在内存，原值没有写入报告。数值字段仅发布聚合和锁定参数，不发布原始单元格。本隐私扫描不解析测试CSV；R9审计在模板键哈希验证后仅投影窗口前必要列；本扫描不解析任何测试CSV。测试窗口内RCYL/事件/其他动态值不解码、不解析、不使用。

| 文件路径 | 原始扫描记录 | 结果 | 身份绑定 |
|---|---|---|---|
| `docs/handoff_20261016_A2B032_B_V1/CLAUDE_INSTRUCTION_ORIGINAL_R9.md` | `A032R9-PRIVACY-001` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/ENVIRONMENT_LOCK.json` | `A032R9-PRIVACY-002` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json` | `A032R9-PRIVACY-003` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/PLAN_R9.json` | `A032R9-PRIVACY-004` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/PRIVACY_COVERAGE_MAP.md` | `A032R9-PRIVACY-005` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/PRIVACY_SCAN_RAW.json` | `A032R9-PRIVACY-006` | PASS，私有标记及凭据命中0 | 最终序列化字节；记录不作循环自哈希，清单/Git绑定 |
| `docs/handoff_20261016_A2B032_B_V1/README.md` | `A032R9-PRIVACY-007` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/READ_BOUNDARY_AND_INTEGRITY.json` | `A032R9-PRIVACY-008` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/REPORT_B.md` | `A032R9-PRIVACY-009` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/REPRODUCE.md` | `A032R9-PRIVACY-010` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/REQUEST_CODEX_REVIEW.md` | `A032R9-PRIVACY-011` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/RESULT_A2B032.json` | `A032R9-PRIVACY-012` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/SHA256SUMS.json` | `A032R9-PRIVACY-013` | PASS，私有标记及凭据命中0 | 最终序列化字节；记录不作循环自哈希，清单/Git绑定 |
| `docs/handoff_20261016_A2B032_B_V1/SOURCE_RECEIPT.json` | `A032R9-PRIVACY-014` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/SYNTHETIC_LOG.txt` | `A032R9-PRIVACY-015` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/SYNTHETIC_RESULTS.json` | `A032R9-PRIVACY-016` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/TARGET_ALIGNMENT_DRAFT.md` | `A032R9-PRIVACY-017` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/ZERO_FIT_COUNTS.json` | `A032R9-PRIVACY-018` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/audit_core.py` | `A032R9-PRIVACY-019` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/privacy_check.py` | `A032R9-PRIVACY-020` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/run_audit.py` | `A032R9-PRIVACY-021` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B032_B_V1/test_audit.py` | `A032R9-PRIVACY-022` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |

隐私扫描JSON自身与SHA清单的最终序列化字节在落盘前也经过同一个扫描函数，不因“扫描后才生成”漏扫。扫描JSON的实际SHA由SHA256SUMS.json绑定；SHA清单的自身SHA由固定Git提交与外部回取凭证绑定。两个元数据记录不伪造循环自哈希，因此记录内sha256/bytes写null，属于哈希位置说明，不是免扫。其余文件均逐项记录原字节SHA与字节数。全部最终字节回取后再次比较并扫描，保留本地完整回取凭证。

所有原始赛事文件仅校验字节、不解压；私有配置、原清单及归档读取前后摘要一致。只持久化聚合命中计数，不写匹配标记、原始行、逐井数据或标签。
