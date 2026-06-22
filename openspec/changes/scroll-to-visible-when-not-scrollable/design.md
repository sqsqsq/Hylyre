## D1: 容器发现与 scrollable 解耦

`find_container_root` 仅 `_selector_matches`；`find_scroll_root` 仍用于 swipe。

## D2: 已可见短路前置

每轮先 `find_container_root` + 子树 resolve + pre-lift 全树兜底，再 `find_scroll_root` 决定是否 swipe。

## D3: List→Scroll 回退门控

仅 `container is None` 时在 `i==0` 降级 `swipe_area` 到 Scroll；指定 `in` 时不跨容器降级。

## D4: resolve + native fallback

`for` 循环外；双门控 `container is None` + 纯 `by_text`（`visible` 不计入富字段）：先 resolve 重试，再 `UiDriver.locate_by_text`（Hypium `BY.text`）；`scroll_to` + `tap:true` 仍失败时 agent 层 `touch(by_text=…)`（与 touch 一致）。

## D5: tap-center 安全

`finalize_tap_hit` / `pick_best_tap_hit`：跳过零面积 lift；回退匹配 Text center；pre-lift 多候选经 `_sort_hits` 排序。
