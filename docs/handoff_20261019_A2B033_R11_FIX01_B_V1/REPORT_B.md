【交付登记卡】  
任务编号/阶段：A2B-033-R11-FIX-01 / README解释器命令最小修订  
角色：B 交付；账户B执行与交付  
分支：codex/a2b033-r11-fix01-b-20261019  
完整提交号（40 位）：0e179cc024c7c0a90a105fe0628dfd6e3d2a9585（结果固定快照，最终报告由固定链接与索引绑定）  
目录路径：docs/handoff_20261019_A2B033_R11_FIX01_B_V1  
结果文件路径（单个 JSON）：docs/handoff_20261019_A2B033_R11_FIX01_B_V1/RESULT_FIX01.json  
关键数字：模型拟合0，预处理拟合0，推理0；新旧包均25个成员，仅README.md改变，其余24项原字节相同；新版代码包2455821字节，SHA256=7767b7ca28bfbf0ad9e427942c8416be35053e1e9a32b8a1eed50478fff72c6b；result.zip仍3074字节，SHA256=9670e0d0bbea8e2720e53d032883f91900df65abe49b0da5c4642f755f3084de；模型SHA256=92534c2bd5f2f0d5e5167740b2a66e42c877a834dc22f1471a375c7a0e3e3ac1；旧代码包保留；累计模型/预处理各7次，未增加。  
硬门禁结论：泄漏 / 错位 / 井级隔离 / 指标 —— 通过 / 通过 / 通过 / 通过（继承原步骤2固定源码与已审证据；FIX01无新数据处理或评分，仅验证受保护成员字节不变）。  
UNKNOWN 与未关闭项：CODEX-033-S2-01 P1：README修订和新包身份已提交，待账户A2/Codex只读复核，B不关闭；HIST-DTYPE P1：历史加载身份链继续UNKNOWN；PLATFORM-B0-BINDING P2：历史86.2003实际上传包未独立绑定；PLATFORM-APPROVAL P3：未获上传或最终指定授权。  
对应决策表行（仅 Codex 填写）：不适用  
所依据的 Claude 指令存档提交号：012e9fe50efac3f051b48804bc724e39b703cc93（R11原授权，本次FIX另据当前用户明确批准，原文见AUTHORIZATION_FIX01.md）  
被修订B提交：47077ee354a784bdf99444dd19adb7a8dac36d80  
所依据的账户A2/Codex审核提交：3ed4d57337b3805a3b40457ff66dc45c7ecde8e4

# 账户B执行与交付：README命令已统一，待只读复核

原审查指出依赖安装使用`.venv`而训练/推理使用裸`python`，可能调用另一解释器。按照用户本次明确授权，Windows安装、训练、推理和合成检查的后续命令现在统一显式使用`.venv\Scripts\python.exe`，无需激活；Linux统一替换为`.venv/bin/python`。唯一保留的裸`python -m venv .venv`用于创建虚拟环境，说明要求使用Python 3.13.7，不是后续运行入口。

实际文档修改：1条train命令、2条predict命令、1条行内unittest命令替换解释器，并补充同一解释器的使用说明；参数、数据路径示例、输出位置、算法说明与其它文字不变。README_ONLY.diff提供完整差异；按逆替换可恢复旧README原字节。此处只核对命令链文本，没有执行任何训练、预处理或推理命令。

## 包身份与保留

| 文件 | 字节数 | SHA256 | 状态 |
|---|---:|---|---|
| 新版submission_code.zip | 2455821 | 7767b7ca28bfbf0ad9e427942c8416be35053e1e9a32b8a1eed50478fff72c6b | 本轮私有版本目录另存，CRC通过，<5GB |
| 旧版submission_code.zip | 2455727 | 75943e9244606400d3addd218589069a51519fc2a69af96f8f4633c6f15e241f | 原位置保留，字节不变 |
| result.zip | 3074 | 9670e0d0bbea8e2720e53d032883f91900df65abe49b0da5c4642f755f3084de | 原位置保留，字节不变，没有重生成 |
| 模型 | 2388987 | 92534c2bd5f2f0d5e5167740b2a66e42c877a834dc22f1471a375c7a0e3e3ac1 | 新旧ZIP内及原工件相同，没有加载或拟合 |

新旧ZIP的成员名、顺序和数量相同，25项中只有README.md内容改变。MEMBER_SHA256_COMPARISON.json逐项提供旧/新SHA与字节数，NEW_CODE_PACKAGE_MANIFEST.json提供新版全部成员身份。24项未变成员包含模型权重、模型回执、runtime_policy.json私有配置、requirements.txt、全部.py算法/入口源码、冻结源码容器及参数环境文件。只重写本轮新ZIP，旧包、旧目录和旧清单不覆盖。检查的81份既有文件全部字节不变，见PRESERVATION_CHECK.json。

## 验证范围、拟合计数与隐私

本轮模型拟合0、预处理拟合0、故障重试0、推理0，没有调用train.py、predict.py或合成ML入口。修订工具只使用Python标准库做文本、ZIP和SHA处理；隐私工具只做已授权材料的标记读取和文本扫描，无学习型预处理。原拟合计数记录未变，A2B-033累计模型/预处理各7次。README_COMMAND_CHECK.json是静态命令链检查，不冒充执行完整命令后的新训练验收。

此前步骤2的120行干净复现与linter结论，按[被审B提交](https://github.com/ylrq8475-ui/Shiyou/blob/47077ee354a784bdf99444dd19adb7a8dac36d80/docs/handoff_20261019_A2B033_STEP2_B_V1/REPORT_B.md)和[独立审核](https://github.com/ylrq8475-ui/Shiyou/blob/3ed4d57337b3805a3b40457ff66dc45c7ecde8e4/docs/handoff_20261019_A2B033_STEP2_CODEX_REVIEW_V1/RESULT_CODEX.json)继承，不宣称本轮重新执行了120行推理或干净训练。模型、结果、私有配置及算法逐字节不变是本轮复核依据。

每份本轮发布文件和最终元数据自身都有隐私扫描记录，原始证据与逐一对应见PRIVACY_SCAN_RAW.json和PRIVACY_COVERAGE_MAP.md。新版正式代码ZIP、权重、result.zip及私有配置不上GitHub；只发布README、差异、聚合身份与检查记录。原始赛事数据没有复制、解压或上传，未持久化任何逐井值。

## 复核与未关闭项

本交付是CODEX-033-S2-01的修订证据，不是B代替A2的关闭结论。其P1继续记录为待账户A2/Codex只读复核；历史HIST-DTYPE也不关闭。是否可进入上传批准仍由独立审核填写，本次upload_approval_ready=false，平台上传0。原步骤1的3/5弱信号和R11用户越过门槛记录保持原样。

账户A2/Codex仅需检查文档解释器链、25项成员的一改24不改、新包SHA与旧结果/模型身份、零拟合和隐私覆盖，不要求或授权重新拟合。转交请求见REQUEST_A2_CODEX_READONLY_REVIEW.md。结果固定快照：[RESULT_FIX01.json](https://github.com/ylrq8475-ui/Shiyou/blob/0e179cc024c7c0a90a105fe0628dfd6e3d2a9585/docs/handoff_20261019_A2B033_R11_FIX01_B_V1/RESULT_FIX01.json)。
