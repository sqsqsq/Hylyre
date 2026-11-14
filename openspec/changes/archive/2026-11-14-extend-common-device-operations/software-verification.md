# 软件实施与验收记录

日期：2026-11-14。状态：**软件、代码检视及计划内 21 项真机验收完成。多指抬起坐标的环境限制见下文**。未提交、打包、发布或归档。

## 0.6.0 工作区最终整批回归（2026-11-14）

运行 `python -m pytest --cov=hylyre --cov-fail-under=70 -q -W ignore::DeprecationWarning --tb=short`，**1475 passed、2 skipped、2 deselected、0 failed**，覆盖率 **76.31%**，耗时 97.59 秒。日志保存在验收机的 `.hylyre/verification/extend-common-device-operations/0.6.0-final-regression.log`。默认 pytest 配置排除两项 slow 打包测试。下文的 1383 是较早实现阶段的运行记录，保留用于追溯。

## 范围核对

| 范围 | 实现与证据 |
|---|---|
| 18个新操作、touch扩展及属性等待 | api/common_operation_contract.py统一预检；common_operations.py沿OperationOutcome/ledger/builder执行；101项首轮新单元及后续边界回归 |
| 全部入口 | planned_step_keys/step_dispatch、CLI原子JSON、MCP、steps、plan、session/daemon；tests/integration/test_common_entrypoint_parity.py最终64项通过 |
| 驱动与fake | 可选基类接口不增加abstractmethod；Hypium原生映射；单/多指一次完整注入；离线查询/断言/set_checked/Shell为blocked |
| 定位与属性 | 同一dump解析全部端点/区域，唯一性/屏幕/区域边界验证，Rect原点只抵消一次；三态属性共用于过滤/查询/set_checked |
| 状态/应用 | set_checked读前/必要时点击一次/有界复读；精确已安装包匹配；无前台bundle阻塞，ability缺失明示 |
| Shell | hdc_cli.structured_shell独立子shell与唯一尾标记、argv宿主边界、固定serial、CRLF兼容、设备/传输码分开、超时回收与远端未知、完整raw log产物 |
| 结果协议 | 无schema或协议版本升级；查询仅action facts，属性断言用presence/absence，使用合法既有/厂商命名错误码；新旧golden/report verify均覆盖 |
| 使用文档 | docs/common-device-operations.md全操作JSON、默认值/限制/兼容变化；agent-plan-a、agent-loop、CHANGELOG及CLI/MCP帮助已同步 |

## 检查及日志

- 本机 Python 3.14.5，Hypium 6.0.7.210；签名、KeyCode符号与适配边界见 [interface-verification.md](interface-verification.md)。项目pyproject/CI无mypy、pyright或其它类型检查门禁；使用已有pytest门禁及 `python -m compileall -q hylyre`，未引入整仓类型整治。
- 首轮全量因两个既有固定inventory测试未随新增命令更新而失败，1341 passed / 2 failed / 2 skipped；已更新真实命令/工具集合及选项归属测试，没有修改产品行为以绕过测试。
- 真机返修前的整批命令：`python -m pytest --cov=hylyre --cov-fail-under=70 -q -W ignore::DeprecationWarning --tb=short`。结果 **1383 passed, 2 skipped, 2 deselected**，耗时92.06秒，覆盖率 **75.63% >=70%**。日志：`.hylyre/verification/extend-common-device-operations/software-full-regression.log`。跳过是已有schema场景，deselected是配置排除的slow打包测试；不为本次实施运行发布/打包。
- 上述整批启动后补充了窄边界：nested all不可观测属性、JSON未分隔后缀拒绝、无屏幕边界/区域边界、摘要新布尔字段、scroll_into_view字段传递；对应目标检查 **190 passed**（test_common_device_operations、step_text、ui_dump_filter、find_cmd、mcp_server、common_entrypoint_parity）。继续复用有效全量结果，不无依据重复整批。
- 共享批量入口补整批预检：非法后续步骤不会先执行前一步或bundle启动，192项对应run_steps/report/MCP/session/入口目标检查通过；session额外转发artifact_base，确保Shell log路径相对authoritative trace。
- 独立Shell目标检查含旧HDC兼容、非零/缺标记/超时/特殊字符/大输出、真实本地宿主进程回收；已有跨入口目标测试覆盖默认60秒及序列化，不运行破坏性设备命令。
- `openspec validate extend-common-device-operations --strict` 与 `git diff --check` 通过。report verify由64项集成检查实际生成trace/report并运行，既有schema/golden检查包含在整批中。

