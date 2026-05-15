---
name: run-steps MCP batch
overview: 为 hylyre run 增加 --steps/--steps-file 批量步骤执行能力（CLI 主、MCP 薄壳），消除多步导航时的重复进程启动 / AI 轮转开销。
todos:
  - id: extract-step-dispatch
    content: 从 runner.py 提取 _execute_one_step 为公共函数 dispatch_planned_step（放 agent.py 或 step_dispatch.py）
    status: completed
  - id: steps-cmd
    content: 新建 hylyre/cli/commands/steps_cmd.py，实现 execute_run_steps（CLI execute_* 层）+ run_steps_on_agent（核心逻辑）
    status: completed
  - id: cli-cmd
    content: 在 hylyre run 下增加 --steps / --steps-file 参数，复用 session
    status: completed
  - id: unit-tests
    content: 补 tests/unit/test_run_steps.py 单测（5 个场景）
    status: completed
  - id: mcp-tool
    content: 在 mcp/server.py 注册 hylyre_run_steps 薄壳工具
    status: completed
  - id: agent-rules
    content: 更新 .cursor/rules/hylyre.mdc 和 FastMCP instructions，让 Cursor agent 知道何时用 run_steps
    status: completed
  - id: docs
    content: 更新 agent-loop.md、AGENTS.md、agent-plan-a.md 文档
    status: completed
isProject: false
---

# `hylyre run --steps`：CLI 批量步骤执行

## 背景与动机

### CLI 场景

`hylyre run tap -S session.json -j '...'` 每次调用都是独立 Python 进程（~3s 启动开销）。4 步导航 = 4 次进程启动 = 12s 纯开销。`hylyre run --plan` 可以批量，但要求写 markdown 文件，对于"已知几步 JSON、想快速跑一遍"的场景过重。

### MCP 场景

每个 MCP 工具调用之间有 AI 轮转延迟（~8s）。4 步导航 = 4 次轮转 = 32s 纯等待。如果能一次调用传入步骤数组，轮转只需 1 次。

### 共同需求

在 session 内接受 **inline JSON 步骤数组**，顺序执行，返回结构化结果。CLI 是主入口，MCP 薄壳调同一套 `execute_*`。

## 核心设计

### CLI 接口（主）

```bash
# 从 JSON 文件读步骤数组（推荐，避免 shell 转义）
hylyre run --steps-file steps.json -S .hylyre/session.json --on-fail abort

# 内联 JSON（短步骤或脚本场景）
hylyre run --steps '[{"touch":{"by_id":"..."}},{"swipe":{"direction":"UP"}}]' \
  -S .hylyre/session.json

# 可选：执行步骤前先启动 app
hylyre run --steps-file steps.json -S .hylyre/session.json \
  --bundle com.huawei.hmos.wallet --page-name MainAbility
```

`--steps` / `--steps-file` 与现有 `--plan` 互斥。位于同一个 `hylyre run` 命令下，统一"执行"入口：

- `hylyre run --plan <file>` — markdown 计划批量（面向 CI / Skill 6）
- `hylyre run --steps-file <file>` / `--steps <json>` — JSON 步骤数组批量（面向快速验证）
- `hylyre run tap|swipe|scroll|...` — 单步原子（面向探索）

### MCP 接口（薄壳）

```python
hylyre_run_steps(
    steps: list[dict],          # [{"touch": {...}}, {"swipe": {...}}, ...]
    session_id: str | None,
    session_path: str | None,
    device_sn: str | None,
    on_fail: str = "abort",     # "abort" | "skip"
    bundle: str | None,
    page_name: str | None,
    wait_time: float = 1.0,
) -> str  # JSON result
```

内部调用 `steps_cmd.execute_run_steps(...)` 或 `steps_cmd.run_steps_on_agent(...)`，与 CLI 完全同一条代码路径。

### 步骤格式

复用现有 `_execute_one_step` 分发逻辑，每个 step 是一个 planned JSON dict：

- `{"touch": {"by_id": "..."}}` / `{"touch": {"by_text": "..."}}`
- `{"swipe": {"direction": "UP", "distance": 60, "area": {...}}}`
- `{"scroll": {"direction": "down", "steps": 6}}`
- `{"input": {"text": "hello", "by_id": "field"}}`
- `{"action": {"type": "touch", ...}}`

### 返回格式

```json
{
  "total": 4,
  "executed": 3,
  "results": [
    {"index": 0, "step": {"touch": {"by_id": "..."}}, "status": "ok", "elapsed_ms": 720},
    {"index": 1, "step": {"touch": {"by_id": "..."}}, "status": "ok", "elapsed_ms": 680},
    {"index": 2, "step": {"swipe": {}}, "status": "error", "error": "element not found", "elapsed_ms": 150}
  ],
  "on_fail": "abort",
  "total_elapsed_ms": 1550
}
```

CLI 输出同样的 JSON 到 stdout（或 `--out file.json`）。

### on_fail 策略

- `"abort"`（默认）：某步失败立即停止，返回已执行步骤结果 + 失败上下文
- `"skip"`：某步失败标记 error，继续执行下一步

## 改动范围（按实施顺序）

### 1. 提取公共 step 分发函数

将 [`hylyre/scenario/runner.py`](hylyre/scenario/runner.py) 中 `_execute_one_step` 提取为公共函数 `dispatch_planned_step`：

- 放在 `hylyre/api/agent.py`（作为 `HylyreAgent` 的方法），或新建 `hylyre/api/step_dispatch.py`
- `runner.py` 的 `_execute_one_step` 改为调用公共函数
- 保持 `_JSONISH` regex + 根键分发逻辑不变

### 2. CLI 核心逻辑：[`hylyre/cli/commands/steps_cmd.py`](hylyre/cli/commands/steps_cmd.py)（新文件）

