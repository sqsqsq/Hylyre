## Context

状态：已完成计划内实施与验收。逐项结果与环境限制见 acceptance/device-acceptance.md。范围由用户确认的 Claude 高/中优先级加六项补充组成，以下阶段是交付顺序，不是削减承诺范围。

现有公共链为 planned_step_keys → 预检/dispatch → HylyreAgent → UiDriverBase/HypiumDriver → OperationOutcome → build_step_result → trace/report。CLI、MCP、session 必须复用这条链。touch 当前固定 normal；swipe 是方向型滑动；已有富选择器和滚动定位，不另造定位器。

接口依据：本机 Hypium 6.0.7.210 的 action/device/uidriver.py 及华为 Python API 文档。已确认 long_click、double_click、drag、slide、fling、pinch_in/out、inject_gesture、inject_multi_finger_gesture、press_key、get_component_property、clear_text、move_cursor、switch_component_status、current_app、has_app、swipe_to_recent_task。接口存在不等于目标设备支持，尤其 drag.press_time 文档要求设备 API level >= 20。

## Goals / Non-Goals

**Goals:** 完整覆盖下列操作；旧调用保持默认行为；原子/批量/会话结果一致；所有参数是 JSON 数据而非 Hypium 对象；结果和断言诚实可追溯。

**Non-Goals:** 亮灭屏/解锁专用操作、旋转、文件传输、卸载、录屏、图像模板匹配、鼠标全套、窗口管理、手写笔、触控板；不新增 VLM 依赖、测试脚本语言、变量插值系统或任意 Python 执行入口。交付按下述实现与真机验收范围执行。

## Decisions

### 1. 对外操作清单和输入输出

以下名称为本变更约定：JSON 根键使用下划线，CLI 为 `hylyre run <kebab-name>`，MCP 为 `hylyre_run_<snake_name>`。touch 继续使用已有 `run tap` / `hylyre_run_tap`，不新增 long-click/double-click 平行入口。所有新增步骤也可通过 run --steps-file、plan 和 hylyre_run_steps 调用。复杂嵌套输入使用统一 JSON 参数或步骤文件，不强行为每层节点增加 CLI flag。

| JSON 步骤 | 输入契约 | 结果与最小真机验收 |
|---|---|---|
| touch（扩展） | 原定位字段；mode=normal/long/double，默认 normal；仅 long 可给正数 press_time（秒），未给时使用 2 秒 | 普通点击不变；长按弹出菜单；双击触发目标行为；显式时长真实下传 |
| drag | start/end 目标；press_time、drag_time、speed 可选 | 拖动排序或对象移动；区分按住与移动；显式 speed 与 drag_time 同时给出拒绝 |
| slide | start/end 目标；可选 duration（秒），映射 slide_time，默认 0.3。传 speed 在预检拒绝 | 精确从 A 到 B，无长按语义；不能用分段 slide 冒充连续轨迹 |
| fling | direction 沿用 swipe，大小写不敏感，适配层传 UP / DOWN / LEFT / RIGHT。distance、area 可选。speed 为 fast / normal / slow，默认 fast | 调用原生 fling，并观察惯性滚动；不悄悄替换为 swipe |
| pinch_in / pinch_out | area、scale、direction；可选 dead_zone_ratio | 图片/地图缩小和放大；分别验证 scale (0,1) / (1,2)，dead_zone_ratio (0,0.5) |
| two_finger_swipe | start1/end1/start2/end2 目标、duration、可选 area 区域选择器，适配层取唯一控件边界并传入原生 Rect | 双指同时移动，与两次串行 swipe 区分 |
| multi_finger_touch | points 目标数组、duration、可选 area 区域选择器，适配层取唯一控件边界并传入原生 Rect | 多个触点同时按下；至少两点，数量上限按底层能力拒绝超限 |
| gesture | fingers 数组，每指含连续 points；speed | 适配层按每指点序构造一个 Gesture，一指调用 inject_gesture，多指调用 inject_multi_finger_gesture，整条轨迹一次注入，默认 speed=2000 |
| press_key | key（Hypium KeyCode 名称或整数）、mode 默认 normal | Enter/音量等实际产生作用；未知符号名预检拒绝，不猜键码 |
| press_combination_key | keys 数组，2–3 个键 | 一次组合按下，不能退化为顺序单键；组合键不接受单键 mode |
| get_component_property | target、property | 返回原类型的 value；属性缺失不得假装为空文本或 false |
| shell | command 非空字符串、timeout 正数，默认 60 秒 | 返回 stdout、stderr、设备 exit_code、transport_exit_code；失败和超时分类清楚 |
| clear_text | target（输入控件） | 原生清空，复读文本确认测试场景为空；不以输入空字符串替代 |
| move_cursor | direction=left/right/up/down/begin/end，times 正整数默认 1 | 使用当前已聚焦输入框；移动后插入文本验证位置，不自动点击造成光标重置 |
| wait_for / wait_gone（扩展） | 既有选择器增加 checked/checkable/focused 布尔过滤；复用既有 timeout | 按属性匹配目标的出现/消失断言，不新增断言步骤 |
| set_checked | target、checked 布尔值、timeout 默认 3 秒 | 读取当前值；已满足则不点击；否则设定并复读验证；重复执行不反向切换 |
| current_app | 空对象 | 返回 bundle 与 ability（不可得时为 null 并说明），用真实前台 App 核对 |
| has_app | bundle 非空字符串 | 返回 installed 布尔值；未安装是成功读取 false，不是执行失败 |
| recent_tasks | 空对象 | 调用 swipe_to_recent_task，实际进入最近任务页 |

