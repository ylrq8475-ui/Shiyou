# A2B-021 范围内问题清单

本清单不替代 A 全项目历史问题清单；不重新打开 A2B-017 已关闭的锁定实施问题。

|编号|等级|问题与影响|证据位置|建议修复与验证|状态|
|---|---|---|---|---|---|
|A21-01|P0（继承）|事件段末月及次月起 12 月属于项目假设，官方语义尚未确认；影响锚点与标签窗口|payload/PLAN.json::cohort.boundary；a2b013_safe.py::segment_end_anchors/_build_train_panel|主办方确认业务事件、段首/末及预测起点；独立核对版本映射，不按分数选定义|未关闭|
|A21-02|P0（继承）|预测生成时点未获官方解释；影响当时信息可获得性，保守月前截止不能代替官方证明|a2b013_safe.py::_safe_history_values；execution/FINAL_RESULT.json::P0|保留保守边界，取得时点解释后审核字段时间；不能仅用榜单放行|未关闭|
|A21-03|P2（证据限制）|历史 dtype 摘要/身份链仍 UNKNOWN；75 项输入未随匿名包提供，影响完整历史身份声明，不是已发现漂移|IMPLEMENTATION_PRETRAIN_LOCK.json::source_and_input_files；A_INDEPENDENT_REVIEW.json|按本机许可只读验核既有私有/历史证据；缺少历史记录不补造，不上传原始输入|保留 UNKNOWN|
|A21-04|P2|最大可修复机制未识别；支持度、损失集中度和组均值不足以给因果结论|A_DATA_FINDINGS.json；MECHANISM_LEDGER.md|下一轮先锁定可否证机制、同边界对照及预算，诊断不等于训练授权|待研究，不阻断本轮收尾|
|A21-R1|P1（复测事项）|需独立检查本轮合成、聚合分数、资格与停止路径|A_SYNTHETIC_TESTS.log；A_CHECK_DETAILS.json；REPORT_A.md|40 项合成实际执行、独立算术与事件交叉绑定，确认均未达门槛且未升级|本轮有限范围复测完成；未证明真实重训|

未关闭继承 P0：2 项。当前范围新增未关闭 P1：0 项。范围外历史问题数量未在本轮全量清点，不以此表宣称全项目 P1 为 0。
