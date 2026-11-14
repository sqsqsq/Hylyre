# 真机属性结果返修代码检视

Claude Code CLI --model claude-opus-5-5 --effort high
Session fae0f980-a891-491f-8dc0-b98c626123a2

**结论：通过，上轮那个阻断已解决。**

我重新读了磁盘上的 `hylyre/scenario/results.py:240-248`，和你贴的代码一致。

- 第 243 行新加的 `isinstance(facts.get("property"), str)` 放在集合查找（第 244 行）前面。`and` 会短路，所以 list、dict 这类非字符串的 property 直接判为不满足条件，不会再去查 `frozenset`，`TypeError` 不会再出现。
- 这类数据会走默认的 `redact_evidence` 结果，`facts.value` 保持 `[REDACTED]`，正好是回归用例 `("get_component_property", ["checked"], False)`（`tests/unit/test_selector_identity_redaction.py:510`）期望的结果。
- 豁免范围没有变化：多加一个条件只会让条件更严格，原来能保留的 6 个布尔属性的 `true`/`false` 照样保留，其他情况照旧脱敏。

这次复核只读了代码，没有运行命令。66 项测试通过是开发者那边的结果，我没有自己复跑。
