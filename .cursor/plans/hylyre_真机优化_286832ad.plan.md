---
name: Hylyre 真机优化
overview: 围绕 bc-openCard 真机踩到的 7 条诉求，在本仓 Hylyre-core 侧实现：富选择器消歧（坐标兜底）、滚动到目标、toast 优雅降级、失败落 UI 树/截图、scroll 容器自动探测；并新增可被下游 harness 调用的 force-stop/冷重启 CLI；#3/#6 的 harness 调用层改动写成下游说明文档移交 framework 团队。
todos:
  - id: resolver
    content: 新建 hylyre/api/selector_resolve.py：纯函数解析 dump 树，支持 by_text/id/type/key + match(contains/exact) + visible/clickable/enabled + scope=top_overlay + within/below/above/after/before + all(AND) + index；语义写硬：文本节点抬升到最近可点祖先、按 overlay_rank/z-order 排序、返回 candidates_summary；复用 parse_bounds_rect
    status: completed
  - id: exceptions
    content: 新建 hylyre/api/exceptions.py：StepSkipped、SelectorResolutionError
    status: completed
  - id: selector-touch
    content: agent.py touch 接入解析器：x/y/by_id 走原生；by_key 走 resolver 坐标（driver.touch 无 by_key）；by_text 默认 dump+resolve（overlay 最上层+可点，候选写日志，0 命中再原生兜底）；含富字段直接解析器；legacy _apply_action_block(type=touch) 改为整块下发 _apply_touch_block 不漏富字段；可选 prefer_native_text 逃生开关
    status: completed
  - id: wait-for-rich
    content: agent.py wait_for/wait_gone 富选择器：含富字段时轮询 dump+resolve_targets 到出现/消失；纯单属性仍走 Hypium（回应 review P0#2）
    status: completed
  - id: scroll-to
    content: 新增 scroll_to root key 与 scroll_until_visible helper（容器子树内 resolve + 容器内 swipe + 指纹稳定终止）；touch 支持 scroll_into_view；注册 keys/dispatch/CLI/MCP
    status: completed
  - id: scroll-autodetect
    content: _apply_scroll_block/mouse_scroll：at 省略时用 _hylyre_hints 自动探测可滚动容器，回退 (0.5,0.5)（#7）
    status: completed
  - id: toast
    content: HypiumDriver.assert_toast 自有轮询 + 捕获 check_toast 异常防 NoneType 崩溃；assert_toast 块加 on_unsupported=skip/poll_interval，skip 抛 StepSkipped
    status: completed
  - id: skip-wiring
    content: StepSkipped 跨层打通：steps_cmd 出 skipped 且 abort 不中断、steps_report 映射「跳过」、runner 出「跳过」且 resolved_outcome 不计失败（回应 review P1#6）
    status: completed
  - id: failure-diag
    content: run_plan_on_agent/run_steps_on_agent 加 failure_dir：失败时 best-effort 落 dump.json+screenshot.png（吞诊断自身异常），路径写入 notes/trace；CLI/MCP 加 --failure-dir；透传覆盖 session daemon 路径 execute_run_steps→_session_ipc→daemon run_steps/run_step→run_steps_on_agent（绝对路径，同机本地写盘）
    status: completed
  - id: force-stop-cli
    content: hdc_cli 加 shell()/force_stop()（positional aa force-stop）；device.py 加 hylyre device force-stop / cold-restart（含启动等待）并接线；闭环依赖下游接入
    status: completed
  - id: page-save
    content: app_cmd.page_save：单设备时自动取设备而非 exit 2、否则列出设备明确报错；失败 stderr 输出根因（dump/写盘阶段）（#6 本仓侧）
    status: completed
  - id: tests
    content: 解析器三棵树单测（同名按钮+半模态/文本子节点抬升/长列表）；FakeUiDriver 可配置树+touch 失败注入覆盖 by_text 默认解析/scroll_to/wait_for 富选择器/失败诊断；StepSkipped 跨层；force-stop argv 构造单测
    status: completed
  - id: docs
    content: 更新 docs/agent-loop.md（选择器语义/scroll_to/AlphabetIndexer/失败诊断/toast skip）、docs/agent-plan-a.md（新字段）、AGENTS.md；新增 docs/downstream-harness-requests.md（#3 冷重启+positional、#6 调用约定+验收命令）
    status: completed
  - id: openspec
    content: 走 openspec-propose 将本计划升级为正式 change（规格+任务）——已完成：openspec/changes/device-automation-robustness（proposal/design/specs/tasks，validate --strict 通过）
    status: completed
