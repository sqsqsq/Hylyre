# Agent 循环模式（无运行态 VLM）

外部 Agent（Cursor、Claude、内部编排器等）承担「看图 / 读控件树 → 规划 JSON → 断言」；Hylyre 负责 **真机执行 + 报告产物**。与 [做法 A：JSON 测试步骤](./agent-plan-a.md) 的区别：循环模式 **逐步** 探测界面再执行；做法 A 适合 **事先已知** `by_id` / `by_text` 的回归计划。

更多：**[app-knowledge.md](./app-knowledge.md)**（页面快照仓、`find`、指纹、存储路径解析）。

## Knowledge-first loop（已知 App）

对 **反复调试同一 bundle** 时，在每次 **`dump-ui` 整树** 之前：

1. **`hylyre app page load --bundle <id> --name <slug>`**（或 MCP **`hylyre_app_page_load`**）：若命中缓存，可直接把 **`tree` / `key_elements`** 交给 planner。
2. **`hylyre app find --bundle <id> --by-text "…"`**（或 **`hylyre_app_find`**）：在已 **`save`** 过的索引里反查 selector，无需当前设备 dump。
3. **仅在缓存缺失或指纹不匹配时**再 **`dump-ui`**；需要大图时可加 **`--filter-*` / `--summary`** 缩小 JSON。
4. **探索到新稳定页面后**执行 **`hylyre app page save`**（或 MCP **`hylyre_app_page_save`**），并可选 **`--auto-fingerprint`**，便于下次 **`app page diff --against current`** 判断是否漂移。

Framework / CI 请固定 **`--store-dir`** 或 **`HYLYRE_APP_STORE_DIR`**，与 Cursor 默认 `./.hylyre/apps` 区分开。

## UI 事实源（dump-ui 实现）

真机上 **`hylyre dump-ui`** / MCP **`hylyre_dump_ui`** 使用 **Hypium `UiTree.refresh()`**，底层走设备侧 **`uitest dumpLayout`**（由 Hypium 拉起），落地为 JSON 控件树。无需单独配置 `hdc uitest` 子命令；仅需 `hylyre[device]` + 可用 `hdc` 设备。

## 双轨制（强 CLI / 弱 MCP）

每一项能力 **先** 有 CLI（`execute_*` + Typer），**再** 由 MCP 工具薄壳调用同一套 `execute_*`。**CLI session**：`hylyre session start` 启动后台进程并在 `127.0.0.1` 上暴露 JSON-RPC（令牌写入会话 JSON）；原子命令传 **`--session` / `-S`** 即可复用 Hypium 连接。**MCP**：`hylyre_open_session` / `hylyre_close_session` 在同一 MCP 进程内复用 `HylyreAgent`（与 CLI session 文件无交集）。

### CLI 典型循环

1. **控件树**（非多模态 Agent）：  
   `hylyre dump-ui --out tree.json`  
   （长时间原子循环可加 **`--session`**，见下文「CLI Session daemon」。）
2. **截图**（多模态 Agent）：  
   `hylyre screenshot --out shot.jpeg`（可加 **`--session`**）
3. **原子步骤**（单行 planned JSON）：  
   `hylyre run action --json "{\"action\":{\"type\":\"touch\",\"by_text\":\"登录\"}}"`  
   或 `hylyre run tap` / `hylyre run input`（根键分别为 `touch` / `input`）、**`hylyre run swipe`** / **`hylyre run scroll`**（根键分别为 `swipe` / `scroll`，见下文）。  
   **Tier A（导航 / 等待 / Toast）**：**`hylyre run back`** / **`home`** / **`stop-app`** / **`clear-app`** / **`wait`** / **`wait-for`** / **`wait-gone`** / **`wait-idle`** / **`assert-toast`** / **`start-app-step`**（各需 **`--json`**，schema 见 [做法 A §2.1](./agent-plan-a.md)）。上述命令均支持 **`--session`**。
