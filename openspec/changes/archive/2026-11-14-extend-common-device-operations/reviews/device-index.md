# 真机等待索引返修代码检视

Claude Code CLI --model claude-opus-5-5 --effort high
Session c46f7da0-4d5c-4a06-81b3-9cc8844065dd

**结论：通过，没有阻断，也没有直接回归。** 只读了代码，没有执行命令，也没有跑测试。

逐项核对（`selector_resolve.py:1036-1047` 的 `allow_empty` 分支，以及 `selector_ops.py:281/297`）：

1. **完整谓词零候选**：`checked`/`index` 等过滤全部应用后，`ordered` 为空才返回 `[]`。所以 `wait_gone` 得到真 absence，`wait_for` 得到 `assertion.mismatch`。测试 `:636` 用 index 0/1/99 覆盖了 for 和 gone 两种情况。
2. **非法索引**：`_validate_selector_predicate` 在搜索候选之前就会拒绝负数、`bool`、字符串和浮点索引（`:930-936`），走不到 `allow_empty` 分支，失败类型是 contract（测试 `:668`）。
3. **有候选但越界**：只有 `not ordered` 时才放行。候选非空但越界时仍抛 `SelectorResolutionError`，失败类型是 selector，`observation` 为 `None`，不会被当成 absence（测试 `:658`、`:693`）。
4. **非等待场景的原有语义**：`allow_empty` 默认 `False`，`resolve_one`、`resolve_action_one`、`scroll`、`touch` 这些路径都没有传它，行为不变（测试 `:688`）。
5. **属性不可观测**：`_filter_match` 先过身份匹配，再调 `property_value`，属性缺失或不是布尔值时抛 `CapabilityUnsupported`，结果是 blocked。这个异常不受 `allow_empty` 影响，不会被当成 absence（测试 `:157`）。
6. **多候选时的证据**：带 index 时返回的就是被选中的那一项，`property_observations` 也来自这一项（测试 `:696` 中选中的是 `second`）。零命中时，诊断用的身份候选查询会先 `pop("index")`，避免把 index 套到另一个谓词上。不带 index 的多个匹配会判为 `ambiguous` 加 mismatch，不会判成 absent（测试 `:677`）。

**不阻断的观察**：如果在轮询过程中列表缩短，导致 `0 < 候选数 <= index`，比如 `index:1` 时两项消失了一项，这一轮会立刻以 selector 失败结束，不会继续等。这和第 3 条"有候选但越界不算 absence"的设计一致，所以不算回归。如果以后要把"第 N 项消失"当作 absence，需要另外定义这个语义。