isProject: false
---

# Hylyre 真机自动化优化

## 范围与分流

- **本仓实现（Hylyre-core）**：#1 选择器表达力、#2 toast、#4 滚动到目标、#5 失败诊断、#7 scroll 容器自动探测；#6 中 `hylyre app page save` 的 CLI 健壮性。
- **额外能力**（你选的方案）：在本仓新增 `hylyre device force-stop` / `cold-restart`（positional 语法），让下游 harness 直接调用，改动更小。
- **下游 framework 仓（本工作区不存在 `framework/`，受「禁止跨仓修改」约束）**：#3 阶段冷重启开关、`device-test-run.ts:434` 的 `-b`→positional、#6 harness 调 `app page save` 的参数。这些写进新文档 `docs/downstream-harness-requests.md` 移交，不在本仓改代码。

## 核心设计：富选择器走「dump 树 → 解析 → 坐标点击」

现有 `touch` 只支持 `x/y`、`by_text`、`by_id`，底层走 Hypium `BY`（单属性、命中树序第一个）。新增一个**纯函数解析器**，对 `dump_ui()` 的树做匹配并算出命中元素中心坐标，再 `touch(x,y)`。这样无需被测应用加 id，且可用注入树做单测。复用已有 `parse_bounds_rect`（`hylyre/ui_dump_hints.py`）、`find_scroll_root`/`gather_text_items`（`hylyre/cli/commands/collect_cmd.py`）。

新建 `hylyre/api/selector_resolve.py`：

```python
def resolve_targets(tree: dict, pred: dict) -> list[ResolvedHit]:
    """返回排序后的命中，每项含 center=[x,y] / tap_bounds / attrs / overlay_rank / depth / candidates_summary。
    pred 支持:
      base:  by_text / by_id / by_type / by_key
      文本匹配模式: match="contains"(默认) | "exact"
      过滤:  visible / clickable / enabled
      限定:  scope="top_overlay" / within(锚点选择器) /
             below|above|after|before(锚点)
      组合:  all=[子选择器...]（AND）
      选择:  index(0-based)
    """
```

**选择器语义要写硬（回应 review P1#5）**——否则会变成另一个脆弱选择器：

- **文本节点 → 可点祖先抬升**：文本常在子 `Text` 上、`clickable`/`onClick` 在父 `Button`/容器上。匹配到文本节点后，向上找**最近的 `clickable=true` 或 `enabled` 祖先**作为点击目标（点其中心），找不到再退回文本节点本身。
- **`all`(AND) 的「节点 vs 抬升目标」语义（回应 review 第 3 点）**：`all=[{by_text},{by_type:"Button"},{clickable},...]` 时，**先用 `by_text` 命中文本节点并抬升到 tap target**，再把 `by_type/clickable/enabled` 等谓词作用在**抬升后的目标祖先**上判定，而不是要求它们落在同一个 `Text` 节点（否则 `by_text 下一步 + by_type Button` 会因文本在 Text 上而永远不匹配）。
- **`visible` ≠ 未被遮挡**：`bounds` 面积>0 只代表「有尺寸」，不代表没被半模态盖住。因此**遮挡判定靠 z-order/overlay 层级**而非 visible：解析器对每个命中标注 `overlay_rank`（所属顶层 window/overlay 的层级），排序时**overlay 越靠上越优先**，再按 clickable、再按树序。
- **排序**：`overlay_rank desc → clickable desc → enabled desc → 树序`。`index` 在排序后的列表上取。
- **候选可观测**：命中>1 时返回 `candidates_summary`（每个候选的 text/id/bounds/overlay_rank），写进日志与 `SelectorResolutionError`，便于排障（回应 #5）。
- `scope:"top_overlay"`：HarmonyOS `bindSheet` 在树里产生独立 overlay/根 window 节点。启发式：按 type 含 `Sheet/Dialog/Popup/Menu/ModalWindow/Overlay` 收集 overlay 根；多 window 时取最后一个（最上层）；只在该子树内匹配。文档注明为启发式 + 兜底。

### #1 选择器接入（修正：by_text 默认走解析器，而非「原生先行」）

> **对上一版 hybrid 的修正（回应 review P0#1）**：Hypium 原生 `BY.text` 在同名按钮 + 半模态场景会**静默点中背后那个、不抛错**，因此「原生先行、失败再兜底」根本不会触发兜底。改为按选择器类型分流：

