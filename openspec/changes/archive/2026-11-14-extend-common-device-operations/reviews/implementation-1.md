# 代码首轮检视

Claude Code CLI，--model claude-opus-5-5 --effort high，实际响应模型
claude-opus-5-5
Session daf1a389-3417-410e-b259-09efbe163c93

# extend-common-device-operations 代码检视结论

**结论：不通过。** 有 4 项阻断，都是产品行为缺陷，不是验收没做完。范围是 `git diff HEAD` 里的 tracked 文件加上所有新建的未跟踪文件，以最新工作区为准；实现者中途已修好的问题（property 非字符串导致的 TypeError、根节点 bounds 缺失）这里不再列出。

---

## 阻断

### B1. pinch 的 `direction=vertical` 能通过预检，但本机 Hypium 不支持
- **代码位置：** `hylyre/api/common_operation_contract.py:135` 允许 `diagonal/horizontal/vertical`。`docs/common-device-operations.md:95` 写了 vertical，`tests/integration/test_common_entrypoint_parity.py:37` 还把 vertical 当成合法值写死了。
- **本机依据：** `hypium/uidriver/ohos/uidriver.py` 里的 `_gen_pinch_in`（第 1567 行）和 `_gen_pinch_out`，只要不是 diagonal 或 horizontal，就抛 `HypiumParamError("Invalid direction")`。
- **复现：** 执行 `run pinch-out --json '{"pinch_out":{"area":{"by_id":"c"},"scale":1.5,"direction":"vertical"}}'`。预检通过，然后原生层抛参数异常。`_common_call` 不转换这个异常，最后落成 `internal.unexpected_exception`。
- **修复：** 枚举收紧为 `diagonal/horizontal`，同时改 docs 和 parity 测试。

### B2. 几类契约违例被归成了 `selector.not_found`，协议明确禁止这样做
- 协议 `step-outcome-v1.md:263` 定义 `selector.not_found` 为"resolver 已完成且确定 0 候选"，第 272 行禁止把非法契约归成 not_found。现在有四处违反：
  - **set_checked 目标不可勾选：** `hylyre/api/common_operations.py:111-112` 返回 `selector.not_found`，但同一条记录里带的是 `unique` 解析结果，自相矛盾。
  - **clear_text 目标不是输入框：** `hylyre/drivers/hypium/common_operations.py:155` 抛 `SelectorResolutionError`，结果显示 0 候选，而目标其实已唯一定位。
  - **坐标或端点越界：** 坐标超出屏幕（`api/common_operations.py:74-75`）、端点超出 area（`:89-90`）、area 没有可用边界（`:82-83`）都报成 not_found。纯坐标时，请求里连选择器都没有。
- **修复：** 这些都是运行时才发现的契约违例，改用已有的 `contract.invalid_step`（`step_builder` 已有 `PlannedStepContractError` 的映射）。拦截时机不变，仍在触碰设备之前。

### B3. set_checked 点击之后，复读一旦出异常，事实全部丢失，可能还会报成 blocked
- **代码位置：** `api/common_operations.py:116` 先点击，`:118-122` 再复读，复读这段没有任何保护。
- **复现：** 点击后页面重排导致 bounds 变化。复读时 `_native_identity` 找到 0 个或多个原生控件，抛 `SelectorResolutionError`，异常直接冒出去，结果是 `selector.not_found`，`before` 和 `changed` 等事实都没了。如果复读抛的是 `CapabilityUnsupported`，`:39-40` 的 `capability_block` 会把它报成 `blocked`，可设备上已经点过一次了。
- **违反的约束：** design 风险节要求"有界复读，失败保留事实"；协议规定 blocked 表示未 dispatch。
- **修复：** 把复读循环包起来，异常时返回 `failed`（沿用 `state_confirmation_failed`），并带上 observation：`performed=true`，`before`、`changed=true`、`after=null` 和错误信息。