## 真机验收结果

2026-11-14，OpenHarmony 7.0.0.111 / API 26、Hypium 6.0.7.210、hdc 3.2.0d。21 个命名项全部获得真机正例，负例与边界按计划复用真机或 stub。[逐项结果和报告路径](acceptance/device-acceptance.md)。

普通华为浏览器中，双指滑动、多点点击和多指轨迹的第二指 UP 相对目标出现约 52 CSS 像素偏差。相同设备及页面进入全屏后，原验收标准下两指 DOWN、末 MOVE 和 UP 均命中，三个 report verify 全部通过。证据支持报告环境差异，无法单靠网页事件断定偏差发生在系统注入还是浏览器分发。保留普通模式记录和全屏正例，未做生产坐标补偿。

已核实的SDK限制会诚实blocked：无法确认serial；缺原生能力；API<20或无法确认API时的显式drag.press_time；本机SDK静默忽略的press_time<1.5；属性不可观测；无前台bundle。stderr不可独立获取按false/null标记，不阻断验收。

## Claude 首审返修（B1–B4）

首审真实结论为不通过；本节记录对应软件返修，同一检视会话随后确认 B1–B4 均已修复，详见第二轮记录。

| 意见 | 最终修改与回归 |
|---|---|
| B1 pinch非法vertical | 共享枚举收紧diagonal/horizontal，文档与parity fixture同步；两操作vertical均在连接前拒绝 |
| B2非法使用not_found | 屏幕/area越界、匹配area无边界、非输入clear_text改PlannedStepContractError→contract.invalid_step；非checkable在读取checked前返回contract.invalid_step并保留唯一目标；真实零候选仍not_found |
| B3点击后确认异常 | 成功点击后的复读异常立即failed/state_confirmation_failed，记录performed=true、before、changed=true、after=null及错误类型/信息；不重试点击；已覆盖能力丢失、目标移动/歧义及连接失败 |
| B4文本升父 | 同一resolver新增匹配节点模式；组件数据操作始终使用实际节点，等待仅在含checked/checkable/focused（含嵌套）时使用实际节点，其它旧rich等待和点击保持升父；正反回归均覆盖 |
| 根容器空属性 | 无控件身份的合成dump根容器跳过，scrollable-only和all首项布尔可定位真实控件；实际控件属性缺失仍报能力缺失 |
| 三键能力 | HMOS文档明确第三键不生效，backend.get_os_info确认OpenHarmony才调用一次三键；HarmonyOS/HMOS/未知身份均在组合动作前blocked，两键保持原路径 |
| has_app分类 | Shell传输非零/超时/错误转ConnectionError，ledger落infrastructure.transport_failure，不再internal.unexpected_exception |

验证命令：`python -m pytest tests/unit/test_common_device_operations.py tests/unit/test_selector_resolve.py tests/unit/test_selector_identity_redaction.py tests/unit/test_tier_a_steps.py tests/unit/test_agent_planned_gesture.py tests/unit/test_hylyre_agent.py tests/unit/test_pre_run_reject.py tests/schema/test_step_outcome_contract.py tests/schema/test_phase1_conformance.py tests/integration/test_common_entrypoint_parity.py -q -W ignore::DeprecationWarning --tb=short`。结果 **701 passed, 2 skipped**（23.44秒），日志 `.hylyre/verification/extend-common-device-operations/review-r1-targeted.log`。之后同一B4中补上all文本子项自身的布尔过滤，**154项**对应common/selector/tier_a检查通过。未重复全量回归、未执行真机。

`python -m compileall -q hylyre`、`openspec validate extend-common-device-operations --strict`、`git diff --check`通过。完整真机验收状态不由本次软件返修改写。

## Claude 二审直接回归返修

二审确认B1–B4及三项顺带修复通过，仅指出B4无条件关闭等待升父导致的直接回归。本次采用最小兼容修法：复用递归布尔约束检查，仅含checked/checkable/focused（含嵌套）的等待使用实际匹配节点；其他旧rich等待仍升父，匹配与property_observations使用同一模式。组件目标继续禁止升父。

