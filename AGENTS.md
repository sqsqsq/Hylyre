# Hylyre — Agent 使用说明（本仓库）

面向 **Cursor / 其它 coding agent**：在这里工作并按下列方式调用 Hylyre 时，**不需要**用户在每次对话里重复长篇环境说明。

## 一次交给使用者的配置（非每轮对话）

- **可选但强烈推荐**：在 Cursor **Settings → MCP** 中为 Hylyre 增加一个 server（命令、工作目录见 [`docs/cursor-mcp-setup.md`](docs/cursor-mcp-setup.md)）。配置一次后，你会多出一组 **`hylyre_*` 工具**，比反复拼终端命令更稳。
- **依赖**：本仓库根目录执行过 `pip install -e ".[dev]"`（真机再加 `device` extra）。`hylyre doctor` 可自检。

## 每轮对话里你应该怎么做（默认行为）

1. **若 MCP 可用**：优先用 **`hylyre_run_plan`**、**`hylyre_report_*`**、**`hylyre_doctor`**、**`hylyre_device_list`**、**`hylyre_dump_ui`** / **`hylyre_screenshot`**、**`hylyre_run_*`**（planned JSON：`action` / `tap` / `input` / **`swipe`** / **`scroll`**）、**`hylyre_collect_list`**、以及按需的 **`hylyre_ai_*`**；路径用**绝对路径**或相对 **仓库根** 的明确路径。
2. **若 MCP 不可用**：在**仓库根**终端执行 `python -m hylyre …`（与 CLI 帮助一致）。**CLI 与 MCP 共享同一套逻辑**（强 CLI / 弱 MCP 薄壳）。**连接复用**：MCP 侧 **`hylyre_open_session`**；CLI 侧长时间原子循环用 **`hylyre session start`**，后续命令加 **`--session`**（见 [`docs/agent-loop.md`](docs/agent-loop.md)）。
3. **用户用自然语言描述用例、又不想配运行态 VLM**：
   - **已知 selector / 稳定文案**：按 **做法 A** 写 `test-plan.md`「测试步骤」列（仅 **JSON**：`action` / `touch` / `input`）。规约见 [`docs/agent-plan-a.md`](docs/agent-plan-a.md)。
   - **需要先感知当前界面**：用 **原子循环**（`dump-ui` / `screenshot` + `run …` + `report …`）。**dump-ui** 含 **`_hylyre_hints`**（scrollable / 可能仍有屏外内容）；要数清虚拟列表优先 **`hylyre collect-list`** / MCP **`hylyre_collect_list`**。用户 **未写滑动手势** 时的默认纪律见 [`docs/agent-loop.md`](docs/agent-loop.md) **「自然语言未约定手势时」**；列表与半屏模态见同页 **「列表与滚屏」**。

## 最短命令备忘

- 离线烟测：`hylyre run --plan <plan.md> --feature <slug> --report-out <report.md> --trace-out <trace.json> --use-fakes`
- 校验：`hylyre report verify --report … --trace … [--plan …]`（ad-hoc 报告可省略 `--plan`）
- 原子循环（节选）：`hylyre dump-ui`、`hylyre screenshot`、`hylyre run action|tap|input|swipe|scroll`。**多条 CLI 串联真机**时用 **`hylyre session start`** + 各命令 **`--session <.hylyre/session.json>`**，结束前 **`hylyre session stop`**。**枚举半屏长列表**：`hylyre collect-list`（或 MCP **`hylyre_collect_list`**）。**半屏浮层里滚动列表**须在 **`swipe.area` / `scroll.at`**（常用 **`by_type: Scroll`**）内操作，或使用 **`run swipe --area-by-type Scroll`** / **`run scroll --at-by-type Scroll`**，避免全屏下滑关掉 Sheet（详见 [`docs/agent-loop.md`](docs/agent-loop.md)）。
- 增量报告：`hylyre report begin` → `hylyre report record` → `hylyre report finalize`
- 真机：去掉 `--use-fakes`，安装 `hylyre[device]`，按需 `--device-sn`、`--bundle`、`--skip-assert-expected`（JSON 步骤 + 无 VLM 时常用）。

## 不要做的

- 不要假设已安装 Lyrebird/mitmproxy —— 缺了只在 Mock 相关步骤失败时再提示。
- 不要把业务独有的 `by_id`/`by_text` 写进规则文件；应写在各 feature 的 `test-plan.md` 里。
