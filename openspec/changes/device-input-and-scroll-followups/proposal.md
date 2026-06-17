## Why

Hylyre 0.2.0 已让 bc-openCard 真机 0 失败闭环，但 v2 验证仍暴露：`input` 只认 `by_text`/`by_id`（placeholder-only 的 `TextInput` 无法定位）；`scroll_to` 对已在屏内目标偶发空滚 15 次。

## What Changes

- `input` 支持与 `touch` 一致的富选择器及 `into` 一步式：解析坐标 → touch 聚焦 → 当前光标输入。
- `action.type=input` 整块下发 `_apply_input_block`（与 touch 一致）。
- `scroll_until_visible` 容器感知兜底：子树未命中时全树查找，但仅接受 center 落在 `scroll_root` bounds 内的命中。
- 文档与 0.3.0 发布元信息；下游 harness F3 追加到移交文档。

## Capabilities

### Modified Capabilities

- `api-agent`: `input` 富选择器 / `into`；`action.type=input` 富字段。
- `selector-resolution`: `scroll_until_visible` 容器感知兜底语义。

## Impact

- `hylyre/api/agent.py`, `hylyre/api/selector_ops.py`, 文档, `build_wheel.py`, `pyproject.toml` 0.3.0.