长按和双击原生映射固定为：normal 调用 touch(mode="normal")；long 调用 long_click(target, press_time=用户值或2)，不得调用没有时长参数的 touch(mode="long")；double 调用 touch(mode="double")。富选择器先解析为坐标，再使用同一映射。long_click 没有 wait_time 参数，已有点击后 wait_time 在适配层另行等待，不得静默丢弃。

属性读取首批固定支持 id、text、key、type、enabled、focused、clickable、scrollable、checked、checkable，计划或选择器的布尔输入必须是 JSON 布尔，不接受字符串布尔值；读取侧将 dump 或原生返回的布尔及字符串 "true"/"false" 归一为布尔，其它值或缺失视为不可观测。保留 get_component_property 查询；不新增 assert_component 或 eq/ne。属性断言复用 wait_for / wait_gone：扩展选择器 checked/checkable/focused，连同已有 clickable/enabled/scrollable 统一明确 true 和 false 的过滤语义，不把 false 当成未传。文本与身份匹配继续使用既有 by_text/by_id/by_key/by_type/all。

get_component_property、选择器属性过滤和 set_checked 共用三态布尔读取（true、false、不可观测）。现有 _attr_bool 会把缺失值折叠为 false，仅保留在点击排序、祖先查找等既有二态调用中；未知或缺失值不得默认 false。底层无法观测请求属性时明确能力缺失，不能把它当作目标不匹配使 wait_gone 错误通过。wait_for 要求完整谓词匹配的目标存在；wait_gone 只证明不存在匹配目标，可能是目标消失，不等同于“目标仍存在且值变为 false”。需要后者用 wait_for {by_id:"x",checked:false}。

set_checked 自行采用“读当前值、必要时点击一次、复读确认”，不直接使用 switch_component_status；原因是需要保留读前/读后事实和 changed=false 的无操作证据。读取走上述共享路径，保持状态幂等，不引入新断言链。

### 2. 定位、坐标与参数规则

- target/start/end 复用现有富选择器（by_id/by_text/by_key/by_type/all、scope/within 等）；找不到、歧义、类型不适用均按现有错误分类，禁止回退第一个控件。
- 点击/拖拽/slide 允许坐标或选择器；属性读取、清空、状态设置必须定位真实控件。富选择器已解出的节点须通过现有身份/边界信息对应原生控件，不能把坐标当作可读取属性的控件；无法唯一对应时明确失败。
- 新手势端点统一为 `{x:100,y:200}` 或富选择器，沿用 touch.x/y 的屏幕绝对整数像素语义；不新增 unit 或比例坐标。原有 swipe.start_point 保持兼容，不在本次改变其行为。新操作中的 area 仅约束操作区域，不把端点变为区域相对坐标；原生接口若以 area 为原点，适配层转换且避免重复偏移。gesture 的 points 也允许这种目标形态，所有 selector 在注入前解出屏幕中心。统一比例坐标另开变更。
- area 复用现有区域选择器；手势执行前一次性解析区域及全部目标，验证边界后才触碰设备，不在轨迹中间滚动找目标。需要滚动的前置动作显式写 scroll_to。
- gesture 每指至少两个点，至少一指；触点上限依底层实现验证。复杂手势整体一次注入，异常不自动重复。
- 预检拒绝非法枚举、NaN/Infinity、非法时长/距离/缩放、互斥参数、缺失终点和未知属性；验证逻辑共用，不在 CLI/MCP 各复制一套。
- 新操作的可选参数未提供时采用已核对的 Hypium 默认值并写入帮助；不会盲目把 null 传给不接受它的原生参数。所有显式参数必须执行或明确报不支持，不能忽略。

### 3. 结果和能力兼容

