# Hylyre — Agent 使用说明（本仓库）

面向 **Cursor / 其它 coding agent**：在这里工作并按下列方式调用 Hylyre 时，**不需要**用户在每次对话里重复长篇环境说明。

## 一次交给使用者的配置（非每轮对话）

- **可选但强烈推荐**：在 Cursor **Settings → MCP** 中为 Hylyre 增加一个 server（命令、工作目录见 [`docs/cursor-mcp-setup.md`](docs/cursor-mcp-setup.md)）。配置一次后，你会多出一组 **`hylyre_*` 工具**，比反复拼终端命令更稳。
- **依赖**：本仓库根目录执行过 `pip install -e ".[dev]"`（真机再加 `device` extra）。`hylyre doctor` 可自检。

## 每轮对话里你应该怎么做（默认行为）

1. **若 MCP 可用**：优先用 **`hylyre_run_plan`**、**`hylyre_report_verify`**、**`hylyre_doctor`**、**`hylyre_device_list`**、**`hylyre_ai_*`** 等；路径用**绝对路径**或相对 **仓库根** 的明确路径。
2. **若 MCP 不可用**：在**仓库根**终端执行 `python -m hylyre …`（与 CLI 帮助一致）。
3. **用户用自然语言描述用例、又不想配运行态 VLM**：按 **做法 A** 把步骤写进 `test-plan.md` 的「测试步骤」列（仅 **JSON**：`action` / `touch` / `input`）。规约见 [`docs/agent-plan-a.md`](docs/agent-plan-a.md)，字段提示见 [`.cursor/rules/hylyre-plan-a.mdc`](.cursor/rules/hylyre-plan-a.mdc)。

## 最短命令备忘

- 离线烟测：`hylyre run --plan <plan.md> --feature <slug> --report-out <report.md> --trace-out <trace.json> --use-fakes`
- 校验：`hylyre report verify --report … --trace … --plan …`
- 真机：去掉 `--use-fakes`，安装 `hylyre[device]`，按需 `--device-sn`、`--bundle`、`--skip-assert-expected`（JSON 步骤 + 无 VLM 时常用）。

## 不要做的

- 不要假设已安装 Lyrebird/mitmproxy —— 缺了只在 Mock 相关步骤失败时再提示。
- 不要把业务独有的 `by_id`/`by_text` 写进规则文件；应写在各 feature 的 `test-plan.md` 里。
