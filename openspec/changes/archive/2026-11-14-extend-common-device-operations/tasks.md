## 1. 实施前接口核对

- [x] 1.1 核对 Hypium 6.0.7.210 与目标环境版本，记录本次全部原语签名、默认值、KeyCode 名称和设备 API 限制；不静默缩减 design 操作表。
- [x] 1.2 核对 Gesture 构造、多指数量限制、fling 参数、属性读取类型、富选择器到原生组件的身份映射；记录可直接复用的现有代码位置。
- [x] 1.3 用无副作用探针确认目标 hdc 的 stdout/stderr/远端退出码/超时行为，按 design 固定规则确定退出码直取/唯一标记包装、stderr_available 和超时未知状态。
- [x] 1.4 确认支持设备、测试 App 页面和各操作可观察反馈；为全部真机验收项列出环境与预期结果，缺条件如实记录。

## 2. 公共契约和执行接线

- [x] 2.1 扩展 api/planned_step_keys、step_dispatch、scenario/plan_contract 的操作注册、角色与共享参数验证，补非法参数不触碰设备的测试。
- [x] 2.2 在 UiDriverBase 增加默认不支持的新能力接口，保持旧子类可实例化；更新 Hypium 适配及 fake/stub 的对应表面。
- [x] 2.3 复用 selector_resolve/selector_ops 实现新目标、区域和多端点解析；对 two_finger_swipe 和 multi_finger_touch 将唯一 area 目标的边界转为 Hypium Rect，验证屏幕端点没有重复偏移。补唯一性、缺失、边界、既有屏幕像素坐标适配及先验证后执行测试。
- [x] 2.4 接入公共 OperationOutcome/build_step_result，明确查询事实、属性断言和多目标证据字段；只更新确实受影响的 schema、code 注册和 golden。
- [x] 2.5 为新增操作接入 session/daemon 的序列化分派与目标设备选择，补 JSON 参数和无/有会话一致性测试。

- [x] 2.6 合并 plan_contract.py 与 runner.py 的步骤切分到一个函数，预检/执行共用；覆盖 input 与 shell 的中英文分号、转义换行、引号、中文、格式化 JSON、反引号/围栏及自然语言旧分隔兼容（含自然语言引号）。
- [x] 2.7 扩展选择器 checked/checkable/focused，使用共享三态读取（true/false/不可观测），过滤和查询不得直接复用缺失返回 false 的 _attr_bool，点击排序和祖先查找仍用原函数；贯通过滤字段注册、请求证据、节点转换和全部定位入口，明确输入仅接受 JSON 布尔、读取侧归一化字符串 true/false，及已有布尔过滤的 false 语义，覆盖缺属性不误判 wait_gone 通过。

## 3. 点击、基础手势和编辑

- [x] 3.1 扩展 touch：normal/double 映射 touch(mode)，long 映射 long_click(press_time=用户值或2)，保留点击后 wait_time；更新原生 selector、富选择器转坐标、坐标及 action 点击路径，补旧默认行为测试。
- [x] 3.2 实现 drag/slide，支持坐标及控件起终点、drag 的时长/速度约束和设备不支持分类。slide 仅将 duration 映射到 slide_time（默认 0.3 秒），预检拒绝 speed；补调用参数和失败分支测试。
- [x] 3.3 实现 press_key/press_combination_key，转换符号名/整数键码并拒绝非法组合，验证组合键为单次原生操作。
- [x] 3.4 实现 clear_text/move_cursor，验证原生清空与当前光标移动，不改变已有 input 契约。
- [x] 3.5 为本阶段操作补 CLI 原子命令、MCP 工具、plan/steps 和 session 路由，参数化验证每个入口均可达。

## 4. 缩放、多指与连续轨迹

- [x] 4.1 实现原生 fling 与 pinch_in/pinch_out，验证 fling.speed 仅接受 fast/normal/slow 字符串且默认 fast，覆盖区域、缩放、方向及非法边界。
- [x] 4.2 实现 two_finger_swipe/multi_finger_touch，覆盖同时执行、时长、触点数量及区域坐标。
- [x] 4.3 实现 gesture 的单指折线和多指轨迹，在适配层逐指构造 Gesture，验证单指一次 inject_gesture、多指一次 inject_multi_finger_gesture，以及点序、连续接触、完整注入与不支持结果，不用串行 slide 替代。
- [x] 4.4 为本阶段补 CLI JSON 输入、MCP、plan/steps/session 接线及序列化测试，确保不泄露 Hypium 对象。

## 5. 属性、状态与应用

- [x] 5.1 实现共享十项控件属性读取和 get_component_property，保留真实类型，明确缺失属性与空值差别。
- [x] 5.2 用已有 wait_for/wait_gone 验证扩展属性过滤，覆盖 true/false、匹配/不匹配、目标消失及属性不可观测；不新增 assert_component 或 eq/ne。
- [x] 5.3 实现 set_checked 的共享读前状态、按需点击一次、共享读后确认（不直接调用无法提供前后证据的 switch_component_status），覆盖已满足不点击、不可勾选和确认失败。
- [x] 5.4 实现 current_app/has_app/recent_tasks，保证未安装是查询 false，ability 不可得时显式说明。
- [x] 5.5 为本阶段补全部入口与 fake 行为，验证查询不提高断言覆盖率，复用同一属性真源。

## 6. Shell

- [x] 6.1 在现有 hdc_cli 模块补结构化 Shell 执行，保持旧 shell/force_stop 调用兼容，设备端原文与宿主参数边界清晰。
- [x] 6.2 实现设备退出码直取或唯一尾标记包装；独立 stderr 不可得时 stderr_available=false、stderr=null；保留原始证据，处理非零/缺标记/超时/宿主进程回收与远端状态未知。
- [x] 6.3 接入 CLI/MCP/plan/steps/session，测试固定文本成功、远端非零、传输错误、超时及特殊字符；不运行破坏性命令。

## 7. 集成验证和使用文档

- [x] 7.1 对 design 操作表全部根键执行入口覆盖测试，核对命令帮助、JSON 默认值与异常处理一致。
- [x] 7.2 跑项目现有类型门禁及受影响的 driver、agent、selector、tier_a、pre_run、session、CLI/MCP、schema/report 测试；若无类型门禁如实记录，避免扩成整仓整治。
- [x] 7.3 执行一次整批回归和新旧报告兼容验证；后续窄返修仅重跑受影响检查，无新增风险不重复全测。
- [x] 7.4 完成 design 固定矩阵：每命名单元一个页面/上下文、一正一反；touch 正例 double，long 用 press_time=3 边界覆盖，normal 复用 tap 回归，不增加第三条真机用例；仅增加明列边界；重叠用例复用证据，能力缺失用 stub；记录 Hypium/hdc/系统/API 版本，stderr 不可独立获取不阻断验收。
- [x] 7.5 对生成 trace/report 执行 report verify，确认模拟/blocked/查询与真实断言没有混淆；缺条件的真机项保持未完成。
- [x] 7.6 更新 docs/agent-plan-a.md、docs/agent-loop.md、必要的契约示例、工具说明和变更说明，提供本批每类操作的可复制 JSON 示例及版本限制。
- [x] 7.7 形成最终验收记录，对照范围逐项确认实现、入口、测试、真机状态；完整通过才标记交付完成，不自动提交、打包、发布或归档。
