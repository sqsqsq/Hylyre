## D1: input 走解析器 + touch 聚焦

Driver 契约不变（`input_text` 仅 `by_text`/`by_id`/当前光标）。Agent 层对 `by_type`/`by_key`/富字段/`into`：`dump_ui` → `resolve_one` → `touch(x,y)` → `input_text(text)`。

## D2: scroll_to 容器感知兜底

`i==0` 且指定 `in` 时：子树 resolve 失败后，全树 resolve 但过滤 `center ∈ scroll_root.bounds`，避免外部同名短路（保留 v1 回归语义）。