```python
async def run_steps_on_agent(
    agent: HylyreAgent,
    steps: list[dict],
    on_fail: str = "abort",
) -> dict:
    """Execute planned JSON steps sequentially, return structured results."""

def execute_run_steps(
    steps: list[dict],
    *,
    device_sn: str | None = None,
    session_file: Path | None = None,
    on_fail: str = "abort",
    bundle: str | None = None,
    page_name: str | None = None,
    wait_time: float = 1.0,
) -> dict:
    """CLI execute_* 入口：创建/复用 agent，调用 run_steps_on_agent。"""
```

`run_steps_on_agent` 逐步调用 `dispatch_planned_step`，每步计时，按 `on_fail` 策略处理异常。

### 3. CLI 命令入口：[`hylyre/cli/__main__.py`](hylyre/cli/__main__.py)

在 `hylyre run` 下增加 `--steps` / `--steps-file` 互斥参数组（与 `--plan` 互斥）：

- `--steps <json_string>` — 内联 JSON 数组
- `--steps-file <path>` — 从文件读 JSON 数组
- `--on-fail abort|skip`（默认 abort）
- 复用现有 `--session` / `-S`、`--device-sn`、`--bundle`、`--page-name` 等参数

### 4. 单测：`tests/unit/test_run_steps.py`

用 FakeAgent 验证 `run_steps_on_agent`：

- 3 步全成功 → results 全 ok，executed == total
- 第 2 步失败 + on_fail=abort → executed == 2，第 2 步 status=error
- 第 2 步失败 + on_fail=skip → executed == 3，第 2 步 status=error，其余 ok
- 含 bundle 参数 → start_app 先执行（通过 execute_run_steps 验证）
- steps 为空数组 → 返回 total=0, results=[]

### 5. MCP 薄壳：[`hylyre/mcp/server.py`](hylyre/mcp/server.py)

注册 `@mcp.tool(name="hylyre_run_steps", ...)`：

- 参数映射到 `steps_cmd.run_steps_on_agent`（session_id 路径）或 `steps_cmd.execute_run_steps`（session_path / device_sn 路径）
- 用 `_call_logged_async` 包裹
- description 注明"批量步骤，减少 MCP 轮转"

### 6. Agent 感知层更新（让 Cursor agent 正确使用新能力）

Cursor agent 感知 MCP 工具分两层：**发现**（MCP 协议自动暴露 schema）和**正确使用**（需要规则指导）。仅靠工具自动发现不够，agent 不会主动优先选择 `hylyre_run_steps` 而非逐步调用。需要在以下位置显式写入使用策略：

#### 6a. [`.cursor/rules/hylyre.mdc`](.cursor/rules/hylyre.mdc)（最高优先级，always-applied）

在"调用方式"章节追加批量步骤规则：

```markdown
## 批量步骤（优先级高于逐步调用）

已知 2 个以上连续 JSON 步骤时（如从 `app_find` 获取的导航路径、或上轮循环确认过的步骤序列），
**优先**用 **`hylyre_run_steps`**（MCP）或 **`hylyre run --steps-file`**（CLI）一次性执行，
**不要**逐个调用 `hylyre_run_tap` / `hylyre_run_swipe` 等单步工具。

仅在以下场景才逐步调用：
- 需要每步后感知界面（`dump_ui` / `screenshot`）再决定下一步
- 步骤不确定，需要探索
```

#### 6b. [`hylyre/mcp/server.py`](hylyre/mcp/server.py) — `FastMCP(instructions=...)` 字符串

在现有 instructions 末尾追加：

```
Batch known steps: hylyre_run_steps (pass list of JSON steps in one call,
avoids per-step round trips). Prefer over multiple run_tap/run_swipe calls
when steps are known upfront.
```

#### 6c. [`AGENTS.md`](AGENTS.md)

在"每轮对话里你应该怎么做"章节追加：

```markdown
3. **已知多步时批量执行**：有 2+ 个确定的 JSON 步骤时，用 **`hylyre run --steps-file`**（CLI）或 **`hylyre_run_steps`**（MCP）一次性执行。仅在需要逐步感知界面时才用单步工具。
```

### 7. 文档更新

- [`docs/agent-loop.md`](docs/agent-loop.md)：在 "CLI 典型循环" 和 "MCP 典型循环" 中加入 `--steps` / `hylyre_run_steps`，说明与 `--plan` 和单步的定位区别
- [`docs/agent-plan-a.md`](docs/agent-plan-a.md)：说明 `--steps-file` 与 `--plan` 的关系（前者无报告产物，后者有完整报告 + trace）

## 不改的

- `hylyre run --plan` 保持原样（markdown 计划 + 报告 + trace，面向 CI / Skill 6）
- 现有单步工具（`run tap` / `run swipe` / ...）接口不变
- 不做 MCP 热重载（nice-to-have，后续再议）

## 预期效果

### CLI 路径

```
Before: session start → run tap(3s) → run tap(3s) → run tap(3s) → run tap(3s) → collect-list(9s)
4 次进程启动开销 = 12s；总计 ~24s

After:  session start → run --steps-file nav.json(5s, 单进程 4 步) → collect-list(9s)
1 次进程启动；总计 ~17s
```

### MCP 路径

```
Before: open_session → [AI 8s] → start_app → [AI 8s] → tap1 → [AI 8s] → tap2 → [AI 8s] → tap3 → [AI 8s] → collect_list
5 次 AI 轮转 = 40s + 12s 设备 = ~52s

After:  open_session → [AI 8s] → run_steps(start_app + 3 taps) → [AI 8s] → collect_list
2 次 AI 轮转 = 16s + 12s 设备 = ~28s（>45% 降幅）
```
