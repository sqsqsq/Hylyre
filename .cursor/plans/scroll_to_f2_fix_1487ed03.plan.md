---
name: scroll_to F2 fix
overview: 针对 v3 F2：Scroll scrollable=false 时 find_scroll_root 为 None，指定 in 时已可见短路被跳过。核心修复是 find_container_root + 前置短路；保留 List→Scroll swipe 回退；native 回退仅 container=None。0.3.1 patch。
todos:
  - id: openspec-change
    content: 新建 OpenSpec change scroll-to-visible-when-not-scrollable：容器匹配不要求 scrollable；已可见短路在滚动前；native 回退仅无 in 时
    status: completed
  - id: find-container-root
    content: collect_cmd.py 新增 find_container_root（仅 _selector_matches）；find_scroll_root 保留专用于 swipe
    status: completed
  - id: scroll-until-visible
    content: 重构 scroll_until_visible：container_selector / swipe_area 分离不互染；前置 find_container_root 短路；滚动段保留 List→Scroll fallback（i==0）；解除 scroll_root=None+break 死路径
    status: completed
  - id: resolve-api
    content: resolve_first_hit_match_center_in_container（pre-lift center 判定；lift 越界回退 text center）；子树命中 hits[0] 通常安全，备注后续可统一 tap-center
    status: completed
  - id: native-fallback
    content: for 循环**之后**（含 break 路径）纯 by_text 原生 BY.text 回退；双门控 container is None + 无富字段；指定 in 时找不到则报错
    status: completed
  - id: visible-pred
    content: _apply_scroll_to_block 纯 by_text pred 设 visible=True
    status: completed
  - id: unit-tests
    content: 主回归 scrollable=false；次回归 pre-lift sibling + lift-center-outside；container=None 已可见 swipes==0；native 回退 gate 测；复跑 3 旧用例
    status: completed
  - id: docs-release
    content: 更新 agent-loop/agent-plan-a；bump 0.3.1 + build_wheel + pytest + openspec validate
    status: completed
isProject: false
---

# scroll_to 已可见目标修复（F2 · v3 → 0.3.1）— 修订版 v2

## 一句话定性

真机根因：`Scroll scrollable: "false"` → `find_scroll_root` 为 `None` → 指定 `in` 时第 0 轮 `break`，0.3.0 兜底从未执行。核心修复：`find_container_root` + 已可见短路前置；**须保留 List→Scroll swipe 回退**；**native 回退仅 `container is None`**。

## 背景与根因（TC-013-step-0）

- Scroll `bounds=[0,285][1320,2036]`，`scrollable: "false"`；整树无 `scrollable: "true"`。
- 目标 Row+Text「华为支付」center `(660,1743)` 已在 Scroll 内。
- 死路径见 [`selector_ops.py:232-252`](hylyre/api/selector_ops.py)：`scroll_root is None` + 指定 `in` → 直接 `break`（实际 0 swipe，报错写 after 15 scrolls）。

## 修复方案

### 3.1 新增 `find_container_root`（根因 A）

[`collect_cmd.py`](hylyre/cli/commands/collect_cmd.py)：`find_container_root` 仅 `_selector_matches`，**不要求 scrollable**。`find_scroll_root` 保留，专用于 swipe。

### 3.2 重构 `scroll_until_visible`（根因 B · 核心）

[`selector_ops.py`](hylyre/api/selector_ops.py)：

**变量分离（审阅 ④）**：不原地改写 `scroll_area`。

```python
container_selector = dict(container) if container else None
swipe_area = dict(container) if container else {"by_type": "List"}

for i in range(max_scrolls):
    tree = ...

    # (1) 已可见短路 — 与 scrollable 无关
    if container_selector is not None:
        croot = find_container_root(tree, container_selector)
        if croot is not None:
            hits = resolve_targets(croot, target_pred)
            if hits:
                return hits[0]  # 审阅③：子树 lift 通常受 croot 约束；若发现越界再统一 tap-center
            if i == 0:
                hit = resolve_first_hit_match_center_in_container(
                    tree, target_pred, _scroll_root_bounds(croot))
                if hit is not None:
                    return hit
    else:
        hits = resolve_targets(tree, target_pred)
        if hits:
            return hits[0]

    # (2) 滚动决策 — 仍要求 scrollable
    scroll_root = find_scroll_root(tree, swipe_area)
    # 审阅①：保留 List → Scroll 回退（原 L233-235）
    if scroll_root is None and i == 0 and container_selector is None:
        swipe_area = {"scrollable": True}  # type: ignore[assignment]
        scroll_root = find_scroll_root(tree, {"by_type": "Scroll"})
    if scroll_root is None:
        break
    await ...swipe(swipe_area, scroll_root)...
```

