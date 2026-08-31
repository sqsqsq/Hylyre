# Hylyre — Agent 使用说明（本仓库）

面向 **Cursor / 其它 coding agent**：在这里工作并按下列方式调用 Hylyre 时，**不需要**用户在每次对话里重复长篇环境说明。

## 一次交给使用者的配置（非每轮对话）

- **可选但强烈推荐**：在 Cursor **Settings → MCP** 中为 Hylyre 增加一个 server（命令、工作目录见 [`docs/cursor-mcp-setup.md`](docs/cursor-mcp-setup.md)）。配置一次后，你会多出一组 **`hylyre_*` 工具**，比反复拼终端命令更稳。
- **依赖**：本仓库根目录执行过 `pip install -e ".[dev]"`（真机再加 `device` extra）。`hylyre doctor` 可自检。

## 每轮对话里你应该怎么做（默认行为）

1. **若 MCP 可用**：优先用 **`hylyre_run_plan`**、**`hylyre_report_*`**、**`hylyre_doctor`**、**`hylyre_device_list`**、**`hylyre_dump_ui`** / **`hylyre_screenshot`**、**`hylyre_run_*`**（planned JSON：`action` / `tap` / `input` / **`swipe`** / **`scroll`** / **`scroll_to`** / **`back`** / **`home`** / **`stop_app`** / **`clear_app`** / **`wait`** / **`wait_for`** / **`wait_gone`** / **`wait_idle`** / **`assert_toast`** / **`start_app`**；若连续多步已定，一次性 **`hylyre_run_steps`**，可选 **`failure_dir`**）、**`hylyre_collect_list`**、**`hylyre_find`**、**`hylyre_app_page_*`**（快照 CRUD）、**`hylyre_app_find`**、**`hylyre_app_fingerprint`**，以及按需的 **`hylyre_ai_*`**；路径用**绝对路径**或相对 **仓库根** 的明确路径。
2. **若 MCP 不可用**：在**仓库根**终端执行 `python -m hylyre …`（与 CLI 帮助一致）。**CLI 与 MCP 共享同一套逻辑**（强 CLI / 弱 MCP 薄壳）。**连接复用**：MCP 侧 **`hylyre_open_session`**；CLI 侧长时间原子循环用 **`hylyre session start`**，后续命令加 **`--session`**（见 [`docs/agent-loop.md`](docs/agent-loop.md)）。
3. **用户用自然语言描述用例、又不想配运行态 VLM**：
   - **已知 selector / 稳定文案**：按 **做法 A** 写 `test-plan.md`「测试步骤」列（仅 **JSON**：`action` / `touch` / `input`）。规约见 [`docs/agent-plan-a.md`](docs/agent-plan-a.md)。若同一对话里已连续多步已知，可先用 **`python -m hylyre run --steps-file`**（会话内 **`--session`**）批量执行以降低进程启动开销，再写回归计划。
   - **需要先感知当前界面**：用 **原子循环**（`dump-ui` / `screenshot` + `run …` + `report …`）。对 **已知 bundle** 可先 **`app page load` / `app find`**（或 MCP **`hylyre_app_page_load`** / **`hylyre_app_find`**），详见 **[docs/app-knowledge.md](docs/app-knowledge.md)**。**dump-ui** 含 **`_hylyre_hints`**（scrollable / 可能仍有屏外内容）；要数清虚拟列表优先 **`hylyre collect-list`** / MCP **`hylyre_collect_list`**。用户 **未写滑动手势** 时的默认纪律见 [`docs/agent-loop.md`](docs/agent-loop.md) **「自然语言未约定手势时」**；列表与半屏模态见同页 **「列表与滚屏」**。

## 最短命令备忘

- 下游 framework vendor：`python scripts/build_wheel.py --clean` → 产出 `dist/release/hylyre-*-py3-none-any.whl` 与 `release.manifest.json`；下游禁 `.whl` 时用 **`--source --clean`** → `dist/release-src/`（`src/` 源码树 + schema 2 manifest）；**只交付契约冻结包**（无 runtime、不可安装，用于消费方先行适配）用 **`--contracts --clean`** → `dist/contracts-freeze/`（`contracts/` + schema 3 manifest + 可复现 zip）。校验统一 `--verify <目录>`（说明见 [`docs/framework-vendor-bundle.md`](docs/framework-vendor-bundle.md)）
- 离线烟测：`hylyre run --plan <plan.md> --feature <slug> --report-out <report.md> --trace-out <trace.json> --use-fakes`。**注意**：0.5.0 起离线桩不再伪造断言结果——桩没有设备可观测，计划里的 `wait_for`/`wait_gone`/`assert_toast` 会得到 `blocked/capability`（case 判 `阻塞`），这是诚实表达而非回归；离线只用于验证计划解析与 action 链路，断言结论必须真机跑。
- 校验：`hylyre report verify --report … --trace … [--plan …]`（ad-hoc 报告可省略 `--plan`）
- 原子循环（节选）：`hylyre dump-ui`、`hylyre screenshot`、`hylyre find`（输出 **`hits` + `_hylyre_hints`**）、`hylyre app page …` / `hylyre app find`、`hylyre run action|tap|input|swipe|scroll|scroll-to|back|home|wait|assert-toast|…`。**`input`** 支持 `by_type`/富选择器/`into`（0.3.0+，解析→聚焦→输入）。**若干已知步骤可一条命令跑**：`hylyre run --steps-file nav.json --session …`（或 MCP **`hylyre_run_steps`**），可选 **`--failure-dir`**。减少多次 `run tap`/MCP 往返。**多条 CLI 串联真机**时用 **`hylyre session start`** + 各命令 **`--session <.hylyre/session.json>`**，结束前 **`hylyre session stop`**。**阶段跑冷启**：**`hylyre device cold-restart --bundle …`**（下游 harness 接入见 **`docs/downstream-harness-requests.md`**）。**枚举半屏长列表**：`hylyre collect-list`（可选 **`--reset-to-top` / `--bidirectional`**；MCP **`hylyre_collect_list`**）。**半屏浮层里滚动列表**须在 **`swipe.area` / `scroll.at`**（常用 **`by_type: Scroll`**）内操作，或使用 **`run swipe --area-by-type Scroll`** / **`run scroll --at-by-type Scroll`**，避免全屏下滑关掉 Sheet（详见 [`docs/agent-loop.md`](docs/agent-loop.md)）。**富选择器**（`scope:top_overlay`、`scroll_to`、toast **`on_unsupported:skip`**）见 **`docs/agent-loop.md`** / **`docs/agent-plan-a.md`**。
- 增量报告：`hylyre report begin` → `hylyre report record` → `hylyre report finalize`
- 真机：去掉 `--use-fakes`，安装 `hylyre[device]`，按需 `--device-sn`、`--bundle`、`--page-name`、`--wait-time`、`--skip-assert-expected`（JSON 步骤 + 无 VLM 时常用）。`run --steps-file` 也可加 `--feature`/`--report-out`/`--trace-out` 产出与 plan 同 schema 报告。

## 不要做的

- 不要假设已安装 Lyrebird/mitmproxy —— 缺了只在 Mock 相关步骤失败时再提示。
- 不要把业务独有的 `by_id`/`by_text` 写进规则文件；应写在各 feature 的 `test-plan.md` 里。