改 `hylyre/api/agent.py` 扩展 `_touch_from_payload` / `_apply_touch_block`：

- **`x/y`、`by_id`（唯一性强）**：走 Hypium 原生（快），不变。
- **`by_key`：走 resolver 坐标点击**（回应 review 第 2 点）。因为 `UiDriverBase.touch`（`ui_driver.py:49`）只支持 `x/y/by_text/by_id`，并无 `by_key`；不加宽三处 driver 接口，统一让 `by_key` 经 `resolve_targets` 算坐标后 `touch(x,y)`，与 driver 契约一致。
- **`by_text`（默认即解析器路径）**：`dump_ui()` → `resolve_targets(pred + visible=true,clickable优先)` →
  - 命中唯一：`touch(x,y)`；
  - 命中多个：默认取排序后第一个（overlay 最上层 + 可点），并把候选写日志（满足 requests 第 67-68 行「默认值优化救活 bindSheet」）；
  - 命中 0：原生再试一次兜底，仍失败 → 抛 `SelectorResolutionError`（含候选/dump 摘要）。
- **含富字段（scope/within/below/index/all/by_type/scroll_into_view…）**：直接 dump→解析→坐标点击。
- **legacy `action` 包装不漏富字段（回应 review 第 1 点）**：当前 `_apply_action_block`（`agent.py:147`）在 `type=="touch"` 时只挑 `x/y/by_text/by_id` 就调 `_touch_from_payload`，绕过 resolver。改为把**去掉 `type` 的完整 dict** 交给 `_apply_touch_block`，使 `{"action":{"type":"touch","by_text":"下一步","scope":"top_overlay"}}` 也走富选择器（input/swipe/scroll 等分支已是「去 type 整块下发」，保持一致）。

> 性能：`by_text` 每次多一次 `dump_ui`。可在 `--session`/MCP open_session 下复用连接，dump 本身已有 `diagnostic_log` 计时；如需可加 `prefer_native_text:true` 逃生开关回到旧行为（默认关）。

示例：`{"touch":{"by_text":"下一步","scope":"top_overlay"}}`、`{"touch":{"by_text":"下一步","index":1}}`、`{"touch":{"all":[{"by_text":"下一步"},{"by_type":"Button"}],"scope":"top_overlay"}}`。

### #1b wait_for / wait_gone 也接富选择器（回应 review P0#2）

requests 第 32 行明确 `touch` 与 `wait_for` 都受限，但当前 `_apply_wait_for_block`（`agent.py:461`）仍走 `require_selector` 单属性。改为：

- `wait_for`/`wait_gone` 块识别富字段时，改用**轮询 `dump_ui()` + `resolve_targets`**（到/消失为止，复用现有 `timeout`），可表达「等顶层半模态里的某按钮出现」。
- 无富字段（纯单属性）保持走 Hypium `wait_for_component`（不回归）。

### #4 + #7 滚动到目标 / 容器自动探测

- 新增 planned root `scroll_to`：`{"scroll_to":{"by_text":"招商银行","in":{"by_type":"List"},"max_scrolls":15}}`，可选 `tap:true` 找到即点击。实现共享 helper `scroll_until_visible()`：循环 `dump_ui` → 解析器在容器子树内找目标 → 未中则在容器内 `swipe`（复用 `_build_swipe_payload` + collect 的「指纹稳定/回弹」终止），命中即返回坐标。
- `touch` 内联 `scroll_into_view:{by_type:"List"}`：先 `scroll_until_visible` 再点。
- #7：`_apply_scroll_block`/`mouse_scroll` 在 `at` 省略时，先用 `_hylyre_hints.scrollable_containers` 自动探测最近可滚动容器并在其中心滚动，失败回退现有 `(0.5,0.5)`。低风险、保留旧行为。
- **AlphabetIndexer（#7/P2，回应 review P2#7）**：`scroll_to` 解决了「滚到底部项」；对 A-Z 索引（`AllBanksPage` 的 `AlphabetIndexer`），不另造能力，而是在 `docs/agent-loop.md` 写明可达性——可用 `touch` 富选择器点字母（`{"touch":{"by_text":"Z","within":{"by_type":"AlphabetIndexer"}}}` 或按 `by_type:"AlphabetIndexer"` + 字母文本/坐标）快速定位，再 `scroll_to`/`touch` 目标行。文档给出 bc-openCard「招商银行(Z)」示例。

