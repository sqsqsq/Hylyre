# 做法 A：Cursor / 外部 Agent 生成 test-plan（无运行态 VLM）

适合 **事先已掌握** 稳定 `by_id` / `by_text`（或可靠坐标）、要把一批用例固化成 `test-plan.md` 做回归的场景。若需要先读当前界面再规划步骤，请改用 **[Agent 循环模式](agent-loop.md)**（CLI 或 MCP 均可）。

目标：由 **Cursor Agent**（或其它 LLM）把用户的自然语言意图 **改写为 `test-plan.md` 里「测试步骤」列中的单行 JSON**，再用 `hylyre run` 在真机上执行。此时 **不需要** 配置 `HYLYRE_VLM_*` 去理解步骤（步骤已是结构化 JSON）。

> 解析与执行见 `hylyre/scenario/runner.py`：非 JSON 行会走 `ai_action`，必须带 VLM；**JSON 行**走 `run_planned_*`，只依赖 Hypium / 指纹设备。

## 1. test-plan.md 硬性格式

1. 必须存在标题 **`## 测试用例清单`** 或 **`### 测试用例清单`**（`plan_parse.parse_test_plan` 用该节定位表格）。
2. 表头必须为 **7 列**，顺序固定：

   `用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC`

3. 表头下一行是 markdown 分隔符（`| --- | --- | ...`）。
4. 示例骨架见仓库：`tests/e2e/fixtures/json-steps-test-plan.md`。

## 2. 「测试步骤」列：只放 JSON 行

