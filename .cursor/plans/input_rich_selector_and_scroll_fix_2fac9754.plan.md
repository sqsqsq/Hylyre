---
name: input rich selector and scroll fix
overview: 为 Hylyre 0.3.0 实现 v2 的 F1（input 支持 by_type/富选择器 + into 一步式）与 F2（scroll_to 对已在屏内目标立即命中），走完整 OpenSpec 流程并打发布件；F3 仅写入下游 harness 移交文档。
todos:
  - id: archive-old
    content: 先收口旧 change：实现类任务对照代码勾选；验证类（8.1 full pytest / 8.2 doctor+fakes smoke / 8.3 validate）必须实跑通过后再勾；随后 openspec archive，使 specs 落入 openspec/specs/ 基线，避免与新 change 同改 api-agent/selector-resolution
    status: completed
  - id: openspec
    content: 新建 OpenSpec change device-input-and-scroll-followups（基于 0.2.0 基线的 delta：api-agent 的 input 富选择器、selector-resolution 的 scroll_to 容器感知兜底），validate --strict 通过
    status: completed
  - id: f1-agent
    content: 改写 _apply_input_block 支持 by_type/by_key/富选择器/into：解析坐标→touch 聚焦→input_text 当前光标；仅 by_text/by_id 保持原生；action.type=input 整块下发
    status: completed
  - id: f1-ops
    content: selector_ops 新增 pred_from_input_block 与 resolve_input_hit（复用 resolve_targets/resolve_one 与候选日志）
    status: completed
  - id: f2-scroll
    content: scroll_until_visible 容器感知兜底：i==0 子树未命中时查全树，但仅接受 center 落在 scroll_root bounds 内的命中（保留容器语义，外部同名不短路）
    status: completed
  - id: tests
    content: 补单测：F1 by_type/into/action 富字段走解析、仅 by_id 不回归；F2 容器内已可见立即命中 swipes==0；保留并复跑现有 only_searches_inside_list（外部同名仍需滚动）
    status: completed
  - id: docs
    content: 更新 agent-plan-a.md（input 词汇+into+当前光标）、agent-loop.md（input 聚焦/ scroll_to 已可见）；downstream-harness-requests.md 追加 F3 并更新头部为 v2/0.3.0
    status: completed
  - id: release
    content: 同步 0.3.0 发布元信息（build_wheel.py manifest note/doc purpose、framework-vendor-bundle.md 含 F3）；bump 0.3.0，build_wheel --clean + --verify，全量 pytest（含 packaging slow）通过
    status: completed
isProject: false
---

## Hylyre v2 优化：input 富选择器 + scroll_to 兜底

### 范围与分流

- 本仓实现：**F1**（`input` 选择器表达力）、**F2**（`scroll_to` 已可见目标立即命中）。
- 下游移交：**F3**（`record-adapter` 写 local 时自动补写 DevEco 路径）→ 仅追加到 [docs/downstream-harness-requests.md](docs/downstream-harness-requests.md)，不改本仓代码（framework 仓不在工作区，受跨仓约束）。

### F1 — `input` 支持 by_type / 富选择器 / `into`（核心）

问题：`[_apply_input_block](hylyre/api/agent.py)` 仅取 `by_text`/`by_id`，其余被丢弃；底层 `[input_text](hylyre/drivers/hypium/driver.py)` 仅支持 `by_text`/`by_id`/当前光标。只有 placeholder 的 `TextInput` 无法定位 → 输入静默丢失。

设计（复用 v1 解析器，与 `touch` 一致；不拓宽 driver 契约）：

- 改写 `_apply_input_block`，分流：
  - **`into` 子选择器**（一步式）：`pred = block["into"]`。
  - **顶层富选择器**：`by_type`/`by_key`/`scope`/`within`/`index`/`all`/`visible`/`clickable`/`enabled`，或 `by_text`+`by_id` 之外的组合。
  - 命中富/`into`/`by_type`/`by_key` → 走解析器：`resolve_targets`→`touch(x,y)` 聚焦（带短 `focus_wait`）→`input_text(text)`（无选择器=当前光标），即宿主验证过的绕过手法内化。
  - **仅 `by_text` 或仅 `by_id`（无富字段）**：保持现状走 Hypium `input_text(by_text=/by_id=)`，不回归。
  - **无任何选择器**：当前光标输入（文档注明，建议先 `touch` 聚焦）。
- 新增 `selector_ops` 助手：`pred_from_input_block`（剥离 `text`/`into`/`mode`/`value`/`prefer_native_text`；有 `into` 用其作 pred）、`resolve_input_hit`（dump+resolve，复用 `resolve_one`/候选日志）。
- `action.type=="input"` 分支（[agent.py](hylyre/api/agent.py) `_apply_action_block`）改为去掉 `type` 整块下发 `_apply_input_block`（与 v1 的 touch 修法一致），使 `{"action":{"type":"input","by_type":"TextInput",...}}` 也走富选择器。
- CLI `[run input](hylyre/cli/__main__.py)`、MCP `[hylyre_run_input](hylyre/mcp/server.py)` 已整块透传 payload，自动获得新能力，无需改签名。