3b. **批量步骤**（同一会话一条进程跑多步）：  
   `hylyre run --steps-file nav.json --session …`（或 **`--steps '[ … ]'`**），可选 **`--on-fail abort|skip`**；与 **`--plan` 互斥**。可选 **`--bundle`/`--page-name`/`--wait-time`**：在步骤前先 **`start_app`**。输出结构化 JSON（stdout；或 **`--out` / `-o`** 写文件）。不落 `test-report.md`/`trace.json` —— 仍需 CI / Skill 6 时请用 **`run --plan`**。
4. **启动应用**（可选，三种方式勿混用）：  
   - **Runner 级冷启**（整份 `--plan` 开始前一次）：`hylyre run --plan … --bundle com.example.app`  
   - **原子 CLI**（无 JSON 信封）：`hylyre run start-app --bundle com.example.app`（支持 **`--session`**）  
   - **计划内一步**（与其它 JSON 步骤并列）：`hylyre run start-app-step --json '{"start_app":{"bundle":"com.example.app"}}'`  
   一次性会话需在 `session start` 时传入相同的 `--mock-port` / `--lyrebird-url`。
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
- `hylyre_run_action` / `hylyre_run_tap` / `hylyre_run_input` / **`hylyre_run_swipe`** / **`hylyre_run_scroll`**
- **Tier A**：**`hylyre_run_back`** / **`hylyre_run_home`** / **`hylyre_run_stop_app`** / **`hylyre_run_clear_app`** / **`hylyre_run_wait`** / **`hylyre_run_wait_for`** / **`hylyre_run_wait_gone`** / **`hylyre_run_wait_idle`** / **`hylyre_run_assert_toast`** / **`hylyre_run_start_app_step`**（payload 根键与 [做法 A](./agent-plan-a.md) 一致）
- **`hylyre_start_app`**：原子启动（CLI 旗标式，非 planned JSON 根键）
- **`hylyre_run_steps`**：一次传入 `steps` 数组（与单步相同根键），减少 MCP 往返；可选 **`failure_dir`**（绝对路径，session 模式同样生效）；或 CLI **`run --steps-file`**
- **`hylyre_run_scroll_to`**：滚到目标可见（planned 根键 `scroll_to`）；Tier A 工具亦支持可选 **`failure_dir`**
- **`hylyre_collect_list`**：在半屏列表里滚到底并合并所有可见 **`Text`** 行（可选正则过滤）；等价 CLI：`hylyre collect-list`
- **`hylyre_find`**：当前屏控件树扁平查找；返回 **`hits`** + 根级 **`_hylyre_hints`**（与 `dump-ui` 同源滚动信号），便于不走整树 dump 时仍能判断是否该转 **`collect-list`**。
- **`hylyre_app_page_*`** / **`hylyre_app_find`** / **`hylyre_app_fingerprint`**：App 知识持久化（见 **[app-knowledge.md](./app-knowledge.md)**）
- `hylyre_report_begin` → `hylyre_report_record`（传入 `trace_state` JSON）→ `hylyre_report_finalize`
- 可选：`hylyre_open_session` 后把同一 `session_id` 传给上述工具，减少重复连接。

## CLI Session daemon（性能）

每条独立的 `hylyre` CLI 进程默认 **connect → 操作 → disconnect**；Hypium/HDC 链路可能带来 **约 10–12s** 的固定开销。**会话模式**把连接保持在后台 daemon，原子命令只付操作耗时：

1. `hylyre session start [--device-sn SN] [--mock-port P] [--session-file path]`  
   成功后打印会话 JSON 路径（默认 `./.hylyre/session.json`）。
2. 后续在同目录执行：`hylyre dump-ui -o t.json --session .hylyre/session.json`、`hylyre run --steps-file nav.json --session …`、`hylyre run swipe ... --session ...`、`hylyre collect-list --session ...`、`hylyre screenshot -o s.jpeg --session ...` 等。
3. `hylyre session stop`（或向 daemon 发 `shutdown` RPC）结束并删除会话文件。
4. `hylyre session status` 打印 `{alive, pid, ping_ok, …}` JSON。