- 每一**条**被执行的逻辑对应一行 **单行 JSON**（一行内不要换行）。
- **多条**步骤可在同一单元格里用 **英文分号 `;` 或中文分号 `；`** 分隔，解析器会先换成换行再逐条执行（见 `_iter_steps`）。
- 不要使用 `<br/>` 拆步骤：解析时 `<br/>` 会被替换成空格，多段 JSON 会粘在一起。
- **避免** 在任意列里出现未转义的 **竖线 `|`**：表格按 `|` 切列，会破坏 7 列对齐。JSON 里的文案若含 `|`，改用别表述或 `by_id`。
- **禁止** 用 markdown **反引号** 或 ` ``` ` 围栏包裹 JSON（如 `` `{"touch":…}` ``）；解析器会尽量剥离，但表格中应直接写裸 JSON。
- **禁止** 把 CLI 子命令名（`tap`、`swipe` 等）当作 JSON 根键；根键必须是下表中的 planned 键名。

**推荐写法（canonical direct 根键）**：优先 `touch` / `input` / `swipe` 等**直接根键**；`action` 信封与 direct 等价，任选其一即可。

### 2.1 允许的 JSON 根键（与 `HylyreAgent.run_planned_*` 及 `hylyre run --plan` 一致）

| 根键 | 含义 | 典型 payload |
|------|------|----------------|
| `touch` | 点击（推荐） | `{"touch":{"by_text":"充值"}}`、`{"touch":{"x":100,"y":200}}` |
| `input` | 输入（推荐） | `{"input":{"text":"hello","by_id":"field","by_text":null}}` |
| `action` | 单步动作（可选信封） | `{"action":{"type":"touch","by_text":"登录"}}`、`{"action":{"type":"input","text":"100","by_id":"amount"}}`、`{"action":{"type":"swipe","direction":"UP","distance":60,"area":{"by_type":"Scroll"}}}` |
| `input` | 输入 schema | `{"input":{"text":"hello","by_id":"field","by_text":null}}` |
| `swipe` | 方向滑动手势（Hypium `swipe`）；**半屏模态内需带 `area` 限定列表 `Scroll`**；竖向列表露出下方条目常用 **`UP`** | `{"swipe":{"direction":"UP","distance":55,"area":{"by_type":"Scroll"}}}` |
| `scroll` | 纵向滚轮式滚动（Hypium `mouse_scroll`） | `{"scroll":{"direction":"down","steps":6}}` |
| `scroll_to` | 在容器内滚到目标可见；可选找到后点击 | `{"scroll_to":{"by_text":"招商银行","in":{"by_type":"List"},"max_scrolls":15,"tap":true}}` |
| `back` | 系统 / Nav 栈返回（Hypium `press_back`；**不是**全屏 `swipe RIGHT`） | `{"back":{}}`、`{"back":{"times":2}}`、`{"back":{"mode":"swipe","side":"RIGHT"}}` |
| `home` | Home 键 / 回桌面 | `{"home":{}}` |
| `stop_app` | 结束应用进程（硬重置会话） | `{"stop_app":{"bundle":"com.example.app"}}` |
| `clear_app` | 清除应用数据 | `{"clear_app":{"bundle":"com.example.app"}}` |
| `wait` | 固定等待秒数 | `{"wait":{"seconds":1.5}}` |
| `wait_for` | 等待控件出现 | `{"wait_for":{"by_text":"钱包","timeout":10}}` |
| `wait_gone` | 等待控件消失 | `{"wait_gone":{"by_text":"加载中","timeout":10}}` |
| `wait_idle` | 等待 UI 空闲 | `{"wait_idle":{"timeout":10}}` |
| `assert_toast` | 断言 Toast 文案 | `{"assert_toast":{"text":"操作成功","timeout":3}}` |
| `start_app` | 计划内重启应用（区别于 runner 级 `--bundle`） | `{"start_app":{"bundle":"com.example.app","page_name":"EntryAbility"}}` |

`action.type` 除 `touch` / `input` / `swipe` / `scroll` 外，还支持上表 Tier A 类型名（如 `{"action":{"type":"back"}}`）。

`action.type` 为 `touch` 时还可带 `wait_time`（可选）。

### 2.1.1 富选择器（`touch` / `input` / `wait_for` / `wait_gone` / `scroll_to`）

除 **`x`/`y`/`by_id`**（仍走 Hypium 原生、唯一性强）外，**`by_text` 默认**经 **`dump-ui` → `resolve_targets` → 坐标点击**（避免半模态盖同名按钮时静默点到背后项）。**`by_key`** 同样走解析器坐标。

**`input`**（0.3.0+）：`by_type`/`by_key`/富字段或 **`into`** 子选择器 → 解析坐标 **`touch` 聚焦** → **`input_text` 落当前光标**（driver 契约不变）。仅 **`by_text` 或 `by_id`（无富字段）** 仍走原生 Hypium `input_text`。**无任何选择器**时输入落当前聚焦框（建议先 `touch` 聚焦）。

| 字段 | 含义 |
|------|------|
| `into` | 一步式定位对象，如 `{"into":{"by_type":"TextInput","scope":"top_overlay"}}` |
| `focus_wait` | 聚焦 touch 后等待秒数（默认 `0.15`） |
| `match` | `"contains"`（默认）或 `"exact"` |
| `visible` / `clickable` / `enabled` | 布尔过滤（`visible` 指 bounds 有面积；遮挡靠 overlay 排序） |
| `scope` | `"top_overlay"`：只在最上层 Sheet/Dialog/Popup 子树内匹配 |
| `within` / `below` / `above` / `after` / `before` | 相对锚点选择器（对象） |
| `all` | 子选择器数组（AND）；`by_text` 命中文本节点后 **抬升到可点祖先** 再与其余谓词组合 |
| `index` | 排序后候选列表的 0-based 索引 |
| `prefer_native_text` | `true` 时 `by_text` 回退旧行为（原生 Hypium，默认关） |
| `scroll_into_view` | 点击前先 `scroll_until_visible`（对象，如 `{"by_type":"List"}`） |

示例：

```json
{"touch":{"by_text":"下一步","scope":"top_overlay"}}
{"input":{"by_type":"TextInput","scope":"top_overlay","text":"123456"}}
{"input":{"into":{"by_type":"TextInput","scope":"top_overlay"},"text":"123456"}}
{"touch":{"all":[{"by_text":"下一步"},{"by_type":"Button"}],"scope":"top_overlay"}}
{"wait_for":{"by_text":"短信验证","scope":"top_overlay","timeout":10}}
{"scroll_to":{"by_text":"招商银行","in":{"by_type":"List"},"max_scrolls":15,"tap":true}}
```

**`assert_toast`** 另支持：

| 字段 | 含义 |
|------|------|
| `on_unsupported` | `"error"`（默认）或 `"skip"`：设备/版本不支持时整条步骤标记 **「跳过」**（非失败） |
| `poll_interval` | 轮询间隔秒数（默认 `0.3`） |

**`scroll`**：省略 **`at`** 且无顶层 **`x`/`y`** 时，会读 **`_hylyre_hints.scrollable_containers`** 自动取第一个可滚动容器中心；失败回退屏幕中心比例 `(0.5,0.5)`。

**`scroll_to`** 字段：`by_text`/`by_id`/`by_type`/`by_key`（目标）、`in`（容器选择器，可省略）、`max_scrolls`（默认 15）、`tap`（找到后是否点击，默认 false）。**已可见短路优先于滚动**：容器按 selector 匹配，不要求 `scrollable`；目标已在容器 bounds 内可见时立即命中（含 `scrollable: false` 的 Scroll）。指定 `in` 时先在容器子树匹配，未中则用匹配节点 center 做 bounds 兜底（多候选按 clickable 等排序）；lift 到零面积 clickable 时 tap 回退 Text center。指定 `in` 时不会对屏外同名做全局 resolve / native 回退。无 `in` 时循环外：resolve 重试 → `locate_by_text`（Hypium）→ `tap:true` 时最终 `touch(by_text=…)`。

**`swipe` / `scroll` / `action.type` 为 `swipe` 或 `scroll`** 的字段说明、列表虚拟化、半屏模态及 **`dump-ui`** 的关系，见 [`agent-loop.md`](./agent-loop.md) 中的 **列表与滚屏** 与 **自然语言未约定手势时** 两节。

### 2.2 `action.type`：`swipe` 与 `scroll`

与根键 **`swipe` / `scroll`** 等价，仅外层换成 `action` 信封：

- **`{"action":{"type":"swipe","direction":"LEFT","distance":50}}`**
- **`{"action":{"type":"scroll","direction":"up","steps":3,"at":{"by_type":"Scroll"}}}`**

字段名与 [`agent-loop.md`](./agent-loop.md) 中 **列表与滚屏**、**自然语言未约定手势时** 两小节一致。

### 2.3 批量：`hylyre run --steps-file`（无 `test-plan.md`）

已知多步 planned JSON 时，可用 **JSON 文件数组**批量执行。步骤对象根键与本节 2.1 相同；与 **`hylyre run --plan`** **互斥**。

**快速重放**（仅步骤结果 JSON）：

```bash
hylyre run --steps-file nav.json --session .hylyre/session.json --on-fail abort --out steps-result.json
```

**Skill 6 / Framework 报告**（与 `--plan` 同 schema 的 `test-report.md` + `trace.json`）：

```bash
hylyre run --steps-file nav.json --feature wallet-x \
  --report-out report.md --trace-out trace.json \
  --bundle com.example.app --page-name MainAbility