示例：

- `{"input":{"by_type":"TextInput","scope":"top_overlay","text":"123456"}}`
- `{"input":{"into":{"by_type":"TextInput","scope":"top_overlay"},"text":"123456"}}`

### F2 — `scroll_to` 容器感知兜底（修订：不破坏容器语义）

问题：`[scroll_until_visible](hylyre/api/selector_ops.py:115)` 指定 `in` 容器时，第 0 次只在 `scroll_root` 子树内 `resolve_targets`；目标已可见但不在该子树（`scroll_root` 选取偏差/子树范围问题）→ 空滚 15 次。现全树兜底仅 `container is None` 时触发。

约束（来自现有回归 [test_scroll_until_visible_only_searches_inside_list](tests/unit/test_device_automation_robustness.py:176)）：列表**外**的同名目标 (y=15, 在 List bounds `[0,100][500,600]` 之上) **不得**短路，必须滚动到列表**内**目标 (center 50,415)。因此**不能无条件全树兜底**。

修复（容器感知兜底）：`i==0` 时，
1. 先 `resolve_targets(scroll_root, pred)`（子树，命中即返回）；
2. 未命中再 `resolve_targets(tree, pred)` 全树，但**仅接受 `center` 落在 `scroll_root` bounds 内**的命中（用 `parse_bounds_rect` 校验），返回首个；
3. 仍无 → 进入既有滚动循环。

这样：F2 真实场景（目标在容器 bounds 内但被子树 resolve 漏掉）立即命中；而外部同名目标（在容器 bounds 外）被排除，现有测试保持绿。`container is None` 的旧全树兜底分支不变。

### OpenSpec 流程（先收口旧 change，避免双 active）

[device-automation-robustness](openspec/changes/device-automation-robustness/tasks.md) 仍 in-progress、`tasks.md` 全未勾，但其能力（selector/rich touch/scroll_to）均已实现并提交，且与本次 delta 同改 `api-agent`/`selector-resolution`。先收口：

1. 勾选其 `tasks.md`（对照已落地代码逐条确认）、`openspec validate device-automation-robustness --strict`、`openspec archive device-automation-robustness` → delta specs 并入 `openspec/specs/` 基线。
2. 在新基线上新建 change `device-input-and-scroll-followups`：`api-agent`（input 富选择器/`into`）、`selector-resolution`（scroll_to 容器感知兜底）两个 delta + proposal/design/tasks，`openspec validate --strict` 通过。
   - 若 archive 因环境受阻：退一步将 F1/F2 作为追加需求并入现有 change，但**不**再起第二个 active change。

### 测试（`tests/unit`）

- F1：注入「半模态内仅 placeholder 的 TextInput」树，断言 `input {by_type,scope}` 与 `input {into}` 都产生 `touch(x,y)` 聚焦事件 + 随后 `input_text(text, 无选择器)`；`action.type=input` 富字段同样走解析器；仅 `by_id` 仍走原生 `input_text(by_id=)` 不回归。
- F2：新增「容器内已可见」用例（目标在 `Scroll` bounds 内、首帧即在树中）→ 立即返回、`swipes==0`；**保留并复跑** [test_scroll_until_visible_only_searches_inside_list](tests/unit/test_device_automation_robustness.py:176)（外部同名仍 `swipes>=1`、命中列表内 center 50,415）。

### 文档

- [docs/agent-plan-a.md](docs/agent-plan-a.md) input 行补选择器词汇 + `into` + 无选择器落当前光标说明。
- [docs/agent-loop.md](docs/agent-loop.md) 富选择器/scroll_to 小节补 input 聚焦语义与「已可见即命中」。
- [docs/downstream-harness-requests.md](docs/downstream-harness-requests.md)：头部承接 v2/0.3.0，新增 **F3** 段（record-adapter 写 local 时一并探测补写 DevEco 路径的诉求 + 验收）。

### 发布（0.3.0 元信息同步 — P3）

F3 随 0.3.0 交付，需同步发布元信息，避免仍写死 v1 #3/#6：

- [scripts/build_wheel.py](scripts/build_wheel.py:100) manifest `note` 与 [integration_docs purpose](scripts/build_wheel.py:113)：措辞改为泛化（如「harness integration items: cold-restart / page save / personal-setup」或不枚举编号）。
- [docs/framework-vendor-bundle.md](docs/framework-vendor-bundle.md:21) 产物说明里 #3/#6 描述同步加 F3。
- bump `pyproject.toml` 0.2.0→0.3.0，`python scripts/build_wheel.py --clean` 产出 `dist/release/`（wheel + manifest + downstream 文档），`--verify` 通过；全量 `pytest`（含 packaging slow）。

### 验收对照

- F1：只有 placeholder 的输入框，单条 `input`（`by_type`/`into`）即稳定输入，无需 touch+input 两步。
- F2：目标已在屏内时 `scroll_to` 立即命中，不空滚。
- F3：移交文档说明 record-adapter 应一并补写 DevEco 路径（下游接入）。

