## ADDED Requirements

### Requirement: MCP and session coverage of extended operations
MCP SHALL 提供 design.md 操作工具及 run_steps 批量入口，输入输出为 JSON 数据；会话模式 SHALL 复用相同操作执行与结果构建，不跨设备降级。

#### Scenario: Serialized gesture in session
- **WHEN** MCP 经指定会话发送多指轨迹
- **THEN** 点序及参数完整传递到指定设备，返回公共结果 envelope
