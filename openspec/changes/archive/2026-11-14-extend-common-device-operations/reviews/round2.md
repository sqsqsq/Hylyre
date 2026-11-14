# Claude Code CLI 第二轮定点复核

调用沿用首轮并添加 --resume 6a5a30f0-eb18-4f3f-ade0-525b80025aed；--model claude-opus-5-5 --effort high。

实际响应模型：claude-opus-5-5

## 结论：有 1 个阻断项

这次只读了你指定的 design.md、tasks.md 和两份 spec，没有读其它源码，没有跑测试，没有碰设备，也没有改文件。B1/B2/B3 的内容都已修好，Migration 说明也已补上。唯一的阻断是本次编辑放错了一个 Scenario 的位置，属于机械性问题。

### 逐项结论

| 项 | 结论 | 依据 |
|---|---|---|
| **B1 统一切分** | **内容已修复** | design.md:84 写全了规则：先去掉反引号或围栏包装；只有以 `{` 开头的片段，在对象深度大于 0 时才跟踪字符串和转义；对象外面和自然语言照旧按中英文分号及换行切分；自然语言里的引号不会进入 JSON 字符串状态；非法原始换行仍按 JSON 错误拒绝。上轮提的四个样例都已列入，并要求预检与执行结果相同。tasks.md:16 和 scenario-runner/spec.md:11 一致。 |
| **B2 布尔输入与读取归一** | **已修复** | design.md:45、selector-resolution/spec.md:18-23、tasks.md:17 三处一致：输入只接受 JSON 布尔；读取侧把布尔和字符串 `"true"`/`"false"` 归一为布尔；其它值或缺失视为不可观测。Scenario 写明 dump 里的 `checked="false"` 能匹配选择器 `checked=false`，选择器写 `checked:"false"` 在预检被拒绝。和 design.md:47 的"未知不得默认 false"没有冲突。 |
| **B3 touch 正例** | **已修复** | design.md:106 和 tasks.md:53 一致：touch 正例是 `mode=double`，long 由 `press_time=3` 的边界用例覆盖，normal 复用已有 tap 回归证据，不加第三条 touch 真机用例。design.md:108 里"所有类型的能力成功须有支持设备正例"现在没有冲突：normal 是旧行为，不算新能力。 |
| **可选：false 行为变更** | **已说明** | design.md:124 的 Migration Plan 写明：显式 false 从原先被忽略改为精确过滤，调用方需要删掉该字段，并要求在变更说明里列出。和 design.md:11 的"旧调用保持默认行为"不冲突，因为显式 false 不属于默认行为。 |

### 阻断项

**S1｜新加的自然语言切分 Scenario 挂到了错误的 Requirement 下**
- 位置：specs/scenario-runner/spec.md:25-27
- 问题：`#### Scenario: Legacy natural language splitting` 写在 `### Requirement: Offline observations remain honest`（第 17 行）后面。OpenSpec 把 Scenario 归到它前面最近的 Requirement 下，所以它成了"离线观测诚实"的场景，而不是"JSON command text remains intact"（第 10 行）的场景。archive 合入主 spec 后，B1 的自然语言验收会落在不相关的需求下面，离线需求也会多出一个无关场景。
- 最小修复：把第 25-27 行整体移到第 15 行之后（放在 `Shell contains separators` 场景后面、第 17 行 Requirement 之前），并删掉第 23-24 行多余的空行。
- 验收：第 10 行那个 Requirement 下有两个 Scenario（`Shell contains separators` 和 `Legacy natural language splitting`）；第 17 行 Requirement 下只剩 `Offline application query`；`openspec validate extend-common-device-operations --strict` 通过。

### 可选建议（不阻断）
- selector-resolution/spec.md:19 的"只接受 JSON 布尔"也会作用到已有的 clickable/enabled/scrollable。上轮看过，现有过滤只认 `is True`，所以像 `"clickable":"true"` 这种字符串写法以前很可能是被静默忽略的；改后会在预检被拒绝。现在的预检是否已经拒绝它，这次按要求没有去核实。如果确实属于行为变化，建议在 design.md:124 的例外里补上"字符串布尔改为预检拒绝"一句。