首次连接设备若长时间无响应，daemon 进程会在 **180s**（可用环境变量 **`HYLYRE_SESSION_CONNECT_TIMEOUT`** 覆盖，单位秒）后失败退出，避免离线设备无限挂起。

与 **MCP `session_id`** 的关系：**互不共用文件**；编排若在 Cursor 里且已 `open_session`，用 MCP 工具即可；若在 shell / CI 里拼多条 CLI，优先 **`session start` + `--session`**。

## dump-ui `_hylyre_hints`

`dump-ui` / `hylyre_dump_ui` 在 JSON **根级**附带 **`_hylyre_hints`**（planner 可读，不参与 Hypium 原生 schema）：

- **`scrollable_containers`**：`scrollable=true` 且类型为 `Scroll` / `List` / `Grid` / `WaterFlow` 的节点摘要（`bounds`、`origBounds`、`id`、`key`）。
- 若 **`origBounds` 底部明显大于裁剪后的 `bounds`**，标记 **`likely_more_content_below`**（暗示列表可能未展示完全）。

当任务涉及 **「列出全部 / 计数 / 核对清单」** 且 hints 提示有更多内容时：**优先 `hylyre collect-list`**（或按下列滚动手动 loop），不要仅凭首张 dump 下结论。

## `collect-list`（列表完整性）

对匹配到的滚动容器执行 **`swipe` UP（限定 `area`）→ `dump-ui` → 文本去重合并**，直到连续 **`--max-stable-rounds`** 轮无新增 **`Text`** 行或达到 **`--max-scrolls`**：

- **CLI**：`hylyre collect-list [--session FILE] [--scroll-by-type Scroll] [--scroll-by-id …] [--item-pattern REGEX] [--reset-to-top] [--bidirectional] [--out merged.json]`
- **MCP**：`hylyre_collect_list`，参数 `session_path`（CLI 会话文件）或 `device_sn`（一次性连接）；可选 **`reset_to_top`**、**`bidirectional`**、**`early_bounce_break`**。

默认收集 **`Text`** 叶节点字符串；**`--item-pattern`** 对 `id|key|text` 拼接串做正则过滤。

**输出字段补充**：结果 JSON 含 **`iterations_up`** / **`iterations_down`** / **`iterations_reset`**（仅在 **`--reset-to-top`** 时可能 >0）以及 **`reset_to_top` / `bidirectional` / `early_bounce_break` 布尔**，便于排查「滚了几轮、是否在相位重置」。

**何时加 `--reset-to-top`**：进入半屏 Sheet / 列表后 **滚动位置不确定**（例如从中间状态 resume），先在 **`Scroll` 限定区域内**反复 **`DOWN`** 直到可见 **`Text` 指纹稳定**，再执行常规 **`UP` 合并**，减少漏掉视口上方条目。

**何时加 `--bidirectional`**：在完成 **`UP` pass** 后，再从当前位置 **`DOWN` 合并一轮直到稳定**，用于补齐 **`UP` 起始位置之上**曾落在屏外的项（与 **`reset-to-top`** 互补：`reset` 偏向先到稳定顶端，`bidirectional` 偏向双向扫一遍）。

**默认**：`reset_to_top` / `bidirectional` 均为 **false**，与旧版一致。

**半屏 Bottom Sheet**：进入后列表通常已在**顶端**，不要默认传 **`reset_to_top`** / **`bidirectional`**，否则易在半屏内反复 **DOWN** 触边回弹。若 **`_hylyre_hints`** 里目标 **`Scroll`** 无 **`likely_more_content_below`**，多表示当前视口已含列表全部可见项。