### #2 Toast 优雅降级 + 不崩（skip 是跨层契约，不止改 driver）

> 回应 review P1#6：`report-sections.yaml:11` 已允许「跳过」状态，但执行链路目前**没有跳过这条路**——`run_steps_on_agent`（`steps_cmd.py:47`）只有 `ok/error`，`steps_report.py:49` 把非 ok 一律映射「失败」，`ScenarioRunner.run_plan_on_agent` 把异常一律记「失败」。所以 StepSkipped 必须**端到端打通**。

driver 侧（`hylyre/drivers/hypium/driver.py` `assert_toast`）：
- 自有轮询循环（`timeout` + 新增 `poll_interval`）反复调 `raw.check_toast`，捕获其 `TestError`/异常转清晰报错；避免 Hypium 内部「失败自动截图」拿到 None 路径而崩（我方层先吞次级异常，必要时预设 Hypium 报告目录）。
- `assert_toast` 块新增 `on_unsupported:"skip"|"error"`（默认 error）；识别「该版本不支持/超时无 toast」且 skip 时抛 `StepSkipped`。

跨层接线（关键）：
- 新建 `hylyre/api/exceptions.py`：`StepSkipped`、`SelectorResolutionError`。
- `run_steps_on_agent`（`hylyre/cli/commands/steps_cmd.py`）：捕获 `StepSkipped` → `status:"skipped"`（区别于 `error`），`on_fail=abort` 时**不**中断。
- `steps_batch_to_scenario_result`（`hylyre/scenario/steps_report.py:49`）：`skipped → "跳过"`。
- `ScenarioRunner._run_case_on_agent` / `run_plan_on_agent`（`hylyre/scenario/runner.py:117`）：捕获 `StepSkipped` → `CaseResult(status="跳过")`；确认 `resolved_outcome` 不把「跳过」计为失败。

### #5 失败落 UI 树 + 截图

- `ScenarioRunner.run_plan_on_agent` 与 `run_steps_on_agent` 新增 `failure_dir`：步骤异常时 best-effort `dump_ui()`+`screenshot()` 写 `failure_dir/step-<n>.{json,png}`，**捕获诊断自身异常**（不让截图崩盖住主错误，呼应 #2b），把相对路径写进 `CaseResult.notes` / 批量 `results[].diagnostics`，进而进 trace `cases[].notes`。
- `hylyre run` / `run --steps-file` 加 `--failure-dir`（默认取 report-out 同级 `failures/`）；MCP 对应加参。
- **`failure_dir` 必须覆盖 session daemon 路径（回应 review 实现提醒）**：`hylyre run --steps-file --session …` 的链路是 `execute_run_steps`(`steps_cmd.py:118`)→`_session_ipc`→daemon `run_steps`(`daemon.py:81`)→`run_steps_on_agent`，现无透传点。需把 `failure_dir` 一路传：`execute_run_steps(failure_dir=)` → IPC `params["failure_dir"]` → `_dispatch` 的 `run_steps`/`run_step` 取出传给 `run_steps_on_agent`/`dispatch`。daemon 与 CLI 同机（127.0.0.1），路径字符串可直接透传、由 daemon 进程本地写盘。session 模式下 `failure_dir` 需用绝对路径。

### #3 force-stop / 冷重启 CLI（移交下游用）— 注意闭环边界

> 回应 review P0#3：本仓只能交付「Hylyre-core 子任务」，#3 真正闭环（阶段跑默认冷重启、每轮干净首页）取决于**下游 harness 是否改用本 CLI 并打开开关**。plan 不声称 #3 在本仓完成。

- `hylyre/drivers/hypium/hdc_cli.py` 加 `shell(args, serial)` 与 `force_stop(bundle, serial)`（positional `aa force-stop <bundle>`，不再用本机失败的 `-b`）。
- `hylyre/cli/commands/device.py` 加 `hylyre device force-stop --bundle [--device-sn]` 与 `hylyre device cold-restart --bundle [--ability] [--wait-time]`（force-stop + `aa start` + 起来后等待/确认主 Ability）。
- 闭环验收命令写进移交文档：下游每轮跑前 `hylyre device cold-restart`，连续多轮互不污染。

### #6 app page save 健壮性（本仓侧）+ 失败可观测

> 回应 review P1#4：requests 第 185 行不只要「不传 device 别 exit 2」，还要「抓本轮访问过的页面」+「失败 stderr 落 run 目录」。后者属下游调用层（写进移交文档约定页面命名/保存时机/错误日志归档）；本仓侧改 CLI 行为本身：

