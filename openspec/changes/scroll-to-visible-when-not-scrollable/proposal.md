## Why

Hylyre 0.3.0 真机 TC-013：`scroll_to` 目标已在 Scroll 可视区内仍失败。根因是 HarmonyOS 一屏内容时 Scroll 报告 `scrollable: "false"`，`find_scroll_root` 为 `None`，指定 `in` 时已可见短路被跳过并直接 `break`。

## What Changes

- 新增 `find_container_root`：容器匹配不要求 `scrollable`。
- `scroll_until_visible`：已可见短路在滚动决策之前，不依赖 scrollable root。
- pre-lift 容器 bounds 兜底；List→Scroll swipe 回退仅 `container is None`。
- 指定 `in` 时不再跨容器 List→Scroll 降级（相对 0.3.0 有意收紧）。
- 纯 `by_text` 且无 `in` 时，循环外 native 解析回退。

## Capabilities

### Modified Capabilities

- `selector-resolution`: `scroll_until_visible` 容器发现与已可见短路语义。

## Impact

- `hylyre/cli/commands/collect_cmd.py`, `hylyre/api/selector_ops.py`, `hylyre/api/selector_resolve.py`, `hylyre/api/agent.py`
- 0.3.1 patch
