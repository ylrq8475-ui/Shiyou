# N1方案及层位字段表

账户B执行与交付。依据官方数据字典，原图字节摘要见DICTIONARY_SOURCE_RECEIPT.json。日期只有方案完工日期；其余日期类字段为否。仅字段定义及聚合，不含方案、层位原值。

| 文件角色 | 字段名 | 官方含义 | 单位 | 缺失含义 | 日期类 |
|---|---|---|---|---|---|
| plan | 井号 | 对应井史数据WELL_ID | / | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 完工日期 | 对应井史数据压裂日期 | 年/月/日 | UNKNOWN：官方字典未给出缺失业务解释 | 是 |
| plan | 层位 | 对应层位数据 | / | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 井段(喷枪深度)(m) | 井段（喷枪深度） | m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 砂岩射开厚度(m) | 砂岩射开厚度 | m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 有效厚度(m) | 有效厚度 | m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 渗透率(10-3μm2) | 渗透率 | 10^-3 μm² | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 上隔层厚度(m) | 上隔层厚度 | m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 下隔层厚度(m) | 下隔层厚度 | m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 目的层温度(℃) | 目的层温度 | ℃ | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 压裂方式 | 压裂方式 | / | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| plan | 石英砂用量(m3) | 石英砂用量 | m³ | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | WELL_ID | 井号 | / | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | XH | 序号 | / | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | CW | 层位 | / | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | YCZMC | 油层组名称 | / | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | XCH | 小层号 | / | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | XFCH | 细分层号 | / | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | XB | 相别 | / | 空值：非河道 | 否 |
| layer | SYDS | 砂岩顶深 | m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | SYDS1 | 砂岩底深 | m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | SYHD | 砂岩厚度 | m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | YXHD | 有效厚度 | m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | STL | 渗透率 | 10^-3 μm² | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | DCXH | 地层系数 | 10^-3 μm²·m | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | KXD | 孔隙度 | % | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | HSBHD | 含水饱和度 | % | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | SFSBHD | 束缚水饱和度 | % | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | CCCD | 采出程度 | % | UNKNOWN：官方字典未给出缺失业务解释 | 否 |
| layer | SYJSJG | 水淹解释 | / | 空白：未解释 | 否 |
| layer | SKQK | 射孔标记 | / | 空值：未射开 | 否 |