沿用 OperationOutcome、StepResult、builder/reducer、已有失败分类与协议版本。查询按 action 角色记录“读取已执行”，值位于 observation.facts；不新增 query 角色。属性断言继续使用 wait_for/wait_gone 的 presence/absence 角色与证据链，保留属性谓词及可取得的实际观测值；读取成功不能变成 assertion matched=true。

set_checked 是动作，其成功条件包含复读达到目标；已满足时记录 changed=false，禁止伪造一次点击。它不因此替代用例的独立业务断言。多目标操作的目标/区域证据使用现有可扩展事实字段，不新增第二套 selector schema。

缺少底层方法或明确的设备不支持返回 blocked/capability；真实操作异常、定位失败、断言不匹配按既有规则分类，不把所有异常都包装为 capability。保留失败边界截图/诊断。不同 API 级别不能静默忽略自定义 press_time。为新 UiDriverBase 能力提供默认“不支持”实现，避免既有第三方子类因新增 abstractmethod 无法实例化。

离线 --use-fakes 复用既有模拟动作政策并标明模拟；没有观测来源的属性/应用查询、属性断言、依赖真实状态的 set_checked 与 Shell 返回 blocked/capability，绝不伪造业务值。单元测试可注入可控 stub 验证成功/失败分支，这不等于离线真机结论。

仅在现有 schema 实际限制了新增 kind/事实时更新对应声明、golden 和兼容测试；不为了扩展能力升级整个结果协议或创造新 manifest。

### 4. Shell 的边界与解析

command 是明确请求在选定设备执行的 shell 文本，允许管道、引号、分号、中文和换行；宿主端必须用参数数组启动 hdc，禁止交给 Windows PowerShell/cmd 再解释。设备选择沿用现有 session/device-sn 规则，不能落到别台设备。

现有 hdc_cli.shell 仅返回剥除空白后的 stdout，应在同模块补结构化路径并保持旧调用行为。第 1 阶段探针后按固定规则实现：

- 设备退出码：hdc 可靠透传则直接使用；否则设备端用独立子 shell 执行原 command，外层紧接着输出每次调用唯一的退出码标记（形如 __HYLYRE_RC_<nonce>=数值），避免 command 中 exit 终止外层。解析尾部标记并仅剥离包装附加部分，保留原输出和尾随换行；原始传输输出存为现有证据产物。标记缺失/格式错误是执行或传输失败，exit_code=null，不能猜为 0。
- stderr：有可验证独立设备通道则 stderr_available=true 并返回文本；没有则 stderr_available=false、stderr=null，合并内容保留在 stdout，不能把 hdc 自己的 stderr 当作设备 stderr。独立 stderr 不可用不阻断验收，按真实能力标记即合格。
- transport_exit_code 与设备 exit_code 分开记录；非零设备码判失败并保留输出，传输失败优先报告传输错误，无法获得设备码时为 null。
- timeout：回收宿主子进程，记录远端进程是否仍运行未知，不自动重试。输出过大时复用现有 artifact，截断必须显式标记并指向完整产物。

计划文本切分是公共契约的现存缺陷，必须在第 2 阶段修复：plan_contract.py 与 runner.py 的两份 replace 分号逻辑合并到同一切分函数，预检和执行均调用。去除既有反引号/代码围栏包装后，仅以 `{` 开始的片段进入 JSON 扫描，在对象深度大于 0 时跟踪字符串和转义；对象内部不切分，字符串内部转义换行、引号、分号和中文原样保留，格式化 JSON 换行不拆步。对象之外和自然语言片段按旧行为用英文/中文分号及换行切分，自然语言中的引号不启动 JSON 字符串状态。非法原始 JSON 字符串换行仍按 JSON 错误拒绝。验收样例：`点击A；点击B` 与 `点击"确定";返回` 各两步；带反引号的 shell JSON（command 为 a;b）后接分号与 back JSON 为两步；input JSON 内含中文分号和转义换行为一步；预检与执行得到同样结果。Shell 阶段只复用，不再独立实现切分。

本功能不新增交互确认、任意命令白名单或权限状态系统；执行者仍只运行任务明确授权的命令。验收只用无副作用命令与测试 App，不执行清设备、改系统配置或读取秘密。

### 5. 依赖与实施阶段

1. 接口核对：实际签名、设备能力、Shell 探针，按第 4 节固定规则选择适配路径。
2. 公共契约：注册/预检/结果接线、统一步骤切分、共享属性读取及选择器属性过滤扩展。
3. 点击、基础手势和编辑：touch、drag、slide、按键、clear_text、move_cursor，落实原生映射和既有坐标语义。
4. 缩放、多指和连续轨迹：fling、pinch、双指、多点及轨迹。
5. 属性、状态和应用：get_component_property、set_checked、current_app、has_app、recent_tasks；不新增断言步骤。
6. Shell：结构化执行、退出码包装、stderr 可用标记和超时/失败路径。
7. 集成验收：每项入口、兼容测试、固定真机矩阵、文档及交付记录。每阶段都沿公共链纵向交付。