**`--early-bounce-break`（默认开） / MCP `early_bounce_break`**：一次滑动后若下一帧 dump 的可见 **Text** 指纹与滑前相同（触边未滚动），立即结束该方向；需旧版「只靠连续 **`max_stable_rounds`** 轮无新行才停」时用 **`--no-early-bounce-break`**。

## 导航 / 等待 / Toast（Tier A）

Hypium 系统级能力与等待类步骤，根键与 [做法 A §2.1](./agent-plan-a.md) 一致；**`hylyre run --plan`** / **`hylyre_run_steps`** / MCP **`hylyre_run_*`** 均支持。

| 能力 | CLI | MCP | 说明 |
|------|-----|-----|------|
| 系统 / Nav 返回 | `hylyre run back --json '{"back":{}}'` | `hylyre_run_back` | **Nav 子页 pop 优先用 `back`**，不要用全屏 **`swipe RIGHT`** 冒充返回。可选 **`times`**、**`mode":"swipe"`**（边缘滑）。 |
| Home 键 | `hylyre run home --json '{"home":{}}'` | `hylyre_run_home` | 回桌面 / 宿主 |
| 结束进程 | `hylyre run stop-app --json '{"stop_app":{"bundle":"…"}}'` | `hylyre_run_stop_app` | 硬重置会话 |
| 清应用数据 | `hylyre run clear-app --json '{"clear_app":{"bundle":"…"}}'` | `hylyre_run_clear_app` | 冷态数据 |
| 固定等待 | `hylyre run wait --json '{"wait":{"seconds":1.5}}'` | `hylyre_run_wait` | 秒数 |
| 等元素出现 | `hylyre run wait-for --json '{"wait_for":{"by_text":"…","timeout":10}}'` | `hylyre_run_wait_for` | 四选一 selector |
| 等元素消失 | `hylyre run wait-gone --json '{"wait_gone":{"by_text":"…"}}'` | `hylyre_run_wait_gone` | 同上 |
| 等 UI 空闲 | `hylyre run wait-idle --json '{"wait_idle":{"timeout":10}}'` | `hylyre_run_wait_idle` | Hypium `wait_for_idle` |
| 断言 Toast | `hylyre run assert-toast --json '{"assert_toast":{"text":"…"}}'` | `hylyre_run_assert_toast` | 无 VLM 时常用于轻量反馈用例；**`on_unsupported":"skip"`** 时整条标记 **「跳过」**（见下文） |

**典型 Nav 循环**（进子页后回 Tab）：`dump-ui` → 确认在子页 → **`{"back":{}}`** → 再 `dump-ui` / **`find`** 确认 Tab 文案（如「首页」）出现 → 继续 **`touch`**。

**禁止**在 test-plan 中使用 **`{"action":{"name":"back"}}`**；应写 **`{"back":{}}`** 或 **`{"action":{"type":"back"}}`**。

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
- **`at`**：可选；**在半屏模态里与 `swipe.area` 同理**：应指向模态内的 **`Scroll`**（或稳定 **`by_id`**）。**省略且无顶层 `x`/`y` 时**：先读 **`_hylyre_hints.scrollable_containers`**，在第一个可滚动容器中心滚动；若无容器则回退 **屏幕中心比例 `(0.5, 0.5)`**（仍可能落在 Sheet 外，半屏场景仍建议显式 **`at`**）。CLI：`--at-by-type Scroll` 等。
- **`key1` / `key2`**：可选，透传 Hypium 组合键场景

示例：

```bash
hylyre run scroll --json "{\"scroll\":{\"direction\":\"down\",\"steps\":6}}"
```

在 **`hylyre run action`** 里使用 **`{"action":{"type":"swipe",…}}`** / **`{"action":{"type":"scroll",…}}`** 时，字段与 **根键 `swipe` / `scroll`** 的内层对象相同（与 `type` 并列）。**`{"action":{"type":"touch",…}}`** 亦支持富选择器字段（与根键 `touch` 相同）。**`hylyre run swipe` / `run scroll`** 则要求 JSON **根键**分别为 **`swipe` / `scroll`**。批量 **`hylyre run --plan`** 的「测试步骤」列支持上述两种写法（规约见 [做法 A](./agent-plan-a.md)）。

