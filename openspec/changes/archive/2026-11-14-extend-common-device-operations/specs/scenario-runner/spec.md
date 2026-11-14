## ADDED Requirements

### Requirement: Expanded planned operation coverage
Runner SHALL 注册 common-device-operations 全部根键和角色，预检与执行使用同一清单；非法参数在设备调用前拒绝。

#### Scenario: Invalid combination
- **WHEN** 计划中 touch.mode=double 同时给 press_time
- **THEN** 预检拒绝且没有设备动作

### Requirement: JSON command text remains intact
Runner SHALL 在公共契约阶段合并 plan_contract 与 runner 的重复切分为同一函数供预检/执行调用，去除既有反引号/围栏后，仅以 { 开始的片段在对象深度大于 0 时追踪 JSON 字符串/转义，对象内部不切分；其它文本沿用中英文分号及换行切分，自然语言引号不进入 JSON 状态。保留 JSON 字符串内部内容，兼容自然语言、包装和格式化 JSON。

#### Scenario: Shell contains separators
- **WHEN** shell.command 含分号及转义换行
- **THEN** 完整字符串只分派一次，不被拆成多条计划步骤

#### Scenario: Legacy natural language splitting
- **WHEN** 计划包含 点击A；点击B 或 点击"确定";返回
- **THEN** 预检与执行共用函数均得到两步，不因自然语言引号吞掉分隔符

### Requirement: Offline observations remain honest
Runner SHALL 保持模拟标识，无真实观测时查询/断言/set_checked/Shell 返回 blocked/capability。

#### Scenario: Offline application query
- **WHEN** --use-fakes 执行 has_app
- **THEN** 不得伪造 installed 值或真机通过结论