### 6. 验收标准

**静态与单元：** 表中每种操作至少有参数合法/非法、原生调用映射及结果形态测试；touch 三种 mode 覆盖原生与富选择器转坐标路径；多目标缺一、歧义、越界均在触碰前拒绝。类型检查使用项目已有门禁；若尚无类型检查配置，记录现状并采用可运行的目标检查，不引入整仓类型整治。

**入口与兼容：** 对清单全部根键参数化检查计划/steps/原子 CLI/MCP/session 注册和传递，代表操作覆盖成功/失败/blocked/超时；验证无 session 与复用 session 的事实一致。无 mode 的旧 tap、旧 input/swipe/back/home、旧报告样本继续通过。run --steps-file 与 plan 的 Shell 引号、分号、中文、转义换行完整保留。

**结果可信：** 查询 false/空字符串与操作失败可区分；属性真实不匹配生成失败断言；无设备 fake 不制造属性和应用值；报告/trace 经 report verify 通过，验证覆盖率不因查询动作增加而虚增。

**固定验收矩阵与上限：** 以操作表每个命名单元为固定行（pinch_in/out、wait_for/wait_gone 各独立一行），实施前为每行指定一个固定测试页面/设备上下文（查询与 Shell 可共用），一条正例和一条反例。正例须在支持设备执行；非法参数及能力缺失反例用 stub/单测，无需反复真机复现。touch 行正例固定 mode=double；long 由下面自定义 press_time=3 的边界用例覆盖；normal 复用已有 tap 回归证据，不新增第三条 touch 真机用例。该矩阵不做“每入口 × 每设备 × 每属性”的笛卡尔积。

额外边界只保留：长按自定义时长；pinch 两个方向；双指滑动、多点点击、单指连续轨迹、多指连续轨迹各形态；set_checked 已满足/切换成功/不可勾选/复读失败；has_app 已安装/未安装；Shell 正常输出/设备非零/传输错误/超时/特殊字符五类。边界与基础行重叠时复用证据，不重复执行；设备能力缺失、传输错误及难稳定复现的复读失败可注入 stub 验证。所有类型的能力成功仍须有支持设备正例，不能以“不支持”冒充成功。新发现真实缺陷只增加对应回归，不重新扩大整套验收矩阵。

验收记录统一包含 Hypium、hdc、设备系统、API 级别、固定页面/上下文、测试命令、结果和产物路径。stderr 不可独立获取时如实标记即合格。

**交付：** 完整交付要求全部范围已实现、目标检查通过、一次整批回归通过、上述真机矩阵有结论、使用文档与命令帮助一致。缺设备/应用条件时标记“代码验证完成、真机验收未完成”并列缺项，不宣称全部完成。记录 Hypium/hdc/设备系统/API 版本、测试命令、结果和产物路径，不新增独立证据管理系统。

## Risks / Trade-offs

- 设备 API/SDK 不同 → 按能力报不支持，保留原参数语义；真机矩阵注明环境。
- 手势可执行但目标 App 无可观察变化 → 用具有确定反馈的测试页面验证，不仅检查没有抛异常。
- 富选择器节点与原生控件身份不一致 → 复用既有解析链并校验唯一性，禁止重新宽泛查找。
- Shell 输出可能包含敏感业务数据 → 沿用现有日志/脱敏机制，验收只输出固定测试文本；不自行采集业务秘密。
- 状态设置期间页面变化 → 有界复读，失败保留事实，不无限重试或盲目二次点击。

## Migration Plan

旧计划的默认行为保持兼容；例外是 clickable/enabled/scrollable 显式 false 从原先被忽略修正为精确过滤，依赖旧忽略行为的调用应移除该字段，须在变更说明列出；布尔过滤输入统一拒绝字符串布尔，曾依赖其被忽略的调用应移除字段，需要过滤的调用应改为 JSON 布尔。更新命令帮助、agent-plan-a、agent-loop、必要的消费方契约示例及变更说明；不在本任务自动发布或打包。回滚代码时新步骤不再支持，旧步骤继续按旧契约运行，测试应用中的状态由验收前后恢复，不进行用户数据迁移。

## Open Questions

范围没有待定项。实施前需记录两项环境事实：目标设备/API 与可用测试 App；当前 hdc 对远端退出码及 stderr 的支持（依第 4 节既定规则适配，不再作为设计悬项）。两者不阻碍本计划完成，但缺少时不能完成对应真机验收。若真实接口无法实现已承诺语义，应报告具体缺口，不能静默删项或降级。
