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

### 2.1 允许的 JSON 根键（与 `HylyreAgent.run_planned_*` 及 `hylyre run --plan` 一致）

| 根键 | 含义 | 典型 payload |
|------|------|----------------|
| `action` | 单步动作 | `{"action":{"type":"touch","by_text":"登录"}}`、`{"action":{"type":"input","text":"100","by_id":"amount"}}`、`{"action":{"type":"swipe","direction":"UP","distance":60,"area":{"by_type":"Scroll"}}}` |
| `touch` | 等价于 tap schema | `{"touch":{"by_text":"充值"}}`、`{"touch":{"x":100,"y":200}}` |
| `input` | 输入 schema | `{"input":{"text":"hello","by_id":"field","by_text":null}}` |
| `swipe` | 方向滑动手势（Hypium `swipe`）；**半屏模态内需带 `area` 限定列表 `Scroll`**；竖向列表露出下方条目常用 **`UP`** | `{"swipe":{"direction":"UP","distance":55,"area":{"by_type":"Scroll"}}}` |
| `scroll` | 纵向滚轮式滚动（Hypium `mouse_scroll`） | `{"scroll":{"direction":"down","steps":6}}` |
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

**`swipe` / `scroll` / `action.type` 为 `swipe` 或 `scroll`** 的字段说明、列表虚拟化、半屏模态及 **`dump-ui`** 的关系，见 [`agent-loop.md`](./agent-loop.md) 中的 **列表与滚屏** 与 **自然语言未约定手势时** 两节。

### 2.2 `action.type`：`swipe` 与 `scroll`

与根键 **`swipe` / `scroll`** 等价，仅外层换成 `action` 信封：

- **`{"action":{"type":"swipe","direction":"LEFT","distance":50}}`**
- **`{"action":{"type":"scroll","direction":"up","steps":3,"at":{"by_type":"Scroll"}}}`**

字段名与 [`agent-loop.md`](./agent-loop.md) 中 **列表与滚屏**、**自然语言未约定手势时** 两小节一致。

### 2.3 批量：`hylyre run --steps-file`（无 `test-plan.md`）

已知多步 planned JSON，且**暂不需要** `test-report.md` / `trace.json` / L5 Harness 闭环时（例如本地快速重放、`session` + 多条 `tap`），可用 **JSON 文件数组**批量执行：

```bash
hylyre run --steps-file nav.json --session .hylyre/session.json --on-fail abort --out steps-result.json
```

与 **`hylyre run --plan`** **互斥**；步骤对象根键与本节 2.1 相同。**CI / Skill 6 / 可追溯报告**仍以 **`run --plan … --report-out --trace-out`** 为准。

## 3. 预期结果列与 VLM

`runner._run_case_on_agent` 中：仅当 **`agent.vlm is not None` 且 `check_expected`** 时才会对「预期结果」列调用 `ai_assert`。

因此 **做法 A 全流程不配 VLM** 时：

- 「预期结果」可写给人看，但 **运行时不会自动校验**；
- 若仍希望校验，可二选一：配置 VLM；或对关键步骤多用 JSON `touch`/`input` 表达清楚、接受无自动断言。

命令行上 `--skip-assert-expected` 会在 **有 VLM** 时也跳过对「预期结果」的断言。

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
  --skip-assert-expected
```

- 需已安装：`pip install -e ".[device]"`（或 `hylyre[device]`），`hdc`/设备可用。
- Mock：按需加 `--mock-port` / `--lyrebird-url` 与 `--mock-group`。

## 5. 与 Cursor、MCP 的衔接

**一次性配置**：在 Cursor 里启用 Hylyre MCP 的步骤见 [`docs/cursor-mcp-setup.md`](./cursor-mcp-setup.md)。配置后 Agent 可用 **`hylyre_run_plan`**、`hylyre_dump_ui`、`hylyre_run_*`、**`hylyre_run_steps`**、`hylyre_report_*` 等工具；与 CLI **同一套 `execute_*` 逻辑**（见 [`agent-loop.md`](./agent-loop.md)）。

**仓库内约定（已提交）**：

- **[`AGENTS.md`](../AGENTS.md)**：给人与 Agent 看的「默认如何用 Hylyre」摘要。
- **[`.cursor/rules/hylyre.mdc`](../.cursor/rules/hylyre.mdc)**：`alwaysApply`，约束 Agent 的调用优先级（MCP → CLI、做法 A / 原子循环、何时要 VLM）。
- **[`.cursor/rules/hylyre-plan-a.mdc`](../.cursor/rules/hylyre-plan-a.mdc)**：编辑 `*test-plan*.md` 时触发，细化 JSON 步骤格式。
- **[`agent-loop.md`](./agent-loop.md)**：原子循环模式（dump-ui / screenshot + 增量报告）。
