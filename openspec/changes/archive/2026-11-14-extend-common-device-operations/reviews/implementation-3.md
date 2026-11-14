# 代码最终复核

CLI 调用 `claude -p --resume daf1a389-3417-410e-b259-09efbe163c93 --model claude-opus-5-5 --effort high --output-format json --tools Read,Grep,Glob --permission-mode plan --strict-mcp-config`，通过 stdin 提供本轮范围。
响应模型 claude-opus-5-5
Session daf1a389-3417-410e-b259-09efbe163c93

**代码检视通过，无阻断问题。**

- **判定方式：** `hylyre/api/selector_ops.py:274` 只有在谓词里出现 `checked`、`checkable` 或 `focused` 时才关闭升父。用的是 `has_boolean_filters`（`component_properties.py:13`），会递归检查 `all` 和关系锚点里的嵌套条件。
- **旧写法：** `by_text` 加 `clickable:true`，以及 `all:[by_text, by_type:ListItem]`，在 wait_for/wait_gone 里仍然升父，选中的是 parent。测试见 `tests/unit/test_common_device_operations.py:590-602`。
- **新状态约束：** 含 checked、checkable、focused 的写法（包括嵌套在 `all` 里）改用实际匹配的子节点。测试见 `:605-618`。
- **匹配与证据语义一致：** 判断是否命中（`:281`）和生成 `property_observations` 证据（`:297`）用的是同一个 `lift_text`。状态约束和 clickable/type 混用时，必须由同一个节点同时满足，不会把子节点的状态和父节点的类型拼在一起。测试见 `:621-631`。
- **数据组件：** get_component_property、clear_text、set_checked 仍然不升父（`common_operations.py:65`）。
- **文档：** CHANGELOG 第 7 行、`docs/common-device-operations.md:113`、`docs/agent-loop.md:215,217` 都已和代码一致。

还有一处小变化，不算阻断：旧写法里只要带了 `clickable` 这类布尔条件，现在也会附加 `property_observations` 证据。真机 dump 里只有合成根节点的这类属性是空字符串，而它已被排除，所以不会因此误报能力缺失。

本轮只读了代码和文档，没有执行任何命令，也没有操作设备。
