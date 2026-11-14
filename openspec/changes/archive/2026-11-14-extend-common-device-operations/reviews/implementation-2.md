# 返修定点复核

claude-opus-5-5 --effort high
Session daf1a389-3417-410e-b259-09efbe163c93

# B1–B4 定点复核结论

**结论：B1–B4 和三项顺带修复都已通过。** 但 B4 的返修引入了 1 个直接回归，需要先处理，所以本轮还不能整体放行。

## 已通过

- **B1（pinch 方向）：** pinch 方向现在只接受 diagonal 和 horizontal，见 `hylyre/api/common_operation_contract.py:135`。vertical 在连设备前就被拒绝，测试见 `tests/unit/test_common_device_operations.py:446`。
- **B2（错误分类）：** 以下情况都改成了 `contract.invalid_step`，`step_builder.py:162` 已有对应映射：
  - 坐标超出屏幕或区域、区域没有边界：`hylyre/api/common_operations.py:75`、`:83`、`:90`
  - set_checked 目标不可勾选：`common_operations.py:112`
  - clear_text 目标不是输入框：`hylyre/drivers/hypium/common_operations.py:166`
- **B3（set_checked 点击后复读）：** 点击之后的复读异常会被完整捕获，结果是 failed 加 `state_confirmation_failed`，并保留 `performed=true`、`before`、`changed=true`、`after=null` 和 `confirmation_error`，不会再落成 blocked，见 `common_operations.py:118-132`。测试见 `:488-503`。
- **B4（组件目标不再升父）：** 组件目标传 `lift_text=False`，读、清、设都作用在实际匹配的文本节点上，见 `common_operations.py:65`。点击仍然升父，测试见 `:516-553`。
- **空根节点：** `_is_dump_container` 只排除"深度 0、有子节点、type 为空或 Root、无身份信息、布尔属性全部不可观测"的合成根，见 `selector_resolve.py:712-719`。真机 `initial-ui.json` 的根节点 type 为 `""`，符合这个条件。真实节点缺属性时仍然报能力缺失，测试见 `:556-566`。
- **三键组合：** 只有确认是 OpenHarmony 才允许，其他情况一律报 capability，不会静默丢掉第三个键，见 `drivers/hypium/common_operations.py:148-160`。
- **has_app：** shell 失败时抛 `ConnectionError`（`:196`），会归为 `infrastructure.transport_failure`（`step_builder.py:174`）。

## 阻断：B4 返修的直接回归

**问题：** 所有 rich 选择器的 wait_for/wait_gone 现在都不升父了，不只是属性等待。旧用法会出现误判，wait_gone 可能直接假通过。
- **代码位置：** `hylyre/api/selector_ops.py:279`、`:296` 无条件传了 `lift_text=False`。
- **复现：** 用测试里的 `nested_control_tree()`，即 `ListItem(clickable=true)` 下面挂 `Text("张三", clickable=false)`。
  - `{"wait_for":{"by_text":"张三","clickable":true,"timeout":0}}`：旧行为升到 ListItem，判为存在；现在拿 Text 节点判断，结果不匹配，wait_for 失败，同样的谓词放在 `wait_gone` 里会立刻通过。
  - `{"wait_for":{"all":[{"by_text":"张三"},{"by_type":"ListItem"}]}}`：同样失效。这正是 `docs/agent-loop.md:215` 写明的旧语义："by_text 先抬升，再对抬升后的目标应用谓词"。
- **文档对不上：** `docs/common-device-operations.md:113` 只说"属性等待"不升父，CHANGELOG 也没把这条列为兼容变化。
- **建议修法（任选其一）：**
  1. 只有谓词（含嵌套）里出现 checked/checkable/focused 时才用 `lift_text=False`，其余 rich wait 保持升父。
  2. 保留现在的行为，但在 CHANGELOG、`agent-loop.md:215` 和 `common-device-operations.md` 里写明兼容变化，并补一条 `by_text + clickable` 的 wait 回归测试。

## 非阻断提示

- **等待时遇到无 bounds 节点：** 不升父模式下，匹配到 bounds 无法解析的节点会抛 `contract.invalid_step`（`selector_resolve.py:1011-1012`）。这条路径现在也覆盖 wait_for/wait_gone，原来是跳过该节点。真实 dump 里很少出现，但这算 UI 观测结果，归成契约错误不够准确。
- **新操作的 area 也不升父：** area 走 `component=True`（`common_operations.py:80`），用 `by_text` 定位 area 时取的是文本节点自身的边界。这和旧 `swipe.area` 的升父语义不一致，建议在文档里写一句。
- **三键的真机确认：** `get_os_info` 读取 `const.product.software.version` 的第一个词，测试机实际返回的是不是 `OpenHarmony` 需要真机确认。即使不是，也只会报 capability，属于 fail-closed，不算缺陷。

本轮只用了 Read/Grep，没有运行任何命令，也没有连设备。
