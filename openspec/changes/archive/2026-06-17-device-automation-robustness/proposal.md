## Why

`bc-openCard` 银行卡开卡在 HarmonyOS 真机（6.0.2(22)）经 4 轮迭代，暴露出工具链一批阻塞性限制：选择器只能单属性、无法区分「半模态上的下一步」与「背后页面同名下一步」（主流程卡死）；`assert_toast` 直接 TestError 且失败截图因 `None` 路径崩溃；长列表屏外项找不到、`scroll` 必须猜容器类型；步骤失败不落 UI 树/截图无法定位。这些都与被测应用无关，必须在 Hylyre 侧解决，否则结果页/详情页/toast 永远到不了。

## What Changes

- 新增**选择器解析器**：对 `dump_ui()` 树做富匹配（多属性 AND、`scope=top_overlay`、`within/below/above/after/before`、`index`、`visible/clickable/enabled`、`match=contains|exact`），按 overlay 层级/z-order 排序，文本节点抬升到最近可点祖先，算出中心坐标点击。
- `touch` 接入解析器：`by_text` **默认**走解析（取顶层 overlay 的可点项，救活 bindSheet 同名按钮场景），`by_id`/坐标走原生，`by_key` 走解析坐标；legacy `action.type=touch` 整块下发不漏富字段。
- `wait_for` / `wait_gone` 在含富字段时改为轮询 `dump_ui` + 解析器。
- 新增 planned step `scroll_to`（滚动直到目标可见，可选点击）与 `touch.scroll_into_view`；`scroll` 在省略容器时自动探测可滚动祖先（#7）。
- `assert_toast` 优雅降级：自有轮询、捕获 `check_toast` 异常防 `None` 截图崩溃、新增 `on_unsupported=skip|error` 与 `poll_interval`；引入 `StepSkipped` 并**跨层**贯通为「跳过」状态（steps 批量 / steps 报告 / 场景 runner）。
- 步骤失败诊断：`failure_dir` 落当时 UI 树 + 截图（诊断自身异常不掩盖主错误），路径写入 notes/trace；透传覆盖 session daemon 链路。
- 新增 `hylyre device force-stop` / `cold-restart`（positional `aa force-stop`，含启动等待），供下游 harness 调用；`app page save` 单设备自动取设备而非 exit 2、失败 stderr 输出根因。
- 文档：富选择器语义 / `scroll_to` / AlphabetIndexer 可达性 / 失败诊断 / toast skip；新增下游 harness 移交清单（#3 冷重启开关、#6 调用约定）。

## Capabilities

### New Capabilities
- `selector-resolution`: 纯函数将富选择器谓词解析为 UI 树中的命中并算出可点中心坐标，承载 overlay/z-order 排序、可点祖先抬升、候选可观测。

### Modified Capabilities
- `api-agent`: `touch`/`wait_for`/`wait_gone` 接入富选择器；新增 `scroll_to` planned step 与 `touch.scroll_into_view`；`scroll` 容器自动探测；`StepSkipped` 语义。
- `driver-hypium`: `assert_toast` 轮询 + 优雅降级 + 防 `None` 截图崩溃；`mouse_scroll` 省略 `at` 时自动探测容器；hdc `force_stop`/`shell`。
- `scenario-runner`: `failure_dir` 失败落 UI 树/截图并写 notes/trace；`StepSkipped` → 「跳过」在 plan/steps 两条路径与报告映射一致。
- `cli`: `hylyre device force-stop`/`cold-restart`；`run` / `run --steps-file` 的 `--failure-dir`；`run scroll-to`；`app page save` 单设备兜底与根因 stderr。
- `mcp-wrapper`: `hylyre_run_scroll_to` 工具；`failure_dir` 透传参数。

## Impact

- 代码：新增 `hylyre/api/selector_resolve.py`、`hylyre/api/exceptions.py`；改 `hylyre/api/agent.py`、`hylyre/api/planned_step_keys.py`、`hylyre/api/step_dispatch.py`、`hylyre/drivers/hypium/driver.py`、`hylyre/drivers/hypium/hdc_cli.py`、`hylyre/drivers/base/ui_driver.py`、`hylyre/scenario/runner.py`、`hylyre/scenario/steps_report.py`、`hylyre/cli/commands/steps_cmd.py`、`hylyre/cli/commands/loop_cmd.py`、`hylyre/cli/commands/run_cmd.py`、`hylyre/cli/commands/app_cmd.py`、`hylyre/cli/commands/device.py`、`hylyre/cli/tier_a_run_commands.py`、`hylyre/mcp/tier_a_tools.py`、`hylyre/session/daemon.py`。
- 测试：fakes（`FakeUiDriver` 可配置树 + touch 失败注入）；解析器纯函数单测；跨层 StepSkipped；force-stop argv 构造。
- 兼容：`by_text` 默认行为变化（多一次 dump，更稳）；提供 `prefer_native_text` 逃生开关。新 root key/工具向后兼容（旧 plan 不受影响）。
- 下游（不在本仓）：framework `device-test-run.ts` 的冷重启开关与 force-stop 语法、`app page save` 调用参数——以移交文档交付，不在本 change 改动。
