# A2B-031/R8发布文件逐项隐私覆盖

账户B执行与交付。每份发布文件均有本轮扫描记录，无扫描豁免。原始证据见PRIVACY_SCAN_RAW.json的record_id。
真实标记仅在内存：88口训练历史标记及由原清单文件名绑定得到的10口测试标记、实际训练/方案日期和月份、私有候选及方案/层位非数值字符串。公开审核等级P0..P3及诊断编号N1/N2/N4只作为用户规定元数据，短码同名不视为层位原值输出；原值没有写入报告。数值字段仅发布聚合和锁定参数，不发布原始单元格。本隐私扫描不解析测试CSV；R8覆盖仅使用清单文件名绑定的测试标识，不解析任何测试井史CSV或标签。训练RCYL仅用于恢复既有完整队列，不落盘。

| 文件路径 | 原始扫描记录 | 结果 | 身份绑定 |
|---|---|---|---|
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/ENVIRONMENT_LOCK.json` | `A031R8-PRIVACY-001` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/EVIDENCE_A2B031.json` | `A031R8-PRIVACY-002` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/FIELD_CLASSIFICATION.json` | `A031R8-PRIVACY-003` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/FIELD_CLASSIFICATION.md` | `A031R8-PRIVACY-004` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/FIELD_DICTIONARY_PUBLIC.json` | `A031R8-PRIVACY-005` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json` | `A031R8-PRIVACY-006` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/OFFICIAL_EXCERPTS_E1.md` | `A031R8-PRIVACY-007` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/PRIVACY_COVERAGE_MAP.md` | `A031R8-PRIVACY-008` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/PRIVACY_SCAN_RAW.json` | `A031R8-PRIVACY-009` | PASS，私有标记及凭据命中0 | 最终序列化字节；记录不作循环自哈希，清单/Git绑定 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/README.md` | `A031R8-PRIVACY-010` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/REPORT_B.md` | `A031R8-PRIVACY-011` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/REPRODUCE.md` | `A031R8-PRIVACY-012` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/REQUEST_CODEX_REVIEW.md` | `A031R8-PRIVACY-013` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/SHA256SUMS.json` | `A031R8-PRIVACY-014` | PASS，私有标记及凭据命中0 | 最终序列化字节；记录不作循环自哈希，清单/Git绑定 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/SOURCE_RECEIPT.json` | `A031R8-PRIVACY-015` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/SYNTHETIC_LOG.txt` | `A031R8-PRIVACY-016` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/SYNTHETIC_RESULTS.json` | `A031R8-PRIVACY-017` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/USER_AUTHORIZATION_AND_SCOPE.json` | `A031R8-PRIVACY-018` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/ZERO_FIT_COUNTS.json` | `A031R8-PRIVACY-019` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/compute_evidence.py` | `A031R8-PRIVACY-020` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/privacy_check.py` | `A031R8-PRIVACY-021` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261016_A2B031_B_EVIDENCE_R8_V1/test_evidence.py` | `A031R8-PRIVACY-022` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |

隐私扫描JSON自身与SHA清单的最终序列化字节在落盘前也经过同一个扫描函数，不因“扫描后才生成”漏扫。扫描JSON的实际SHA由SHA256SUMS.json绑定；SHA清单的自身SHA由固定Git提交与外部回取凭证绑定。两个元数据记录不伪造循环自哈希，因此记录内sha256/bytes写null，属于哈希位置说明，不是免扫。其余文件均逐项记录原字节SHA与字节数。全部最终字节回取后再次比较并扫描，保留本地完整回取凭证。

所有原始赛事文件仅校验字节、不解压；私有配置、原清单及归档读取前后摘要一致。只持久化聚合命中计数，不写匹配标记、原始行、逐井数据或标签。
