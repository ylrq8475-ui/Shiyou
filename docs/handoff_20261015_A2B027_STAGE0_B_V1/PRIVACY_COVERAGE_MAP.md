# A2B-027阶段0发布文件逐项隐私覆盖

账户B执行与交付。每份发布文件均有本轮扫描记录，无扫描豁免。原始证据见PRIVACY_SCAN_RAW.json的record_id。
真实标记仅在内存：88口训练历史标记及由原清单文件名绑定得到的10口测试标记、实际训练日期/月度字符串、私有候选字符串。本隐私扫描不解析测试CSV；F0另行解析不含RCYL的10表，见结构门禁；测试标签未读取。

| 文件路径 | 原始扫描记录 | 结果 | 身份绑定 |
|---|---|---|---|
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/DELIVERY_BUILD_RECORD.json` | `A027-PRIVACY-001` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/EVENTS.json` | `A027-PRIVACY-002` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/F0_FIELDS.md` | `A027-PRIVACY-003` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/F0_FIELD_RESULTS.json` | `A027-PRIVACY-004` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/FIELD_DICTIONARY.json` | `A027-PRIVACY-005` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/FIT_COUNTS.json` | `A027-PRIVACY-006` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json` | `A027-PRIVACY-007` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/OOF_SOURCE_AND_PENDING_CHANGE.md` | `A027-PRIVACY-008` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/PLAN_STAGE0.json` | `A027-PRIVACY-009` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/PRIVACY_COVERAGE_MAP.md` | `A027-PRIVACY-010` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/PRIVACY_SCAN_RAW.json` | `A027-PRIVACY-011` | PASS，私有标记及凭据命中0 | 最终序列化字节；记录不作循环自哈希，清单/Git绑定 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/README.md` | `A027-PRIVACY-012` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/REFERENCE_PANEL_CONTRACT.json` | `A027-PRIVACY-013` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/REPORT_B.md` | `A027-PRIVACY-014` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/REPRODUCTION.md` | `A027-PRIVACY-015` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/REQUEST_CODEX.md` | `A027-PRIVACY-016` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/RESULT_A2B027_STAGE0.json` | `A027-PRIVACY-017` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/RESULT_SNAPSHOT_BINDING.json` | `A027-PRIVACY-018` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/SHA256SUMS.json` | `A027-PRIVACY-019` | PASS，私有标记及凭据命中0 | 最终序列化字节；记录不作循环自哈希，清单/Git绑定 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/SOURCE_RECEIPT.json` | `A027-PRIVACY-020` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/SPLIT_REFERENCE.json` | `A027-PRIVACY-021` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/STRUCTURE_GATES.json` | `A027-PRIVACY-022` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/SYNTHETIC_LOG.txt` | `A027-PRIVACY-023` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/SYNTHETIC_RESULTS.json` | `A027-PRIVACY-024` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/diagnostic_core.py` | `A027-PRIVACY-025` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/privacy_check.py` | `A027-PRIVACY-026` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/route_b_core.py` | `A027-PRIVACY-027` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/run_stage0.py` | `A027-PRIVACY-028` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/test_diagnostics.py` | `A027-PRIVACY-029` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261015_A2B027_STAGE0_B_V1/train_reader.py` | `A027-PRIVACY-030` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |

隐私扫描JSON自身与SHA清单的最终序列化字节在落盘前也经过同一个扫描函数，不因“扫描后才生成”漏扫。扫描JSON的实际SHA由SHA256SUMS.json绑定；SHA清单的自身SHA由固定Git提交与外部回取凭证绑定。两个元数据记录不伪造循环自哈希，因此记录内sha256/bytes写null，属于哈希位置说明，不是免扫。其余文件均逐项记录原字节SHA与字节数。全部最终字节回取后再次比较并扫描，保留本地完整回取凭证。

所有原始赛事文件仅校验字节、不解压；私有配置、原清单及归档读取前后摘要一致。只持久化聚合命中计数，不写匹配标记、原始行、逐井数据或标签。
