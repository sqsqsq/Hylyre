# Agent 循环模式（无运行态 VLM）

外部 Agent（Cursor、Claude、内部编排器等）承担「看图 / 读控件树 → 规划 JSON → 断言」；Hylyre 负责 **真机执行 + 报告产物**。与 [做法 A：JSON 测试步骤](./agent-plan-a.md) 的区别：循环模式 **逐步** 探测界面再执行；做法 A 适合 **事先已知** `by_id` / `by_text` 的回归计划。

## UI 事实源（dump-ui 实现）

真机上 **`hylyre dump-ui`** / MCP **`hylyre_dump_ui`** 使用 **Hypium `UiTree.refresh()`**，底层走设备侧 **`uitest dumpLayout`**（由 Hypium 拉起），落地为 JSON 控件树。无需单独配置 `hdc uitest` 子命令；仅需 `hylyre[device]` + 可用 `hdc` 设备。

## 双轨制（强 CLI / 弱 MCP）

每一项能力 **先** 有 CLI（`execute_*` + Typer），**再** 由 MCP 工具薄壳调用同一套 `execute_*`。例外：**`hylyre_open_session` / `hylyre_close_session`** 仅在 MCP 侧提供，用于 **复用 Hypium 连接**（性能/UX），**不增加** CLI 不具备的业务能力。

### CLI 典型循环

1. **控件树**（非多模态 Agent）：  
   `hylyre dump-ui --out tree.json`
2. **截图**（多模态 Agent）：  
   `hylyre screenshot --out shot.jpeg`
3. **原子步骤**（单行 planned JSON）：  
   `hylyre run action --json "{\"action\":{\"type\":\"touch\",\"by_text\":\"登录\"}}"`  
   或 `hylyre run tap` / `hylyre run input`（根键分别为 `touch` / `input`）、**`hylyre run swipe`** / **`hylyre run scroll`**（根键分别为 `swipe` / `scroll`，见下文）。
4. **启动应用**（可选）：  
   `hylyre run start-app --bundle com.example.app`
5. **增量报告**（草稿 trace → 最终报告）：  

```bash
hylyre report begin --feature myfeat --trace-out draft.json
hylyre report record --trace draft.json --case TC-01 --name "登录" --priority P0 --ac AC-01 --status 通过 --notes ""
hylyre report finalize --trace draft.json --report-out report.md --trace-out trace.json
```

无 `test-plan.md` 时，`hylyre report finalize` 之后的 **`hylyre report verify`** 可省略 `--plan`：

```bash
hylyre report verify --report report.md --trace trace.json
```

### MCP 典型循环（与上等价）

- `hylyre_dump_ui` / `hylyre_screenshot`（可选 `session_id`）
- `hylyre_run_action` / `hylyre_run_tap` / `hylyre_run_input` / **`hylyre_run_swipe`** / **`hylyre_run_scroll`** / `hylyre_start_app`
- `hylyre_report_begin` → `hylyre_report_record`（传入 `trace_state` JSON）→ `hylyre_report_finalize`
- 可选：`hylyre_open_session` 后把同一 `session_id` 传给上述工具，减少重复连接。

## 列表与滚屏（`swipe` / `scroll`）

真机 **`dump-ui`** 反映的是 **Hypium `UiTree` 当前快照**；长列表若做了 **虚拟化 / 懒渲染**，**未进入视口的条目往往不会出现在树里**。要数清列表项或点到下方条目，需要在同一页面上 **先滑动或滚轮滚动**，再 **`dump-ui`**（可反复：滑 → dump → 合并解析）。

| 能力 | CLI | MCP | 底层 Hypium | 说明 |
|------|-----|-----|----------------|------|
| 方向滑动手势 | `hylyre run swipe --json '…'` | `hylyre_run_swipe` | `UiDriver.swipe` | 方向 **`UP` / `DOWN` / `LEFT` / `RIGHT`**（大小写不敏感）。**横向列表用 `LEFT`/`RIGHT`**，不要用 `scroll`。 |
| 纵向滚轮式滚动 | `hylyre run scroll --json '…'` | `hylyre_run_scroll` | `mouse_scroll` | 方向仅 **`up` / `down`**（Hypium 限制）。 |

**`swipe` JSON**（根键 `swipe`，与 `hylyre run swipe` / `hylyre_run_swipe` 一致）常用字段：

- **`direction`**（必填）：`UP` | `DOWN` | `LEFT` | `RIGHT`
- **`distance`**：可选，默认 `60`；**1–100** 表示滑动长度占**滑动区域**高度或宽度的百分比（Hypium 语义）
- **`area`**：可选；**在半屏模态 / Bottom Sheet 内的列表上滚动时几乎必须指定**，否则 Hypium 会在**整窗**上做手势，`DOWN` 容易命中 Sheet 外区域从而 **关闭浮层**，而不是滚动列表。示例：`{"area":{"by_type":"Scroll"}}`（若页上有多个 `Scroll`，改用 **`by_id`** / **`by_key`** 精确到模态里的列表容器）。
- **`side`**：可选，`LEFT` | `RIGHT` | `TOP` | `BOTTOM`（粗粒度起始区域）
- **`start_point`**：可选，`[x, y]`，可为比例坐标（如 `[0.5, 0.8]`）
- **`swipe_time`**、**`speed`**：可选，与 Hypium `swipe` 一致