`hylyre/cli/commands/app_cmd.py` `page_save`：
- 未传 `--from-dump`/`--session`/`--device-sn` 且**仅连一台设备**时自动取该设备（而非 exit 2）；否则给出可操作明确报错（列出已连设备）。
- `_live_payload`/`save_page_snapshot` 失败时 stderr 输出**根因**（当前 exit 1 仅 `str(e)`，补充 dump/写盘阶段标识），便于下游把 stderr 落 run 目录。
- 移交文档说明：本轮访问页面的「页面命名 + 保存时机（每步后/关键页后）+ 错误日志归档路径」由 harness 调用层约定。

## 接线 / 测试 / 文档

- 注册新 root key：`hylyre/api/planned_step_keys.py`（加 `scroll_to`）、`hylyre/api/step_dispatch.py`（映射 `run_planned_scroll_to`）、`hylyre/cli/tier_a_run_commands.py`（`scroll-to` + 示例）、`hylyre/mcp/tier_a_tools.py`（`hylyre_run_scroll_to` + 描述）。
- 富选择器/StepSkipped 的接线面要全：`touch` / `scroll_to` / `wait_for` / `wait_gone` 都接 `resolve_targets`；StepSkipped 贯穿 plan(`runner.py`)、steps(`steps_cmd.py`/`steps_report.py`)、session daemon、MCP `hylyre_run_*` 返回，避免只在一条路径生效。
- 测试：
  - 解析器纯函数单测（注入「半模态盖同名按钮」「文本在子 Text、clickable 在父 Button」「长列表虚拟化」三棵树，断言命中坐标、overlay 排序、可点祖先抬升、候选 summary）。
  - `FakeUiDriver` 增加可配置返回树 + `touch(by_text)` 失败注入，覆盖 by_text 默认解析、`by_key` 走坐标、scroll_to、wait_for 富选择器、失败诊断落盘。
  - legacy `action` 富字段：`{"action":{"type":"touch","by_text":"下一步","scope":"top_overlay"}}` 走 resolver（断言坐标点击而非原生 by_text）。
  - `all`(AND) 抬升语义：`all=[{by_text},{by_type:"Button"}]` 文本在子 `Text`、Button 在父，断言命中父 Button 中心。
  - StepSkipped 跨层：steps 批量出 `skipped`、steps_report 映射「跳过」、scenario runner 出「跳过」且 `resolved_outcome` 不计失败。
  - force-stop/cold-restart argv 构造单测（仿 `build_file_send_argv`，不真跑 hdc）。
- 文档：更新 `docs/agent-loop.md`（富选择器语义/`scroll_to`/AlphabetIndexer/失败诊断/toast skip）、`docs/agent-plan-a.md`（新 JSON 字段：touch/wait_for 富选择器、scroll_to、assert_toast.on_unsupported）、`AGENTS.md` 备忘；新增 `docs/downstream-harness-requests.md`（#3 冷重启开关+positional force-stop、#6 page save 调用参数/页面命名/保存时机/stderr 归档 的移交清单 + 验收命令）。
- **已完成**：本计划已通过 `openspec-propose` 升级为正式 change `openspec/changes/device-automation-robustness`（proposal/design/specs×6/tasks，`openspec validate --strict` 通过）。后续实现以该 change 的 `tasks.md` 为准，本 plan 仅作速览。

## 验收对照

- #1：半模态盖同名「下一步」时稳定点到半模态按钮，无需改被测源码；`by_text` 默认即避开背后被遮挡项。
- #1b：`wait_for`/`wait_gone` 能等顶层半模态内的目标。
- #2：`assert_toast` 要么真断言，要么 `on_unsupported:skip` → 全链路标记「跳过」（非失败），且不再 NoneType 崩溃。
- #4/#7：不预知步数滚到长列表底部项并点击；`scroll` 不填容器也能滚；文档说明 AlphabetIndexer 可达性。
- #5：失败即有当时 UI 树/截图与相对路径（诊断自身异常不掩盖主错误）。
- #3（边界）：本仓 `hylyre device force-stop`/`cold-restart`（positional）真机生效；阶段跑互不污染的最终闭环依赖下游 harness 接入（见移交文档）。
- #6（边界）：本仓 `page_save` 单设备自动取设备 + 失败根因 stderr；「抓本轮访问页面」的调用约定见移交文档。