```

**冷启**：`run --plan` 与 `run --steps-file` 均支持 `--bundle` + `--page-name` + `--wait-time`（不必在 Framework 侧单独 `hdc aa start`，除非 Ability 需预启）。

### 2.4 确定性 selector 与证据约束

0.4.0 正式执行只接受 `match: "exact"` 或 `match: "contains"`；省略时运行证据会记录 `effective_match: "contains"`，不会把 exact 失败自动放宽为 contains。`touch`、`input`、`wait_for`、`wait_gone`、`scroll_to` 及滚动容器 selector 共用这一语义。action selector 命中 0 个返回 `selector_not_found`，命中多个返回 `selector_ambiguous` 和候选摘要；需要消歧时显式使用既有 `index`、`scope`、`within` 或 `all`。非法值（包括 `starts_with`、拼写错误）也使用冻结的 `selector_not_found`，不会新增错误枚举。

`swipe.area`、`scroll.at` 和 `scroll_to.in` 先经过同一 dump resolver 做唯一性预检；多候选不会固定记录 `candidate_count=1`，也不会由 Hypium/DFS 默认选第一项。没有 `top_overlay` 或相对 anchor 命中时不会放宽约束到整棵树。

普通 Text 的完整节点文本和普通动态 Row 都按正常 `contains` 使用，不根据 Row/Button 祖先类型猜测富文本。若宿主明确在聚合 Text 上提供 `inline_target=true`，或提供独立 Span/semantic action/片段 bounds，才进入 inline 语义；有 inline signal 但没有独立可点击区域时，必须 fail-closed 为 `inline_target_unresolvable`，不能点击父 Text/Row 中心或按字符比例猜坐标；`all[]` 内的 `by_text` 同样适用。未声明 clickable 语义的普通 Span 即使有 bounds 也不可点击。富文本动作仍需计划中的后置 assertion 才能使 case verified。完整的 `StepResult`、三轴 verdict 和迁移边界见 [`docs/deterministic-verification.md`](deterministic-verification.md)。

## 3. 预期结果列与 VLM

`runner._run_case_on_agent` 中：仅当 **`agent.vlm is not None` 且 `check_expected`** 时才会对「预期结果」列调用 `ai_assert`。

因此 **做法 A 全流程不配 VLM** 时：

- 「预期结果」可写给人看，但 **运行时不会自动校验**；
- 若仍希望校验，可二选一：配置 VLM；或对关键步骤多用 JSON `touch`/`input` 表达清楚、接受无自动断言。

命令行上 `--skip-assert-expected` 会在 **有 VLM** 时也跳过对「预期结果」的断言。

trace 会把该事实落成 `expected_check_mode`：`checked_vlm`、`disabled_by_flag`、`unavailable_no_vlm` 或 `empty`；消费方不应再根据 `model_backend` 或命令行参数猜测。
若 expected 非空、VLM 可用但前序步骤中止，仍记录 `checked_vlm`，并在 `steps[]` 增加 `expected_check` 的 blocked 行；不能改写成 `empty`。

`assert_toast` 只有在触发动作前已启动监听时才可作为 verified assertion；原子 CLI/MCP 单独断言会记录 `trigger_window_covered=false`，只能作为非验证性观察。`scroll_to.in` 的 `in` selector 先解析并直接使用唯一命中的容器节点，不再通过首次 DFS 重新选择。

## 4. 真机跑通命令（示例）

在项目根目录（或给定绝对路径）：

```bash
hylyre run \
  --plan path/to/test-plan.md \
  --feature your-feature-slug \
  --report-out path/to/test-report.md \
  --trace-out path/to/trace.json \
  --device-sn <可选> \
  --bundle com.example.app \
  --skip-assert-expected \
  --failure-dir path/to/failures
