# Hylyre 工程进度

## 2026-05-11 · P0.7 完成（本机 pip / pytest / hylyre）

- **Python**：已通过 `winget install --id Python.Python.3.12 -e` 安装 **3.12.10**（路径示例：`%LocalAppData%\Programs\Python\Python312\python.exe`）。**建议**将以下目录加入用户 PATH，便于直接敲 `python`、`pip`、`hylyre`、`pytest`：
  - `%LocalAppData%\Programs\Python\Python312\`
  - `%LocalAppData%\Programs\Python\Python312\Scripts\`
- **安装与验证**（在仓库根 `e:\1.code\Hylyre`）：
  - `python -m pip install -e ".[dev]"` ✅
  - `python -m hylyre doctor` ✅（已修复：`doctor` 子命令与 `doctor` 模块同名导致的 `AttributeError`，改为 `import doctor as doctor_cmd`）
  - `python -m pytest` ✅ **15 passed**
- **`hylyre doctor` 当前环境**：Python / Node / npm / hdc ✅；**mitmproxy** 未在 PATH（预期 P2 前可选；Lyrebird 需要时安装）。
- **OpenSpec**：`openspec/changes/add-mvp-skeleton/tasks.md` 中 **8.8** 项已含 git commit 勾选（见仓库提交记录）。

### P0 总体状态

| 阶段 | 状态 |
|------|------|
| P0.1–P0.6 | 已完成（见下文归档表） |
| P0.7 | **已完成** |

---

## 2026-05-11 · P1 真机烟测（add-driver-hypium 任务 13）

- **环境**：`python -m pip install -e ".[device]"`；USB 连接真机，`hdc list targets` 可见设备。
- **命令**：
  - `python -m hylyre device list` ✅
  - `python -m hylyre ai tap --device-sn <SN> --x 100 --y 150` ✅（Hypium 自动推 agent / 启 uitest daemon，`touch` 正常返回）
- **仓库**：`.gitignore` 增加 `reports/`（Hypium 默认报告目录，避免误提交）。

---

## 2026-05-11 · P0 构建进展（归档表）

| Todo | 说明 |
|------|------|
| **P0.1 环境前置** | Node v22.22.0、npm 11.11.0；winget 安装 Python 3.12 后本机可跑全流程 ✅ |
| **P0.2 工程脚手架** | `pyproject.toml`、`hylyre/`、CLI、`doctor` ✅ |
| **P0.3 自测试基础设施** | `tests/`、`contracts/`、GitHub Actions ✅ |
| **P0.4 OpenSpec** | `openspec init --tools cursor,codex,claude` ✅ |
| **P0.5 宪章 + change** | `openspec/project.md`、`add-mvp-skeleton` 全套 spec delta ✅ |
| **P0.6 文档** | `README.md`、本文件 ✅ |

### 下一步

- **主线**：**P6**（反哺 Skill 6）或工程卫生（如 `compat-framework`）。
- **并行**：仓库 **`scripts/bootstrap_mock.{sh,bat,ps1}`**（可选入口，等价 CLI）。

---


## 2026-05-12 · MITM CA push + mock bootstrap（首版）

- **交付**：`hdc_cli.file_send`、`cert_bootstrap.push_mitm_ca_to_device`、`hylyre mock push-ca`、`doctor` 的 **mitmproxy CA (PEM)** 行、`hylyre bootstrap mock [--install]`（P2b）；仓库脚本 **`scripts/bootstrap_mock.{sh,bat,ps1}`**（`PYTHONPATH`= 仓库根，转发 CLI）。
- **OpenSpec**：稳态 `openspec/specs/cert-bootstrap/spec.md`；change 已归档 `openspec/changes/archive/2026-05-12-add-cert-bootstrap/`（真机烟测任务 6 仍可选）。
- **验证**：`tests/unit/test_cert_bootstrap.py`、`test_hdc_cli.py`、`test_mock_cli.py`、`test_bootstrap_cli.py`；全量 pytest **145 passed**。

## 2026-05-12 · P4 收官（add-scenario-runner 归档）

- **交付**：`ScenarioRunner.run_plan_on_agent`（真机 / `HylyreAgent`）、`hylyre run` 扩展选项（`--device-sn`、`--bundle`、`--mock-port`、`--lyrebird-url`、`--mock-group`、`--skip-assert-expected`）、测试步骤 **JSON 或 NL**（NL 需 VLM）、`trace.tool_calls`、`docs/plan` P4 闭合。
- **OpenSpec**：`openspec/changes/archive/2026-05-12-add-scenario-runner/`（tasks 全勾选）；稳态 **`openspec/specs/scenario-runner/spec.md`**。
- **验证**：`python -m pytest` 全绿（128）。

## 2026-05-12 · P5 MCP（mcp-wrapper）

- **交付**：`hylyre mcp serve`（stdio，`--show-banner` 可选）、`hylyre/mcp/server.py` 注册 8 个 tool；与 CLI 共用 `run_cmd.execute_scenario` / `execute_report_verify`、`doctor`/`device`/`ai`/`mock` 的 `execute_*` 或纯文本封装。
- **依赖**：`pyproject` 中 `[mcp]` 仍为 `fastmcp`；**`dev`** 额外加入 `fastmcp` 以便 CI 跑 `tests/unit/test_mcp_server.py`。
- **验证**：`python -m pytest` 全绿（含 FastMCP `Client` 内嵌调用与 fake `hylyre_run_plan` + `hylyre_report_verify`）。

## 2026-05-12 · L5 mini-harness 与 `docs/plan.md` §7.5 对齐（补严）

- **契约**：`report-sections.yaml` 增加 `pass_rate_required_tiers`、`pass_rate_overall_label`；L5 校验分级通过率、缺陷清单、结论段（含 `outcome` / `n/m`）、`trace.json` `outcome` 与执行表一致。
- **实现**：`hylyre/report/emit.py` 分层归一与四行通过率；`hylyre/harness/runner.py` 补严；`tests/schema/test_contracts_loadable.py`、`tests/unit/test_harness_verify.py`、`openspec/specs/contracts/spec.md` 已跟进。
- **文档**：`docs/plan.md` §7.5 更新检查项与「契约演进顺序」；本文件与 `hylyre/contracts/README.md` 记下维护流程。
- **存量报告**：仓库根 **`reports/`** 目录被 `.gitignore` 忽略（真机/Hypium 产物）；**基准核对**使用 `tests/e2e/fixtures/mock-test-plan.md`：执行 `hylyre run --use-fakes …` + `hylyre report verify …`（本机示例：`reports/ci-smoke/` 烟测产物，`verify` 输出 `Contracts OK`）或跑 `tests/e2e/test_run_fake_pipeline.py`。业务侧旧版手工 `test-report.md` 需按新契约重生成或手改后再验。

## 2026-05-12 · P3 收官（add-api-agent 归档）

- **交付**：`HylyreAgent`、`VlmClientBase` / `HttpVlmClient`、`hylyre.wiring`、`hylyre ai action|query|assert`；L1 单测 + 覆盖率门禁通过。
- **OpenSpec**：`openspec/changes/archive/2026-05-11-add-api-agent/`（`tasks.md` 全勾选）。

## 2026-05-11 · P2 Lyrebird 与证书分工（闭环）

- **代码交付**：`MockControllerBase` / `LyrebirdController` / `hylyre mock start|stop|status|activate|deactivate|capture|cert|push-ca`；CI 内 **respx**，不强依赖真 Lyrebird 进程。
- **OpenSpec**：
  - **`add-driver-lyrebird`**：已 **`/opsx:archive` 等价归档** 至 `openspec/changes/archive/2026-05-11-add-driver-lyrebird/`；稳态能力写入 `openspec/specs/driver-lyrebird/spec.md`。原 `tasks.md` 中 **13、14** closure：**13** → 独立 change **`add-cert-bootstrap`**；**14** → CLI/测已覆盖，真进程依赖本机安装。
  - **`add-cert-bootstrap`**：首版 **`hylyre mock push-ca`** + 稳态 **`openspec/specs/cert-bootstrap/spec.md`**；change 已归档 **`openspec/changes/archive/2026-05-12-add-cert-bootstrap/`**。
- **本机真进程烟测（可选）**：在仓库根执行  
  `python -m pip install -e ".[mock]"` → `python -m hylyre mock start --mock-port 9090 --data <mock数据目录>` → `python -m hylyre mock status` → `python -m hylyre mock stop`。  
  **Windows 注意**：`lyrebird` 依赖链可能需编译 `netifaces`，若 pip 报需 **Microsoft Visual C++ Build Tools**，先安装 [Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 或使用已提供 wheel 的环境（如部分 Linux CI 镜像）。

---

- **`add-mvp-skeleton`** → `openspec/changes/archive/2026-05-11-add-mvp-skeleton/`；稳态能力写入 `openspec/specs/*`。
- **`add-driver-hypium`** → `openspec/changes/archive/2026-05-11-add-driver-hypium/`；`driver-hypium` 等规范合并至主 specs。
- **`add-driver-lyrebird`** → `openspec/changes/archive/2026-05-11-add-driver-lyrebird/`；`driver-lyrebird` 规范合并至主 specs。
- **`add-api-agent`** → `openspec/changes/archive/2026-05-11-add-api-agent/`；`api-agent` 规范见 `openspec/specs/api-agent/spec.md`。
- **`add-cert-bootstrap`** → `openspec/changes/archive/2026-05-12-add-cert-bootstrap/`；`cert-bootstrap` 规范见 `openspec/specs/cert-bootstrap/spec.md`。

## 2026-08-30 · 确定性验证、Selector 语义与证据完整性

- **OpenSpec**：`deterministic-verification-selector-evidence`；先通过 strict validation，再实施生产代码、测试和文档。完成后合并至 `openspec/specs/{api-agent,driver-hypium,scenario-runner,contracts,cli,mcp-wrapper,selector-resolution}/`。
- **契约**：trace schema `0.3-p0`；`CaseResult.steps[]` 是唯一证据真源，`tool_calls`/Markdown 为派生投影；新增 execution/verification/evidence、expected-check 四态、StepResult 两级失败分类和环境/selector 证据。
- **语义**：Hypium wait 返回值、Toast 预监听与布尔结果、exact/contains、action 多候选、聚合富文本 fail-closed 已覆盖 fake/native/resolver 回归。
- **版本/迁移**：推荐 Hylyre `0.4.0`（0.x minor 级行为收紧）；见 `CHANGELOG.md`、`docs/deterministic-verification.md`、`docs/migration-0.4.md`。真机复验项仍 pending，不以 fake 结果冒充。

## 2026-08-30 · Review hardening follow-up

- **Follow-up OpenSpec**：`deterministic-verification-selector-evidence-hardening` 先通过 strict validation；修复 review 反例后再合并 canonical specs。
- **收口**：aborted/skipped/empty-evidence 不再 verified pass；abort 后完整保留 blocked StepResult；selector 约束、多候选 swipe/scroll、rich-text 和 Toast capability skip 均 fail-closed/typed。
- **入口与证据**：新增真实 plan、CLI steps-file、MCP session-batch dispatcher 回归；trace selector 字段收紧，legacy verifier 输出显式标识，敏感 selector/error/notes 脱敏。
- **发布验证**：`dist/release-src/release.manifest.json`：schema `2`、version `0.4.0`、file count `82`、total bytes `537857`、tree hash `545d519edab6ef3ec9694c2fc9040de7975703bf641a57b7bd03ff4ff3812512`；build 与 `--verify` 均通过。

## 2026-08-30 · Final review hardening

- **剩余阻断已闭环**：Toast trigger-window 未覆盖不可 verified；显式标识为 inline target 的原始聚合 Text（含 `all[]`）fail-closed；普通动态 Row `contains` 保持可寻址；nested match 贯穿执行与证据；`scroll_to.in` 使用 resolver 选中的容器节点。
- **兼容修复**：blocked suffix 保留根因 `failure_kind/failure_code`，`executed` 只计实际 dispatch，完整 ledger 仍保留 blocked rows。

## 2026-08-30 · Inline-target contract correction

- **OpenSpec**：`deterministic-verification-inline-contract` 已通过 strict validation，canonical `selector-resolution`/`api-agent` 已同步并归档至 `openspec/changes/archive/2026-08-30-deterministic-verification-inline-contract/`。
- **语义修正**：移除 generic Row/ancestor 富文本启发式，恢复普通动态 Text/Row `contains`；聚合富文本 fixture 改用明确的 host `inline_target=true` signal，并覆盖正常 Row 对冲场景。