补旧by_text+clickable:true、all:[by_text,by_type:ListItem]的wait_for与wait_gone；补三个新状态的顶层/嵌套实际节点行为，以及状态和clickable/type混用时不得拼接父子事实。对应common/selector/tier_a/agent/完整入口检查 **262 passed**（3.84秒），日志 `.hylyre/verification/extend-common-device-operations/review-r2-targeted.log`。使用说明、agent-loop和CHANGELOG已同步明确兼容边界。该轮执行目标回归，随后通过同一审查会话的最终定点复核。

## 代码检视与交付状态

2026-11-14。实施、返修与验收辅助开发实际委派给 gpt-6.1-sol，reasoning_effort=xhigh。三次代码检视均由 Claude Code CLI 调用 claude-opus-5-5，effort=high。会话 daf1a389-3417-410e-b259-09efbe163c93。首轮检查 tracked/untracked 实现，对照本地原生接口。后两轮定点检查既有问题及返修引入的直接回归。原始结论见 [首审](reviews/implementation-1.md)、[第一次返修复核](reviews/implementation-2.md)、[最终复核](reviews/implementation-3.md)。最终结论为代码检视通过，无阻断问题。

首阶段共 9 份只读真机报告通过 report verify。随后完成了交互矩阵、真机返修及复核；最终结果见上述真机验收记录。

## 真机反馈后的软件修复与诊断

- 真实get_component_property.checked被通用value脱敏变成字符串。已在StepResult序列化处仅为该操作的六项布尔属性、且真实value是bool的情况保留类型；文本、字符串布尔、其它操作和target.text继续原有脱敏。对应redaction/common/report/入口/schema检查 **579 passed, 2 skipped**，日志 `.hylyre/verification/extend-common-device-operations/device-boolean-serialization-targeted.log`。随后只补非字符串property的安全检查和对应redaction回归，未重跑全量；真机trace由验收会话定点重跑。
- 双指第二触点touchend在clientY多52CSS像素，MOVE正确。离线调用本机真实OHOSDriver.two_finger_swipe并截获PointerMatrix，有/无area各一次注入，两指起点准确，两指末点一致y1388（SDK分步整数取整相对请求1394少6像素），没有第二指额外偏移或独立release参数。证据 `.hylyre/verification/extend-common-device-operations/two-finger-native-matrix-diagnostic.json`。multi_finger_touch和无area多指gesture出现同一clientY释放偏移，R3 已采集 screen/page/viewport 遥测，全屏对照结果见真机验收记录。

## 真机 wait_gone 索引零匹配返修

真实复现：`interactive-r2/wait-gone.steps.json` 在切换checkBox为true后，`wait_gone {by_type:checkBox,index:0,checked:false}` 完整谓词零匹配，却因通用index范围检查变成selector.not_found，阻断后续真实presence断言。确认属于等待执行链缺陷；现有文档未规定index>0在零候选时必须报错。

最小修复复用resolver的可选allow_empty，仅等待开启：index仍先验证为非负整数，完整谓词零候选返回空；候选非空而显式index越界仍保持既有错误。动作/组件定位默认严格行为不变，不捕捉异常文本、不吞歧义或非法选择器。属性事实优先复用实际已选hits；空匹配时诊断身份候选不再把同一个index重套到去除状态约束的不同谓词上。

common/selector/tier_a/redaction/入口目标检查 **315 passed**（6.82秒），日志 `.hylyre/verification/extend-common-device-operations/device-wait-index-targeted.log`。覆盖原真机复现、其它合法index零候选、目标消失、非法bool/负数/字符串/小数index、非空越界、多匹配未消失、选中控件的实际属性证据及动作默认索引未放宽。真机由验收会话保留原index0步骤定点复跑；唯一控件fixture之后可去除冗余index。

双指R3补充遥测显示DOM/viewport本身未变化，pointerup与touchend的第二指client坐标都有相同偏移；ArkWeb的screen坐标亦不具备独立物理通道。当前证据只能确认宿主矩阵两指一致，尚不能区分设备端UP注入与ArkWeb事件转换；普通模式保留 partial_end_unverified；后续同页全屏通过全部端点核对，参见上方最终结果。

真机返修完成后，原始带 index=0 的三步用例在新会话中全部通过并经 report verify 校验；checked 查询在最终 trace 保留 JSON 布尔 false。[布尔值复核](reviews/device-boolean-r2.md) · [索引等待复核](reviews/device-index.md)。