## `scroll_to`（滚到目标）

根键 **`scroll_to`**：在容器子树内循环 **dump → 解析目标 → 容器内 swipe**，直到命中或达到 **`max_scrolls`**（指纹稳定/回弹时提前终止）。可选 **`tap:true`** 找到后点击。指定 **`in`** 容器时，第 0 次若子树未命中，会在全树中查找 **center 落在容器 bounds 内** 的目标并立即返回（避免对已可见项空滚；容器外同名不会短路）。

```bash
hylyre run scroll-to --json '{"scroll_to":{"by_text":"招商银行","in":{"by_type":"List"},"max_scrolls":15,"tap":true}}'
```

MCP：**`hylyre_run_scroll_to`**（payload 根键须含 `scroll_to` 或整步对象，与 Tier A 其它工具一致）。

**`touch.scroll_into_view`**：内联等价——先滚到可见再点，例如 `{"touch":{"by_text":"招商银行","scroll_into_view":{"by_type":"List"}}}`。

### AlphabetIndexer（A–Z 索引）

长列表若带 **`AlphabetIndexer`**（如全部银行页），可先 **点字母** 再 **`scroll_to`/`touch` 目标行，不必盲滚到底：

```json
{"touch":{"by_text":"Z","within":{"by_type":"AlphabetIndexer"}}}
{"scroll_to":{"by_text":"招商银行","in":{"by_type":"List"},"tap":true}}
```

## 富选择器语义（Agent 必读）

**`by_text` 默认**走 **`dump-ui` + `resolve_targets` + 坐标点击**（不用「原生先行再兜底」——同名按钮在半模态场景下原生会静默点到背后项）。**`x`/`y`/`by_id`** 仍走 Hypium 原生；**`by_key`** 走解析器坐标。

排序：**overlay 越靠上越优先** → **`clickable`** → **`enabled`** → 树序。多命中时默认取第一个，并写 **候选摘要** 到日志/`SelectorResolutionError`。

- **文本抬升**：匹配到 `Text` 叶节点后，向上找最近 **`clickable=true` 或 `enabled` 祖先** 作为点击目标。
- **`all` (AND)**：`by_text` 先抬升，再对抬升后的目标应用 `by_type`/`clickable` 等谓词。
- **`scope:"top_overlay"`**：启发式取最上层 Sheet/Dialog/Popup 子树（HarmonyOS `bindSheet` 场景）。
- **`wait_for` / `wait_gone`**：含富字段时轮询 dump+解析；纯单属性仍走 Hypium `wait_for_component`。
- **`input`**（0.3.0+）：`by_type`/`by_key`/富字段或 **`into`** → 解析 → **touch 聚焦** → **当前光标输入**；仅 `by_text`/`by_id`（无富字段）走原生；无选择器时落当前聚焦框。

逃生：**`prefer_native_text:true`** 恢复旧 `by_text` 原生行为。

字段表见 [做法 A §2.1.1](./agent-plan-a.md)。

## Toast 断言与「跳过」

**`assert_toast`** 在本层自有轮询，并捕获 Hypium **`check_toast`** 异常，避免失败截图路径 **`NoneType`** 崩溃。

```json
{"assert_toast":{"text":"操作成功","timeout":3,"on_unsupported":"skip","poll_interval":0.3}}
```

**`on_unsupported":"skip"`** 时抛 **`StepSkipped`**，全链路（plan / `--steps-file` / MCP batch）映射为 **「跳过」**，**`resolved_outcome` 不计失败**（与 [`report-sections.yaml`](../hylyre/contracts/report-sections.yaml) 一致）。

