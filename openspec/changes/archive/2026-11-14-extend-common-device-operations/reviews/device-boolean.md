# 真机属性结果返修代码检视

Claude Code CLI --model claude-opus-5-5 --effort high
Session fae0f980-a891-491f-8dc0-b98c626123a2

**结论：不通过。有 1 个阻断。**

**阻断：property 为非可哈希值时 `to_dict` 会抛异常（`hylyre/scenario/results.py:243`）**

- 判断条件 `facts.get("property") in BOOLEAN_PROPERTIES` 是拿值去查一个 `frozenset`。如果 `property` 是 list，就会抛 `TypeError: unhashable type: 'list'`，走不到脱敏。
- 前面的处理会把 list 原样保留下来：`ActionObservation.to_dict` 调用的 `_plain`（`hylyre/api/outcome.py:66-67`）会把 list/tuple 统一转成 list，`build_step_result` 不做规整。
- 所以本轮新增的回归用例 `("get_component_property", ["checked"], False)`（`tests/unit/test_selector_identity_redaction.py:510`）会在 `step.to_dict()` 处抛 `TypeError`，到不了 `== "[REDACTED]"` 的断言，测试必挂。
- 在线上，一行畸形的 observation 就会让整份 trace/report 序列化失败，而不是被脱敏后正常输出。
- 改法（一行）：先确认是字符串再查集合：`isinstance(facts.get("property"), str) and facts["property"] in BOOLEAN_PROPERTIES`。改完后该用例应能如预期得到 `[REDACTED]`。

**其余核实项都没问题：**
- `true`/`false` 保留类型：只有同时满足 kind、operation 都是 `get_component_property`、property 在 6 个布尔属性内、value 本身是 `bool` 时，才把原值写回 `facts.value`。trace/report 都经过 `StepResult.to_dict`，这条路径已覆盖。测试用 `is value` 断言，12 种组合都在。
- 豁免没有扩大：
  - 文本类 property（`text`）：仍是 `[REDACTED]`，取值为 `False` 时也一样；
  - 字符串 `"false"`：仍是 `[REDACTED]`；
  - 其他操作（`other_query`）：仍是 `[REDACTED]`；
  - `target.text`：仍是 `[REDACTED]`，测试也断言了 `SECRET` 不会出现在输出里。
- 写回只覆盖 `safe_outcome["observation"]["facts"]["value"]` 这一个字段。`observation`、`facts` 这两个键名不会被判成敏感字段，所以写回路径存在，也不会把其他字段带出来。`raw_dict` 和原始 `self.outcome` 都没有被改动。

**范围说明：**
- "返回值"一侧（API/CLI/MCP 直接返回的结果）不在 `results.py` 里，按你的要求这次没有审。
- 以上结论全部靠读代码得出，没有运行测试。
- 当前会话处于 plan 模式，这次只做只读检视，所以没有写 plan 文件，也没有改代码。
