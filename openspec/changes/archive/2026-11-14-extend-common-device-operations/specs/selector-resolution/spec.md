## ADDED Requirements

### Requirement: Shared boolean property filters
选择器 SHALL 增加 checked/checkable/focused，连同 clickable/enabled/scrollable 共用属性读取及类型归一化；显式 true 和 false 均为精确过滤，字段未给才不约束。字段 SHALL 贯通预检、选择器 request、节点转换、过滤与所有使用选择器的入口。

#### Scenario: False filter is not omitted
- **WHEN** wait_for 选择 by_id=x 且 checked=false
- **THEN** 仅实际可观测 checked=false 的目标匹配；目标不存在或 checked=true 不匹配

#### Scenario: Missing observation cannot prove absence
- **WHEN** 节点符合身份谓词但请求的 checked 属性无法观测
- **THEN** 明确能力缺失或读取失败，不默认 false，也不让 wait_gone 因缺属性而通过

#### Scenario: Disappearance differs from false state
- **WHEN** wait_gone 使用 checked=true 且目标实际消失
- **THEN** 可按现有 absence 语义通过，但不宣称目标仍存在或 checked=false

### Requirement: Input and observed boolean normalization
系统 SHALL 只接受 JSON 布尔作为选择器输入；读取侧 SHALL 把原生/dump 的 true/false 布尔或字符串归一化为布尔，其它值或缺失标记不可观测。过滤、属性查询和状态设置 SHALL 共用三态读取。现有 _attr_bool 的缺失即 false 行为仅适用于原有二态用途，如点击排序和祖先查找。

#### Scenario: String observation differs from string input
- **WHEN** dump 返回 checked="false" 而选择器 checked=false
- **THEN** 可以匹配；反之选择器 checked="false" 在预检拒绝