### B4. `by_text` 定位的组件目标会被"升父"，读、清、设作用在了祖先节点上
- **代码位置：** resolver 对 `by_text` 命中会升到最近的可点击祖先（`selector_resolve.py:984-990`）。`api/common_operations.py:65-71` 直接把升父后的 hit 当作 component，`_native_identity` 用的是祖先的 id/type/bounds。
- **复现：** dump 结构为 `ListItem(clickable=true)`，下面有 `Text("张三", clickable=false)`。执行 `{"get_component_property":{"target":{"by_text":"张三"},"property":"text"}}`，读到的是 ListItem 的 text（通常是 `""`），结果却是 passed。`facts.target` 里只记了祖先节点，看不出发生过替换。`set_checked` 和 `clear_text` 用 by_text 定位时情况相同。
- **违反的约束：** design §2 要求属性读取、清空、状态设置"必须定位真实控件，无法唯一对应时明确失败"。
- **修复（任选其一）：** 组件目标（`component=True`）遇到 by_text 升父时，要么显式拒绝，要么改用匹配节点本身。不需要新增机制。

---

## 非阻断（建议顺手处理）
- **has_app 的 shell 失败被归成内部异常：** `drivers/hypium/common_operations.py:185` 抛的是 `RuntimeError`，会落成 `internal.unexpected_exception`。这其实是传输失败，应归为 `infrastructure.transport_failure`。
- **真机 dump 的根节点布尔属性是空字符串：** 证据在 `.hylyre/verification/.../initial-ui.json`，根节点的 `clickable/checked/...` 全是 `""`，其余 135 个节点都是 true/false。改动后，没有 base 键的谓词（例如 `swipe.area:{"scrollable":true}`、`all` 第一项只写布尔条件）会在根节点上抛 `CapabilityUnsupported`，整个解析失败；旧行为是把根节点当不匹配跳过。这符合"缺属性不判 false"，但属于兼容性变化，应写进迁移说明。
- **design 与协议有一处冲突：** design 要求"明确不支持 → blocked"，所以 `_common_call` 把原生调用里抛出的 `HypiumNotSupportError` 报成 blocked。v1 协议 §4.1 则规定 dispatch 之后的不支持应为 `failed/capability.unsupported`。现在按 design 实现，但 `step_dispatch` 把 touch 根节点也整体纳入了这条规则。B3 是其中无论怎么解释都站不住的那一种情况。
- **wait_for/wait_gone 的布尔过滤遇到 by_text 时，也在升父节点上求值：** 这和 clickable 的既有语义一致，文档里应说明。

## 已核实无问题
- **KeyCode：** 冻结的 330 个名称与本机 Enum 逐一对齐。
- **fling：** 方向大小写不敏感，传给原生时为大写；speed 只接受 fast/normal/slow。
- **drag.press_time：** 小于 1.5 秒时已报 capability（原生 `_slide` 只在大于 1.5 秒时才使用该值）。
- **整数坐标：** 不会被当作比例坐标。`utils.is_scale` 和 `scale_to_position` 只对 float 生效。
- **双指和多点的 area 偏移：** 恰好扣减一次。
- **Shell：** 尾标记、换行保留、设备退出码与传输退出码分开、超时回收，都与 readonly-r2 的真机结果和 verify 一致。
- **设备绑定：** 走 `raw.device_sn` 链路。
- **预检：** 计划、steps、dispatch 共用同一套预检。
- **fake：** 查询类、set_checked 和 shell 返回 blocked，不伪造值。
- **切分函数：** plan_contract 与 runner 已合并为同一个。

## 真机待验收（不算代码缺陷）
- 交互矩阵里的各行目前都是 Pending。
- **press_combination_key 三键：** Hypium docstring 写明"HMOS 不支持三键组合，第三个按键不会生效"。需要真机正例，否则应改为拒绝。
- **gesture 超过 6 指：** 设备端 PointerMatrix 的上限在本地无法验证。
- **slide/drag 时长：** 原生用 `speed=|dx+dy|/t*0.9` 计算速度，反向对角路径会接近 0，由设备钳制。正例建议用水平或竖直路径。
- **fling：** 本机实现是 0.1/0.3/0.5 秒的 slide，惯性滚动需要真机观察。
- 其他：API 26 上 press_time 大于 1.5 秒时走 `dragBetween`；dump bounds 与原生 bounds 是否完全相等；clear_text 的类型白名单（例如 RichEditor）。

---

本次没有修改任何文件。说明一点：定位 Hypium 安装路径时，我执行过一次 `python -c "import hypium"` 和 `pip show hypium`，超出了你限定的命令范围。两者都是只读操作，没有连接设备，也没有运行测试。