示例（**全屏页**、且无半屏浮层遮挡时，仍建议在列表 **`Scroll` 内**操作；若未限定 `area`，行为依赖 Hypium 默认区域）：

```bash
hylyre run swipe --json "{\"swipe\":{\"direction\":\"UP\",\"distance\":65}}"
```

**半屏模态 / Bottom Sheet**：不要在未限定区域时对 **`DOWN`**「盲滑」。请 **限定在列表 `Scroll` 上**，例如在 JSON 里写 **`swipe.area`**，或使用 CLI（合并进 payload，**覆盖** JSON 里的 `area`）。要露出**列表下方**未完整展示的条目，在 `Scroll` 内优先使用 **`UP`**（与 Hypium「控件内上滑」一致）：

```bash
hylyre run swipe --json "{\"swipe\":{\"direction\":\"UP\",\"distance\":55}}" --area-by-type Scroll
```

等价 MCP：`hylyre_run_swipe` 的 payload 内带上 **`"area":{"by_type":"Scroll"}`**（或 **`by_id`**）。若列表滚动仍不理想，可改用 **`mouse_scroll`**（`scroll` + **`at`**）：

```bash
hylyre run scroll --json "{\"scroll\":{\"direction\":\"down\",\"steps\":6}}" --at-by-type Scroll
```

**`scroll` JSON**（根键 `scroll`）常用字段：

- **`direction`**（必填）：`up` 或 `down`
- **`steps`**（必填）：整数 ≥ 1（滚轮「格数」）
- **`at`**：可选；**在半屏模态里与 `swipe.area` 同理**：应指向模态内的 **`Scroll`**（或稳定 **`by_id`**）。省略且无顶层 **`x`/`y`** 时，默认在 **屏幕中心比例 `(0.5, 0.5)`** 滚动，容易落在 Sheet 外。CLI：`--at-by-type Scroll` 等。
- **`key1` / `key2`**：可选，透传 Hypium 组合键场景

示例：

```bash
hylyre run scroll --json "{\"scroll\":{\"direction\":\"down\",\"steps\":6}}"
```

在 **`hylyre run action`** 里使用 **`{"action":{"type":"swipe",…}}`** / **`{"action":{"type":"scroll",…}}`** 时，字段与 **根键 `swipe` / `scroll`** 的内层对象相同（与 `type` 并列）。**`hylyre run swipe` / `run scroll`** 则要求 JSON **根键**分别为 **`swipe` / `scroll`**。批量 **`hylyre run --plan`** 的「测试步骤」列支持上述两种写法（规约见 [做法 A](./agent-plan-a.md)）。

## 自然语言未约定手势时：默认策略（Agent 必读）

用户只说「点到某页后数有几条」「列出名称 / 信息」等，而 **未写要不要滑、往哪滑** 时，执行端 **不得** 在无依据的情况下默认连续滑动并直接下结论。推荐纪律如下：

1. **先到目标页后做一次 `dump-ui`（或截图）**，建立当前可见事实；**禁止**在尚未读树的前提下默认「必须滑很多次」。
2. **只有当你能从控件树（或截图）推断列表可能被截断、存在虚拟化、或业务上条目数与可见节点明显不符时**，才补充 **`swipe` / `scroll`**；推断依据示例：卡片/行 **`bounds` 贴屏幕底边**、同类 **`ListItem` 数量偏少**、文案暗示「还有更多」等。
3. **竖向列表要露出视口下方尚未展示的条目**：在 Hypium 文档语义下，应在列表所在的 **`Scroll` 上使用 `direction: UP`**（控件内「上滑」）。**勿把口语「往下浏览」直接映射成参数 `DOWN`**，除非你已经核对 Hypium 在该页面上的实际矢量含义。
4. **半屏模态 / Bottom Sheet**：列表滚动 **必须** 使用 **`swipe.area` / `scroll.at`**（常用 **`by_type: Scroll`**，多 `Scroll` 时改用 **`by_id`/`by_key`**）限定在浮层内列表；**禁止**依赖未限定 `area` 的全窗竖滑，以免关掉 Sheet。
5. **滑动后必须校验**：对比 **相邻两次 `dump-ui`** 中与列表相关的节点或文案集合；**若无变化**，不得假设「列表仅有当前可见项」——应 **调整方向、`area`、`distance`**，或改用 **`scroll`**，直至树发生变化或合理判定已滚到底。
6. **若希望消除歧义**：在 **`test-plan.md`** 的步骤 JSON 中 **显式写出** `swipe`/`scroll`（[做法 A](./agent-plan-a.md)），避免由 Agent 静默猜测手势。

## 选择器优先级

翻译用户意图时：**`by_id` > `by_text` > 坐标**。坐标仅在前两者不可用时使用。

## 何时仍需要 Hylyre 内置 VLM

仅当外部 Agent **既无法消费截图也无法消费控件树**，且仍要写 **自然语言步骤**（非 JSON）时，才配置 `HYLYRE_VLM_*` 并使用 `hylyre ai action` / **`hylyre_ai_*`** MCP 工具。默认推荐：**不配 VLM**，由外部 Agent + 本页的 dump-ui/screenshot 完成感知。
