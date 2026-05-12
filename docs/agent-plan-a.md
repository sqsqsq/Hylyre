# 做法 A：Cursor / 外部 Agent 生成 test-plan（无运行态 VLM）

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

### 2.1 允许的三种根键（与 `HylyreAgent.run_planned_*` 一致）

| 根键 | 含义 | 典型 payload |
|------|------|----------------|
| `action` | 单步动作 | `{"action":{"type":"touch","by_text":"登录"}}`、`{"action":{"type":"input","text":"100","by_id":"amount"}}` |
| `touch` | 等价于 tap schema | `{"touch":{"by_text":"充值"}}`、`{"touch":{"x":100,"y":200}}` |
| `input` | 输入 schema | `{"input":{"text":"hello","by_id":"field","by_text":null}}` |

`action.type` 为 `touch` 时还可带 `wait_time`（可选）。

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

## 5. 与 Cursor MCP 的衔接

配置了 Hylyre MCP 时，Agent 可先 **写出** 合规的 `test-plan.md`，再调用 **`hylyre_run_plan`**，传同一组路径；`use_fakes=false` 且勿忘设备相关参数。

**Cursor 规则**：仓库已提交副本 [`contrib/cursor-rules/hylyre-plan-a.mdc`](../contrib/cursor-rules/hylyre-plan-a.mdc)。复制到项目根 `.cursor/rules/hylyre-plan-a.mdc`（本仓 `.cursor/` 默认 gitignore），编辑 `*test-plan*.md` 时即可自动附加该规则。
