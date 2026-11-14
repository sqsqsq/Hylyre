## Why

Hylyre 已覆盖基础点击、输入和滚动，但缺少长按、双击、拖拽、键盘及状态操作，导致常见 App 用例必须绕开统一执行与报告链。补齐已确认的高、中优先级能力及六项补充能力，使同一用例可以经计划、CLI、MCP 和会话一致执行并得到可信结果。

## What Changes

- 扩展 touch：normal / long / double，长按可指定时长。
- 新增拖拽、点到点滑动、快速抛滑、双指缩放、双指滑动、多指点击和单指/多指连续轨迹。
- 新增通用按键、组合键、Shell 执行和控件属性读取。
- 补充清空文本、移动光标、基于现有 wait_for/wait_gone 的属性过滤断言、确保勾选状态、当前应用/安装状态查询、进入最近任务。
- 所有操作贯通 JSON 计划、CLI、MCP、会话及现有结果协议；保持旧调用默认行为。
- 不包含亮灭屏/解锁专用入口、旋转、文件传输、卸载、录屏、模板图片匹配、鼠标全套、窗口管理、手写笔或触控板。通用 Shell/按键可执行相关底层命令，但不因此声称提供这些专用能力。
- 实施与验收状态见 tasks.md。

## Capabilities

### New Capabilities
- `common-device-operations`: 新增操作的输入输出、状态语义、能力限制和验收矩阵。

### Modified Capabilities
- `driver-hypium`: 扩展抽象及 Hypium 适配，诚实处理版本与设备能力差异。
- `api-agent`: 共用参数验证、目标解析、查询和断言语义。
- `scenario-runner`: 注册新增步骤并保持预检、执行和离线行为一致。
- `cli`: 提供新操作入口，保持批量与原子调用一致。
- `mcp-wrapper`: 提供 JSON 可序列化输入输出并复用公共执行链。
- `selector-resolution`: 扩展 checked/checkable/focused 与布尔 false 过滤，共享属性读取语义。
- `contracts`: 用现有结果协议承载查询值、基于现有 wait_for/wait_gone 的属性过滤断言和 Shell 结果。

## Impact

影响 hylyre/drivers、api、scenario、cli、mcp、session、contracts，相关 fake、测试、文档及消费方契约示例。以本机 Hypium 6.0.7.210 为已检查的接口基线，不无条件提高所有功能的最低版本，也不新增底层驱动依赖。设备 API 级别限制需单独识别；完整交付需真机验收，离线通过不能替代。
