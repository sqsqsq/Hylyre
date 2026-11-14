## ADDED Requirements

### Requirement: Extended Hypium operation adaptation
驱动 SHALL 提供 common-device-operations 全部原语，按本机签名适配并明确设备限制；新增基类方法 SHALL 默认报告不支持，不破坏既有子类实例化。

#### Scenario: Unsupported custom drag time
- **WHEN** 设备不支持显式 drag.press_time
- **THEN** 返回 capability 不支持，不能忽略参数执行默认拖拽

### Requirement: Legacy driver behavior remains stable
驱动 SHALL 保持未指定 touch.mode 的旧点击及旧 HDC 调用的行为。

#### Scenario: Existing touch call
- **WHEN** 旧调用只传原有坐标或 selector
- **THEN** 执行普通点击并保留旧输出兼容