**TC-013**：`find_container_root` 找到 Scroll(scrollable=false) → 子树命中 → 0 swipe 返回。

### 3.3 tap-center 安全（pre-lift 路径）

[`selector_resolve.py`](hylyre/api/selector_resolve.py) `resolve_first_hit_match_center_in_container`：

- 容器判定：**匹配节点 pre-lift center**；
- 返回 tap：lift 后 center 越出容器 bounds → **回退 text center**。

### 3.4 原生回退（审阅 ② · 门控 + 落点）

**放在 `for` 循环之后**（不在循环体内），使 `break` 路径（如无 scrollable root、0 swipe）也能到达：

```python
for i in range(max_scrolls):
    ...
    if scroll_root is None:
        break
    await swipe...

# 循环外：双门控
if container is None and _is_pure_by_text(target_pred):
    return await _native_by_text_hit(agent, target_pred)  # 对齐 agent.py:164-173
raise SelectorResolutionError(...)
```

**硬性门控**：**仅 `container is None`**。指定 `in` 时 → **报错**，禁止全屏误点（与 `only-searches-inside-list` 一致）。

### 3.5 `visible=True` 一致性

[`_apply_scroll_to_block`](hylyre/api/agent.py) 纯 `by_text` pred 设 `visible=True`。

## 测试

| 用例 | 目的 |
|------|------|
| **`test_scroll_visible_when_container_not_scrollable`**（主） | scrollable=false + 真机 bounds；swipes==0，center==(660,1743) |
| **`test_scroll_pre_lift_bounds_when_target_sibling_of_croot`**（次） | 目标为 croot **sibling**（非子树），强制走 pre-lift 分支 |
| **`test_scroll_pre_lift_bounds_when_lifted_center_outside`**（次） | lift 越界 → tap 回退 text center |
| **`test_scroll_visible_when_container_none`**（补） | 无 `in`、目标已可见 → swipes==0（根因 B else 分支） |
| **`test_scroll_native_fallback_only_without_container`**（门控） | 指定 in + 容器内无目标 + 屏外同名 → **报错/不 swipe**，不 native 误点 |
| **`test_scroll_list_fallback_to_scroll`**（审阅①） | container=None、页仅 Scroll 无 List → i==0 回退后能 swipe 找到目标 |
| 3 个旧用例 | only-searches-inside-list / immediate-in-container / sibling-of-scroll |

## OpenSpec / 文档 / 发布

- Change：**`scroll-to-visible-when-not-scrollable`**
- Spec delta：容器匹配不要求 scrollable；已可见短路在滚动前；native 回退仅无 `in`；**行为收紧**：指定 `in` 时不再跨容器 List→Scroll 降级（见实现备忘①）
- 文档：目标已在容器/屏内时直接命中，即使容器不可滚；native 回退语义与 `in` 约束
- **0.3.1** + build_wheel + pytest + openspec validate
- 下游 TC-013：`scroll_to` 干净写法真机 0 swipe 验收

## 风险与回退

| 风险 | 缓解 |
|------|------|
| 外部同名误命中 | 容器子树 + bounds + pre-lift center；only-searches-inside-list |
| 重构丢 List→Scroll 回退 | 审阅①：显式保留 L233-235 逻辑 + 单测 |
| native 回退破坏 `in` 语义 | 审阅②：仅 container=None；门控单测 |
| swipe_area 被 fallback 改写污染 container 匹配 | 审阅④：container_selector / swipe_area 分离 |
| 子树 hits[0] lift 越界 | 审阅③：通常受 croot 约束；pre-lift 路径有 tap-center 回退 |

## 实现备忘（审阅 v3 · 非阻塞）

1. **List→Scroll 回退门控 = 有意收紧（相对 0.3.0）**：`container_selector is None` 时才做 List→Scroll 降级。原 L233-235 在指定 `in:{by_type:List}` 但页只有 Scroll 时也会滚 Scroll；新版尊重用户 `in` 范围，不再跨容器降级。Spec delta 须写明，避免后续当回归。
2. **native 回退落点**：必须在 `for` 循环**外**（见 3.4），否则 `container=None` + 无 scrollable + `break` 时走不到 native。
3. **命名**：`_scroll_root_bounds(croot)` 实际取任意容器节点 bounds；实现时可 rename 为 `_node_bounds`（可选，非必须）。

## 不在本次范围

- 修改 `_lift_tap_target` 全局策略
