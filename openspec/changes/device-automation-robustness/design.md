## Context

Hylyre 当前 planned-step 选择器（`hylyre/api/selectors.py`）只允许 `by_text/by_id/by_type/by_key` 四选一，底层 `HypiumDriver.touch` 把 `BY.text` 交给 Hypium，命中树序第一个且无 z-order 概念。HarmonyOS `bindSheet` 半模态会在 UI 树里与背后页面**并存同名按钮**，导致 `by_text:"下一步"` 点中背后被遮挡项、主流程卡死。`assert_toast` 直接调 `raw.check_toast`，在该 OS 版本返回 TestError，且 Hypium 失败自动截图拿到 `None` 路径再次崩溃。失败步骤无 UI 树/截图。这些已用「手动 force-stop、改点顶部银行、List 修正」等绕过验证到短信半模态，唯独同名「下一步」和 toast 必须靠工具链优化。

已有可复用基建：`parse_bounds_rect`（`hylyre/ui_dump_hints.py`）、`find_scroll_root`/`gather_text_items`/swipe-until-stable（`hylyre/cli/commands/collect_cmd.py`）、`augment_ui_dump_payload` 的 `_hylyre_hints.scrollable_containers`、`build_file_send_argv` 式的可测 argv 构造（`hdc_cli.py`）。`framework/` 不在本仓，受「禁止跨仓修改」约束。

## Goals / Non-Goals

**Goals:**
- 无需被测应用加 id，即可稳定区分「顶层 overlay 上的控件」与「背后同名控件」。
- toast 断言不再崩溃；不支持时可降级为「跳过」而非「失败」。
- 长列表屏外项可达；scroll 不强制指定容器类型。
- 步骤失败留下当时 UI 树 + 截图。
- 提供 positional force-stop/cold-restart CLI，缩小下游 harness 改动面。
- 全部改动可在无设备的 `pytest` 中覆盖（fakes + 纯函数解析器）。

**Non-Goals:**
- 不在本仓修改下游 framework（#3 阶段冷重启接入、#6 harness 调用参数）——以移交文档交付。
- 不重写 Hypium toast 底层捕获（无法在本仓验证），只做轮询 + 降级。
- 不引入运行态 VLM 依赖；解析器纯结构化。

## Decisions

### D1: 富选择器走「dump 树 → 纯函数解析 → 坐标点击」，而非扩展 Hypium BY 组合
新增 `hylyre/api/selector_resolve.py::resolve_targets(tree, pred) -> list[ResolvedHit]`。把所有富语义（AND、scope、相对定位、index、过滤）在 Hylyre 侧对 `dump_ui()` 树求解，命中后用元素中心坐标 `touch(x,y)`。
- 备选：链式 Hypium `BY.isAfter/within/...`——表达力有限、无法表达 z-order/overlay、且不可在无设备下单测。否决。
- 收益：纯函数、可注入树单测；坐标点击对 overlay/遮挡稳定。

### D2: `by_text` 默认即解析器路径（修正「原生先行」）
Hypium 原生 `BY.text` 对同名按钮会**静默点中背后那个、不抛错**，所以「原生先行、失败兜底」不会触发兜底。因此：`x/y`、`by_id` 走原生；`by_key` 走解析坐标（`UiDriverBase.touch` 无 `by_key`，不加宽 driver 契约）；`by_text` 默认 `dump_ui` + 解析，取排序后第一个（overlay 最上层 + 可点），0 命中再原生兜底。提供 `prefer_native_text:true` 逃生开关回到旧行为。
- 权衡：`by_text` 每次多一次 dump（session/MCP 下连接复用，dump 有计时日志）。可接受，换取正确性。

### D3: 选择器语义写硬，避免脆弱
- **文本节点 → 可点祖先抬升**：匹配文本节点后向上找最近 `clickable=true`/`enabled` 祖先作为 tap target。
- **`all`(AND)**：先由 `by_text` 命中文本节点并抬升，`by_type/clickable/enabled` 作用于**抬升后的目标**（否则文本在子 `Text`、Button 在父会永不匹配）。
- **遮挡靠 z-order 而非 `visible`**：`visible`（bounds 面积>0）≠未被半模态遮挡；每个命中标 `overlay_rank`，排序 `overlay_rank desc → clickable → enabled → 树序`，`index` 在排序后取。
- **`scope=top_overlay`** 启发式：按 type 含 `Sheet/Dialog/Popup/Menu/ModalWindow/Overlay` 收集 overlay 根，多 window 取最后（最上层）。
- 命中>1 返回 `candidates_summary`（写日志与 `SelectorResolutionError`）。

### D4: `StepSkipped` 是跨层契约
`report-sections.yaml` 已允许「跳过」，但执行链路无此路径：`run_steps_on_agent` 只有 ok/error，`steps_report.py:49` 非 ok→失败，`runner` 异常→失败。新增 `hylyre/api/exceptions.py::StepSkipped`，并在 `steps_cmd`（出 `skipped`、`abort` 不中断）、`steps_report`（skipped→跳过）、`scenario/runner`（捕获→「跳过」且 `resolved_outcome` 不计失败）三处贯通。`assert_toast.on_unsupported=skip` 抛出它。

### D5: 失败诊断 best-effort 且不掩盖主错误；透传 session daemon
`failure_dir` 下落 `step-<n>.{json,png}`。诊断采集自身用 try/except 吞掉（直接修复 #2(b) 在我方层的等价问题）。链路 `execute_run_steps → _session_ipc(params["failure_dir"]) → daemon run_steps/run_step → run_steps_on_agent` 全程透传；daemon 同机（127.0.0.1）本地写盘，session 模式要求绝对路径。

### D6: force-stop 用 positional + 纯 hdc（不依赖 Hypium）
`hdc_cli` 加 `shell(args, serial)` 与 `force_stop(bundle, serial)`，用 `aa force-stop <bundle>`（本机 `-b` 形式报「未安装」）。`cold-restart` = force-stop + `aa start` + 启动等待。argv 构造可单测（仿 `build_file_send_argv`），不真跑设备。

### D7: 接线面对齐
新 root key `scroll_to` 注册到 `planned_step_keys`、`step_dispatch`、CLI `run scroll-to`、MCP `hylyre_run_scroll_to`；`--failure-dir` 在 `run`/`run --steps-file`/MCP 同步暴露并透传。

## Risks / Trade-offs

- [overlay 启发式误判：某些 sheet 类型名不在白名单] → 提供 `within`/`index` 等显式维度兜底；类型名列表可扩展并在文档列出；保留 `prefer_native_text`。
- [`by_text` 默认多一次 dump 带来时延] → 连接复用（session/MCP）；逃生开关 `prefer_native_text`；dump 已有 `diagnostic_log` 计时便于评估。
- [坐标点击在解析与点击之间界面发生变化（竞态）] → `scroll_to`/`wait_for` 采用「重新 dump 再判定」的轮询；解析紧邻 touch，窗口极小。
- [toast 在该 OS 真实不可断言] → `on_unsupported=skip` 明确降级为「跳过」，不阻断 P0 100%。
- [失败诊断截图自身失败] → try/except 吞掉，绝不覆盖主错误（这正是 #2(b) 的修复目标）。
- [#3/#6 真正闭环依赖下游] → 本 change 只交付 Hylyre-core 子任务 + 移交文档，验收明确标注边界。
