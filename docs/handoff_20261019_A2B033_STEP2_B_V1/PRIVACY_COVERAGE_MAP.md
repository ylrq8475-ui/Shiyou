# A2B-033/R11步骤2发布文件逐项隐私覆盖

账户B执行与交付。每份发布文件均有本轮扫描记录，无扫描豁免。原始证据见PRIVACY_SCAN_RAW.json的record_id。
真实标记仅在内存：88口训练历史标记及由原清单文件名绑定得到的10口测试标记、实际训练日期和月份、私有候选；不读取方案/层位原值。本轮不读取方案/层位值，也不将其作为本次标记穷尽匹配来源。已知私有标记仅在内存，原值没有写入报告。数值字段仅发布聚合和锁定参数，不发布原始单元格。本隐私扫描不解析测试CSV；R11实际推理入口在模板键哈希验证后仅投影窗口前必要列；隐私扫描本身不解析任何测试CSV。测试窗口内RCYL/事件/其他动态值不解码、不解析、不使用。

| 文件路径 | 原始扫描记录 | 结果 | 身份绑定 |
|---|---|---|---|
| `docs/handoff_20261019_A2B033_STEP2_B_V1/AUTHORIZATION_AND_DEVIATION.json` | `A033STEP2-PRIVACY-001` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/CLEAN_REPRODUCTION.json` | `A033STEP2-PRIVACY-002` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/DEPLOYED_B0_AGGREGATE_COMPARISON.json` | `A033STEP2-PRIVACY-003` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/ENVIRONMENT_CLEAN.json` | `A033STEP2-PRIVACY-004` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/ENVIRONMENT_COMPARISON.json` | `A033STEP2-PRIVACY-005` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/ENVIRONMENT_FIRST.json` | `A033STEP2-PRIVACY-006` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/FIT_LEDGER_STEP2.json` | `A033STEP2-PRIVACY-007` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/FROZEN_SOURCES.json` | `A033STEP2-PRIVACY-008` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/FULL_CLEAN_CLI.json` | `A033STEP2-PRIVACY-009` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/FULL_FIRST_CLI.json` | `A033STEP2-PRIVACY-010` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/INSTRUCTION_ORIGINAL_R10.md` | `A033STEP2-PRIVACY-011` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/INSTRUCTION_ORIGINAL_R11.md` | `A033STEP2-PRIVACY-012` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/INTEGRITY_AFTER.json` | `A033STEP2-PRIVACY-013` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/LINTER_RESULTS.json` | `A033STEP2-PRIVACY-014` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/MODEL_PARAMETERS.json` | `A033STEP2-PRIVACY-015` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/PLAN_R11.json` | `A033STEP2-PRIVACY-016` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/PREDICT_CLEAN_CLI.json` | `A033STEP2-PRIVACY-017` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/PREDICT_FIRST_CLI.json` | `A033STEP2-PRIVACY-018` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/PREFIT_LOCK.json` | `A033STEP2-PRIVACY-019` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/PRIVACY_COVERAGE_MAP.md` | `A033STEP2-PRIVACY-020` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/PRIVACY_SCAN_RAW.json` | `A033STEP2-PRIVACY-021` | PASS，私有标记及凭据命中0 | 最终序列化字节；记录不作循环自哈希，清单/Git绑定 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/PRIVATE_CODE_PACKAGE_MANIFEST.json` | `A033STEP2-PRIVACY-022` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/PUBLIC_CODE_TO_PRIVATE_PACKAGE.json` | `A033STEP2-PRIVACY-023` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/README.md` | `A033STEP2-PRIVACY-024` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/RECEIVED_CODEX_STEP1.json` | `A033STEP2-PRIVACY-025` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/REPORT_B.md` | `A033STEP2-PRIVACY-026` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/REQUEST_CODEX_REVIEW.md` | `A033STEP2-PRIVACY-027` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/RESULT_A2B033_STEP2.json` | `A033STEP2-PRIVACY-028` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/SHA256SUMS.json` | `A033STEP2-PRIVACY-029` | PASS，私有标记及凭据命中0 | 最终序列化字节；记录不作循环自哈希，清单/Git绑定 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/SOURCE_RECEIPT.json` | `A033STEP2-PRIVACY-030` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/STEP2_AUTHORIZATION.json` | `A033STEP2-PRIVACY-031` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/STRUCTURE_AND_BOUNDARY.json` | `A033STEP2-PRIVACY-032` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/SYNTHETIC_CLEAN.json` | `A033STEP2-PRIVACY-033` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/SYNTHETIC_CLEAN_LOG.txt` | `A033STEP2-PRIVACY-034` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/SYNTHETIC_FIRST.json` | `A033STEP2-PRIVACY-035` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/WINDOW_POISON_CHECK.json` | `A033STEP2-PRIVACY-036` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/core.py` | `A033STEP2-PRIVACY-037` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/csv_projection.py` | `A033STEP2-PRIVACY-038` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/fit_ledger.py` | `A033STEP2-PRIVACY-039` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/predict.py` | `A033STEP2-PRIVACY-040` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/privacy_check.py` | `A033STEP2-PRIVACY-041` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/requirements.txt` | `A033STEP2-PRIVACY-042` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/test_033.py` | `A033STEP2-PRIVACY-043` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |
| `docs/handoff_20261019_A2B033_STEP2_B_V1/train.py` | `A033STEP2-PRIVACY-044` | PASS，私有标记及凭据命中0 | 原始字节SHA256与字节数 |

