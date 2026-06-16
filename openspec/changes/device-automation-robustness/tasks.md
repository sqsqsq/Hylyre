## 1. 基础：解析器与异常

- [ ] 1.1 新建 `hylyre/api/exceptions.py`：`StepSkipped`、`SelectorResolutionError`
- [ ] 1.2 新建 `hylyre/api/selector_resolve.py::resolve_targets(tree, pred)`：base 选择器 + `match` + `visible/clickable/enabled` + `scope=top_overlay` + `within/below/above/after/before` + `all`(AND) + `index`；复用 `parse_bounds_rect`
- [ ] 1.3 实现文本节点 → 最近可点/enabled 祖先抬升；`all` 谓词作用于抬升后目标
- [ ] 1.4 实现排序（`overlay_rank desc → clickable → enabled → 树序`）、`candidates_summary`、0 命中抛 `SelectorResolutionError`
- [ ] 1.5 解析器纯函数单测：同名按钮+半模态、文本子节点抬升、`index`、`all`、0 命中诊断（注入树，无设备）

## 2. touch / wait_for 接入富选择器

- [ ] 2.1 `agent.py` 扩展 `_touch_from_payload`/`_apply_touch_block`：x/y 与 by_id 走原生；by_key 走解析坐标；by_text 默认 dump+解析（取顶层 overlay 可点项，0 命中原生兜底）；含富字段直接解析坐标点击
- [ ] 2.2 `prefer_native_text` 逃生开关
- [ ] 2.3 `_apply_action_block(type="touch")` 改为整块（去 `type`）下发 `_apply_touch_block`，不漏富字段
- [ ] 2.4 `_apply_wait_for_block`/`_apply_wait_gone_block`：含富字段时轮询 `dump_ui`+`resolve_targets`；单属性仍走 Hypium
- [ ] 2.5 `FakeUiDriver` 增加可配置返回树 + `touch(by_text)` 失败注入；单测：by_text 默认解析、by_key 坐标、legacy action 富字段、wait_for top_overlay

## 3. scroll_to / scroll 容器自动探测

- [ ] 3.1 `agent.py` 新增 `scroll_until_visible()` helper（容器子树内 resolve + 容器内 swipe + 指纹稳定/回弹终止，复用 collect 逻辑）
- [ ] 3.2 新增 `run_planned_scroll_to`（支持 `in`、`max_scrolls`、可选 `tap`）；`touch` 支持内联 `scroll_into_view`
- [ ] 3.3 `_apply_scroll_block`/`mouse_scroll`：`at` 省略时用 `_hylyre_hints.scrollable_containers` 自动探测，回退 `(0.5,0.5)`
- [ ] 3.4 注册 `scroll_to`：`planned_step_keys.py`、`step_dispatch.py`、`tier_a_run_commands.py`（`run scroll-to`）、`mcp/tier_a_tools.py`（`hylyre_run_scroll_to`）
- [ ] 3.5 单测：scroll_to 找到即点（注入逐步变化的树）、scroll 无 `at` 自动探测

## 4. Toast 优雅降级 + StepSkipped 跨层

- [ ] 4.1 `HypiumDriver.assert_toast`：自有轮询（`timeout`+`poll_interval`）、捕获 `check_toast` 异常、防 `None` 截图崩溃
- [ ] 4.2 `assert_toast` 块支持 `on_unsupported=skip|error`、`poll_interval`；skip 抛 `StepSkipped`
- [ ] 4.3 `run_steps_on_agent`（`steps_cmd.py`）：捕获 `StepSkipped` → `status:"skipped"`，`abort` 不中断
- [ ] 4.4 `steps_batch_to_scenario_result`（`steps_report.py`）：`skipped` → 「跳过」
- [ ] 4.5 `ScenarioRunner`（`runner.py`）：捕获 `StepSkipped` → `CaseResult(status="跳过")`；确认 `resolved_outcome` 不计失败
- [ ] 4.6 单测：toast skip 在 steps 批量与 plan 两条路径均为「跳过」；不崩溃

## 5. 失败诊断 failure_dir（含 session 透传）

- [ ] 5.1 `run_steps_on_agent`/`run_plan_on_agent` 加 `failure_dir`：失败 best-effort 落 `step-<n>.{json,png}`，吞诊断自身异常，路径写入 notes/批量 `diagnostics`
- [ ] 5.2 `run_cmd.py`：`hylyre run` / `run --steps-file` 加 `--failure-dir`（默认 report-out 同级 `failures/`），透传 runner
- [ ] 5.3 透传 session 链路：`execute_run_steps(failure_dir=)` → `_session_ipc` params → `daemon.py` `run_steps`/`run_step` → `run_steps_on_agent`（绝对路径）
- [ ] 5.4 MCP：steps/step 工具加 `failure_dir` 参数透传
- [ ] 5.5 单测：失败落盘并写 notes/trace；诊断自身异常不掩盖主错误；session daemon 透传

## 6. force-stop / cold-restart CLI + app page save

- [ ] 6.1 `hdc_cli.py`：`shell(args, serial)`、`force_stop(bundle, serial)`（positional）、可测 argv 构造（仿 `build_file_send_argv`）
- [ ] 6.2 `device.py`：`hylyre device force-stop`、`hylyre device cold-restart`（force-stop+`aa start`+启动等待）并接线注册
- [ ] 6.3 `app_cmd.py` `page_save`：单设备自动取设备而非 exit 2；零/多设备列出设备明确报错；失败 stderr 输出根因阶段
- [ ] 6.4 单测：force-stop/cold-restart argv 构造；page_save 单设备兜底分支

## 7. 文档 + 下游移交

- [ ] 7.1 更新 `docs/agent-loop.md`：富选择器语义、`scroll_to`、AlphabetIndexer 可达性（招商银行 Z 示例）、失败诊断、toast skip
- [ ] 7.2 更新 `docs/agent-plan-a.md`：touch/wait_for 富选择器字段、`scroll_to`、`assert_toast.on_unsupported`
- [ ] 7.3 更新 `AGENTS.md` 备忘（新增能力一行）
- [ ] 7.4 新增 `docs/downstream-harness-requests.md`：#3 阶段冷重启开关 + positional force-stop 接入、#6 page save 调用参数/页面命名/保存时机/stderr 归档，含验收命令

## 8. 收尾

- [ ] 8.1 全量 `pytest`（不接设备）通过，覆盖率不低于 CI 阈值（`--cov-fail-under=70`）
- [ ] 8.2 `hylyre doctor` 与 `--use-fakes` 假管线（`tests/e2e/fixtures/mock-test-plan.md`）冒烟通过
- [ ] 8.3 `openspec validate device-automation-robustness --strict` 通过