## 步骤失败诊断（`--failure-dir`）

**`hylyre run --plan`** / **`run --steps-file`** / MCP **`hylyre_run_plan`** / **`hylyre_run_steps`** 支持 **`failure_dir`**（CLI **`--failure-dir`**；默认 report 同级 **`failures/`**）。

步骤异常时 **best-effort** 写入：

- `failure_dir/step-<n>.json` — 当时 UI 树
- `failure_dir/step-<n>.png` — 截图

诊断自身异常会被吞掉，不掩盖主错误；路径摘要写入 batch **`diagnostics`** / trace **`cases[].notes`**。

**Session 模式**：`run --steps-file --session …` 经 daemon 透传 **绝对路径** 写盘（CLI 与 daemon 同机）。

Tier A 单步工具（如 **`hylyre_run_scroll_to`**）可选 **`failure_dir`**；原子 **`hylyre_run_tap`/`hylyre_run_scroll`** 不在此范围。

## 自然语言未约定手势时：默认策略（Agent 必读）

用户只说「点到某页后数有几条」「列出名称 / 信息」等，而 **未写要不要滑、往哪滑** 时，执行端 **不得** 在无依据的情况下默认连续滑动并直接下结论。推荐纪律如下：

1. **先到目标页后做一次 `dump-ui`（或截图）**，建立当前可见事实；**禁止**在尚未读树的前提下默认「必须滑很多次」。
2. **只有当你能从控件树（或截图）推断列表可能被截断、存在虚拟化、或业务上条目数与可见节点明显不符时**，才补充 **`swipe` / `scroll`** / **`collect-list`**；推断依据示例：**`_hylyre_hints.likely_more_content_below`**、卡片/行 **`bounds` 贴屏幕底边**、同类 **`ListItem` 数量偏少**、文案暗示「还有更多」等。
3. **竖向列表要露出视口下方尚未展示的条目**：在 Hypium 文档语义下，应在列表所在的 **`Scroll` 上使用 `direction: UP`**（控件内「上滑」）。**勿把口语「往下浏览」直接映射成参数 `DOWN`**，除非你已经核对 Hypium 在该页面上的实际矢量含义。
4. **半屏模态 / Bottom Sheet**：列表滚动 **必须** 使用 **`swipe.area` / `scroll.at`**（常用 **`by_type: Scroll`**，多 `Scroll` 时改用 **`by_id`/`by_key`**）限定在浮层内列表；**禁止**依赖未限定 `area` 的全窗竖滑，以免关掉 Sheet。
5. **滑动后必须校验**：对比 **相邻两次 `dump-ui`** 中与列表相关的节点或文案集合；**若无变化**，不得假设「列表仅有当前可见项」——应 **调整方向、`area`、`distance`**，或改用 **`scroll`**，直至树发生变化或合理判定已滚到底。
6. **若希望消除歧义**：在 **`test-plan.md`** 的步骤 JSON 中 **显式写出** `swipe`/`scroll`（[做法 A](./agent-plan-a.md)），避免由 Agent 静默猜测手势；或在上层编排（如 framework skill 6）对「全量枚举」步骤调用 **`collect-list`**。

## 选择器优先级

翻译用户意图时：**`by_id` > `by_text`（默认真机解析器路径）> 坐标**。坐标仅在前两者不可用时使用。半模态 / 同名按钮优先 **`scope:"top_overlay"`** 或 **`all` + `by_type`**（见上文 **富选择器语义**）。

## 何时仍需要 Hylyre 内置 VLM

仅当外部 Agent **既无法消费截图也无法消费控件树**，且仍要写 **自然语言步骤**（非 JSON）时，才配置 `HYLYRE_VLM_*` 并使用 `hylyre ai action` / **`hylyre_ai_*`** MCP 工具。默认推荐：**不配 VLM**，由外部 Agent + 本页的 dump-ui/screenshot 完成感知。
