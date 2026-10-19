# A2B-033/步骤2审计问题清单

## CODEX-033-S2-01 — P1 — 未关闭

问题：README向.venv安装依赖，但训练/推理用裸python且未激活环境，新机器不能保证使用同一依赖环境。

证据位置：B README.md第14–15、23–24、30行及末段合成测试命令；SHA为0ac4f6d9d5f0d1895da4a3a7aefe1396dc49271ec53b150e221101fc1f1703ae；PUBLIC_CODE_TO_PRIVATE_PACKAGE.json证明随包同字节；A的README_INTERPRETER_PROBE_CODEX.json给出纯合成反例。

影响：R11②第4项完整复现命令，本版代码包不能进入上传批准；不否定现有模型/结果及B已完成的实际复现记录。

建议修复：按独立补丁统一使用环境解释器，B经用户批准后另存新代码包；不改算法、私有策略、模型与result.zip，不重训。

验证：检查新README逐条命令的解释器一致，--help/合成探针验证无需拟合；核对新代码包仅README变更，模型和result.zip摘要仍相同；刷新映射/清单/扫描后由A复核。

状态：A2B-033-R11-FIX-01待用户决定；补丁只在A目录，未合并；未关闭。

## 继承事项

HIST-DTYPE — P1，UNKNOWN，R5用户例外继续继承：缺历史逐文件加载身份；不补造旧摘要，不在本次关闭。

PLATFORM-B0-BINDING — P2，UNKNOWN：86.2003与当时实际上传包SHA未绑定；已有本地归档SHA不能替代平台记录。

PLATFORM-APPROVAL — P3，待另行批准：即使修复复核通过，也不自动上传平台或指定最终版本。

原步骤1为3/5正向弱信号，R11明确偏离授权仅允许步骤2，不追认原门槛通过。