隐私扫描JSON自身与SHA清单的最终序列化字节在落盘前也经过同一个扫描函数，不因“扫描后才生成”漏扫。扫描JSON的实际SHA由SHA256SUMS.json绑定；SHA清单的自身SHA由固定Git提交与外部回取凭证绑定。两个元数据记录不伪造循环自哈希，因此记录内sha256/bytes写null，属于哈希位置说明，不是免扫。其余文件均逐项记录原字节SHA与字节数。全部最终字节回取后再次比较并扫描，保留本地完整回取凭证。

所有原始赛事文件仅校验字节、不解压；私有配置、原清单及归档读取前后摘要一致。只持久化聚合命中计数，不写匹配标记、原始行、逐井数据或标签。

原源码容器FROZEN_SOURCES.json还逐项解码检查10个原始源码文件，核对原始字节SHA；不是只扫描JSON转义文本。每项记录见PRIVACY_SCAN_RAW.json的decoded_source_container_entries。

| 容器内部文件 | 扫描记录 | 结果 |
|---|---|---|
| FROZEN_SOURCES.json :: src/oil_uplift/__init__.py | A033-INNER-SOURCE-001 | PASS |
| FROZEN_SOURCES.json :: src/oil_uplift/a2b013_safe.py | A033-INNER-SOURCE-002 | PASS |
| FROZEN_SOURCES.json :: src/oil_uplift/training.py | A033-INNER-SOURCE-003 | PASS |
| FROZEN_SOURCES.json :: src/oil_uplift/multistep.py | A033-INNER-SOURCE-004 | PASS |
| FROZEN_SOURCES.json :: src/oil_uplift/models.py | A033-INNER-SOURCE-005 | PASS |
| FROZEN_SOURCES.json :: src/oil_uplift/scoring.py | A033-INNER-SOURCE-006 | PASS |
| FROZEN_SOURCES.json :: src/oil_uplift/config.py | A033-INNER-SOURCE-007 | PASS |
| FROZEN_SOURCES.json :: src/oil_uplift/io.py | A033-INNER-SOURCE-008 | PASS |
| FROZEN_SOURCES.json :: src/oil_uplift/exceptions.py | A033-INNER-SOURCE-009 | PASS |
| FROZEN_SOURCES.json :: src/oil_uplift/submission.py | A033-INNER-SOURCE-010 | PASS |
