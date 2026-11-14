## ADDED Requirements

### Requirement: Extended operation targets and validation
Agent SHALL 共用既有富选择器、唯一性、区域解析和预检；新增动作的坐标及属性目标遵循 design.md，不另建定位真源。

#### Scenario: Ambiguous drag endpoint
- **WHEN** 拖拽终点匹配多个控件
- **THEN** 触碰前拒绝并给出定位失败，不选择第一个

### Requirement: Shared observation semantics
Agent SHALL 区分查询动作、属性断言和状态设置，并复用相同属性读取逻辑。

#### Scenario: Missing property
- **WHEN** 底层没有提供请求属性
- **THEN** 明确能力缺失或读取失败，不制造 false 或空字符串