```

- **`--failure-dir`**（可选）：步骤失败时 best-effort 写入 `step-<n>.json`（UI 树）与 `step-<n>.png`（截图）；默认在 `--report-out` 同级 `failures/`。诊断采集失败不会掩盖原错误。

- 需已安装：`pip install -e ".[device]"`（或 `hylyre[device]`），`hdc`/设备可用。
- Mock：按需加 `--mock-port` / `--lyrebird-url` 与 `--mock-group`。

## 5. 与 Cursor、MCP 的衔接

**一次性配置**：在 Cursor 里启用 Hylyre MCP 的步骤见 [`docs/cursor-mcp-setup.md`](./cursor-mcp-setup.md)。配置后 Agent 可用 **`hylyre_run_plan`**、`hylyre_dump_ui`、`hylyre_run_*`、**`hylyre_run_steps`**、`hylyre_report_*` 等工具；与 CLI **同一套 `execute_*` 逻辑**（见 [`agent-loop.md`](./agent-loop.md)）。

**仓库内约定（已提交）**：

- **[`AGENTS.md`](../AGENTS.md)**：给人与 Agent 看的「默认如何用 Hylyre」摘要。
- **[`.cursor/rules/hylyre.mdc`](../.cursor/rules/hylyre.mdc)**：`alwaysApply`，约束 Agent 的调用优先级（MCP → CLI、做法 A / 原子循环、何时要 VLM）。
- **[`.cursor/rules/hylyre-plan-a.mdc`](../.cursor/rules/hylyre-plan-a.mdc)**：编辑 `*test-plan*.md` 时触发，细化 JSON 步骤格式。
- **[`agent-loop.md`](./agent-loop.md)**：原子循环模式（dump-ui / screenshot + 增量报告）。
