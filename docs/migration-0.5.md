# 迁移到 Hylyre 0.5.0（Step Outcome Protocol v1）

- trace schema：`0.3-p0` → **`0.4-p0`**
- 结果协议：**`result_protocol: "hylyre.step-outcome/1"`**
- 破坏性变更，不能以 0.4.2 patch 消费

机器契约本体在 [`hylyre/contracts/`](../hylyre/contracts/)：规范 `step-outcome-v1.md`、
判定表 `builder-decision-table.md`、Schema `output-schema.json`、参考 reducer
`reference_reducer.py`、样例 `golden/**`。**以那份为准**，本文只讲怎么改。

## 0. 先做 dispatch，再做别的

所有读取入口先共同判定 `(schema_version, result_protocol)`：

| 组合 | 结论 |
|---|---|
| `0.4-p0` + `hylyre.step-outcome/1` | v1 typed parse |
| `0.3-p0` / `0.2-p4` / `0.1-p0` 且**无** `result_protocol` | legacy，只读诊断，**不是** evidence |
| 其它任意组合（含 legacy 声称 v1、v1 缺协议、未知 schema） | **显式失败** |

**禁止**在不匹配时返回空 checks / SKIP / 改读中文 status / 回退 flat 字段。

## 1. 字段对照

| 0.3-p0 | 0.4-p0 |
|---|---|
| `step.status` | `step.outcome.status` |
| `step.failure_kind` | `step.outcome.failure.domain`（**仅 failed**） |
| `step.failure_code` | `step.outcome.failure.code`（namespaced，如 `selector.not_found`） |
| `step.evidence` | `step.outcome.observation`（`action` / `assertion` 两种） |
| `step.error` | `step.diagnostic`（**只供人读，不参与路由**） |
| `step.selector.selected_id` | `step.selector.resolution.selected.id` |
| `step.selector.candidate_count` | `step.selector.resolution.candidate_count` |
| `step.selector.requested_match` | `step.selector.request.match` |
| （无） | `step.selector.request.kind/value/constraints` —— 计划意图 |
| （无） | `step.device_session`、`step.artifacts[]`、`step.extensions` |

`blocked` 不再有 `failure_*`，改为 `outcome.cause`；`skipped` 改为 `outcome.reason`。

## 2. 最容易踩的三处语义变化

### 2.1 blocked 不再复制根失败

0.3-p0 把根失败的 `failure_kind/failure_code` 复制给每个未执行步骤，于是**一次根失败被放大成几十条缺陷**。v1：

```json
{"status": "blocked", "cause": {"type": "prior_step", "step_index": 2}}
```

**只有 `outcome.status == "failed"` 是 responsibility event。**
`blocked/capability` 与 `blocked/infrastructure` 各自只投影一次 defer/external disposition，后续 `prior_step` 不重复投影。

### 2.2 attempted 决定 status，不是 domain

同一个 `capability` 域，按**发现时点**落在不同 status：

| 发现时点 | 结果 |
|---|---|
| dispatch 前机器 probe 证明不可用 | `blocked` + `cause.type=capability` |
| 已 dispatch 后 adapter 返回不支持 | `failed` + `failure.domain=capability` |

`observation.performed=false` + `failed` 是**合法**组合（selector 0 候选时 action 确实没生效，但它被尝试过）。

### 2.3 断言失败就是 assertion，不是 selector

0.3-p0 会产出 `role=assertion + observed_present=false + failure_kind=selector`。v1 Schema 直接拒绝：带 `matched=false` 的 assertion observation 时 `failure.domain` 必须是 `assertion`。selector 失败导致断言**根本没跑**时，该步骤**不携带** assertion observation。

## 3. 无 trace 的非零退出

判定顺序**冻结**：

1. 先解析 stdout 的 `pre_run_reject`（exit code `2` + 合法 envelope → plan contract reject，属 testing/plan 问题）；
2. envelope 缺失/非法/协议错配 → 才进入既有「无 trace subprocess crash」分类；
3. stderr 只用于显示，**不参与**机器分型。

注意：**exit=2 本身不是 reject 信号**——steps 文件本身无法解析时同样 exit=2 但没有 envelope。**envelope 才是信号。**

## 4. 跨行规则要真的跑

Schema 只校验单对象。以下必须由 reducer/verifier 执行，契约包内的
[`reference_reducer.py`](../hylyre/contracts/reference_reducer.py) 是规范性 oracle：

- `prior_step` 只能指向同 case、更小 index 的**真实根 outcome**（禁止链式）；
- CaseResult 三轴与 legacy 中文 status 必须由 `steps[]` **复算**；
- run outcome 由 CaseResult 复算；
- `tool_calls` 必须等于 `steps[]` 的投影；
- `candidate_count` 与 `candidates` 长度一致（`unresolvable` 且 `candidate_countable=false` 时豁免）。

`golden/trace/invalid-crossrow/` 里 13 个样例**通过 Schema 但必须被 reducer 拒绝**——如果你的实现让它们全绿，说明跨行校验根本没运行。

## 5. 不做的事

- 不提供 `0.3-p0` → `0.4-p0` 迁移工具，也不保证完整读取兼容；
- legacy 产物**不得**被补字段后当作 v1 evidence；
- 同一个 run 不混用 0.3 与 0.4 step；
- `tool_calls` 是有损投影，**不得**反向用于补齐 trace。
