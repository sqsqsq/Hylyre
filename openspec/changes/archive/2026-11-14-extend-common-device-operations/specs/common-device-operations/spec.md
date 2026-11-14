## ADDED Requirements

### Requirement: Touch modes and duration
系统 SHALL 在既有 touch 中支持 normal、long、double，保持默认 normal；long SHALL 调用 long_click，显式 press_time 原样传递，未给采用 2 秒；double 调用 touch(mode="double")；富选择器转坐标后走相同映射，保留点击后等待，其他模式 SHALL 拒绝 press_time。

#### Scenario: Long press with rich selector
- **WHEN** 使用富选择器并指定 mode=long、press_time=3
- **THEN** 唯一目标处执行按住 3 秒的长按；不能丢失 mode 或退化为普通点击

### Requirement: Directed and continuous gestures
系统 SHALL 支持 drag、slide、fling、pinch_in/out、two_finger_swipe、multi_finger_touch、gesture；端点沿用 {x,y} 屏幕绝对整数像素或富选择器，不新增 unit/比例坐标；area 不改变端点原点，所有端点在执行前验证。

slide SHALL 将可选 duration 映射为 slide_time（默认 0.3 秒），显式 speed 在设备调用前拒绝。fling.speed SHALL 为 fast、normal 或 slow 字符串，默认 fast。two_finger_swipe 与 multi_finger_touch 的可选 area SHALL 在适配层从唯一匹配控件的边界解析为 Rect，执行前校验屏幕端点。

#### Scenario: Continuous multi point gesture
- **WHEN** 提交一指包含三个连续点的 gesture
- **THEN** 适配层构造一个 Gesture 并调用一次 inject_gesture，中间不抬手。非法点在注入前拒绝

#### Scenario: Multiple finger paths
- **WHEN** 一条 gesture 包含多指轨迹
- **THEN** 适配层按每指构造 Gesture，将列表一次传给 inject_multi_finger_gesture

### Requirement: Keys and text editing
系统 SHALL 支持 press_key、press_combination_key、clear_text、move_cursor；组合键同时按下，清空使用原生清空语义，光标移动不得重新聚焦重置位置。

#### Scenario: Move cursor and insert
- **WHEN** 已聚焦文本框中向左移动光标后输入文本
- **THEN** 文本插入移动后的实际位置

### Requirement: Properties and assertions
系统 SHALL 保留 get_component_property，并以共享属性读取/类型归一化扩展选择器 checked/checkable/focused；属性断言复用 wait_for/wait_gone，不新增 assert_component 或 eq/ne。布尔 true/false 均须精确过滤；缺属性不得假装 false。

#### Scenario: Mismatch is assertion failure
- **WHEN** 属性读取成功但实际 checked=false、期望 checked=true
- **THEN** wait_for 的完整谓词不匹配，到期后按现有断言链失败，不以读取成功判为通过

### Requirement: Idempotent checked state
系统 SHALL 支持 set_checked，通过共享属性路径先读状态，必要时点击一次，再确认目标状态；不直接使用不能提供前后证据的 switch_component_status；非 checkable 或未知状态不得盲目点击。

#### Scenario: Already checked
- **WHEN** 当前 checked=true 且请求 checked=true
- **THEN** 不点击，返回 changed=false；不反向切换

### Requirement: Application observations and recent tasks
系统 SHALL 支持 current_app、has_app、recent_tasks；应用查询返回实际观测值而非猜测。

#### Scenario: Absent application
- **WHEN** 查询未安装的 bundle
- **THEN** 读取成功且 installed=false，不将不存在误作执行失败

### Requirement: Structured device shell
系统 SHALL 支持 shell command/timeout，保留 stdout、设备退出码与传输退出码，避免宿主 shell 解释。hdc 不透传设备码时 SHALL 用独立子 shell 加唯一尾标记解析并剥离包装部分，保留原始传输证据；标记缺失判失败而非成功。独立设备 stderr 不可得时 SHALL 返回 stderr_available=false、stderr=null，按真实标记验收；超时回收宿主进程并记录远端状态未知。

#### Scenario: Device command fails
- **WHEN** 设备命令输出固定文本到 stdout/stderr 并以非零退出
- **THEN** 输出保留且步骤失败；即使 hdc 自身返回零也不得报告成功
