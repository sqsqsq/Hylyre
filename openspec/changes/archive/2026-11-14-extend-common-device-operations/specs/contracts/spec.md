## ADDED Requirements

### Requirement: Extended operation result facts
系统 SHALL 复用现有 OperationOutcome/StepResult/builder/reducer 协议；查询记录 action observation.facts，属性断言沿用 wait_for/wait_gone 的 presence/absence 证据链，不新建 custom assertion 路径，Shell 保留输出及退出码。

#### Scenario: Query is not an assertion
- **WHEN** has_app 成功返回 installed=false
- **THEN** 查询动作成功但不增加断言覆盖或证明业务通过

### Requirement: Extended results retain verification compatibility
新增结果 SHALL 通过 schema、golden 与 report verify；能力缺失不得伪造成功，旧报告样本保持兼容。

#### Scenario: Capability blocked
- **WHEN** 设备缺少多指能力
- **THEN** 结果为 blocked/capability 且报告派生状态与 trace 一致
