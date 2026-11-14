# 常用设备操作（计划、CLI、MCP、会话共用）

所有 JSON 也可放入 `hylyre run --steps-file steps.json` 的数组或 test-plan 的测试步骤列。原子 CLI 是 `hylyre run <根键转短横线> --json '<完整步骤>'`；MCP 是 `hylyre_run_<根键>`，参数 `payload` 是完整步骤对象。CLI 加 `--session session.json`，MCP 加 `session_id` 可复用连接。touch 沿用 `run tap` / `hylyre_run_tap`。嵌套输入均为 JSON，不传 Hypium 对象。

## 点击与编辑

```json
{"touch":{"by_id":"item","mode":"double"}}
{"touch":{"by_text":"item","mode":"long","press_time":3,"wait_time":0.1}}
```

省略 mode 是 normal；仅 long 接受正数 press_time，默认 2 秒，实际调用 long_click，点击后等待仍有效。normal/double 使用原生 touch。clear_text 必须定位输入控件并原生清空；move_cursor 使用当前焦点，不点击控件重置光标。input 原有行为不变。

## 可复制操作示例

以下示例的 id/坐标应换成当前页面实际目标。所有 root 名称对应 CLI 与 MCP 的同名操作。

```json
{"drag":{"start":{"by_id":"item"},"end":{"x":300,"y":500},"press_time":1.5}}
```

```json
{"slide":{"start":{"x":100,"y":200},"end":{"x":300,"y":500},"duration":0.3}}
```

```json
{"fling":{"direction":"UP","distance":50,"speed":"fast"}}
```

```json
{"pinch_in":{"area":{"by_id":"canvas"},"scale":0.4,"direction":"diagonal"}}
```

```json
{"pinch_out":{"area":{"by_id":"canvas"},"scale":1.6,"direction":"diagonal"}}
```

```json
{"two_finger_swipe":{"start1":{"x":100,"y":200},"end1":{"x":100,"y":400},"start2":{"x":200,"y":200},"end2":{"x":200,"y":400},"duration":0.5}}
```

```json
{"multi_finger_touch":{"points":[{"x":100,"y":200},{"x":200,"y":200}],"duration":0.1}}
```

```json
{"gesture":{"fingers":[{"points":[{"x":100,"y":200},{"x":200,"y":300},{"x":300,"y":200}]}],"speed":2000}}
```

```json
{"press_key":{"key":"ENTER","mode":"normal"}}
```

```json
{"press_combination_key":{"keys":["CTRL_LEFT","A"]}}
```

```json
{"get_component_property":{"target":{"by_id":"field"},"property":"text"}}
```

```json
{"shell":{"command":"printf 'hylyre\\n'","timeout":60}}
```

```json
{"clear_text":{"target":{"by_id":"field"}}}
```

```json
{"move_cursor":{"direction":"left","times":1}}
```

```json
{"set_checked":{"target":{"by_id":"checkbox"},"checked":true,"timeout":3}}
```

```json
{"current_app":{}}
```

```json
{"has_app":{"bundle":"com.example.app"}}
```

```json
{"recent_tasks":{}}
```

## 参数及版本限制

- 目标使用 `{x:整数,y:整数}` 屏幕绝对像素或既有富选择器（by_id/by_text/by_key/by_type/all、scope/within 等）。属性查询、清空和勾选设置须使用真实控件。多目标和区域在动作前从同一快照解析，目标缺失、歧义或越界会拒绝，先滚动请显式写 scroll_to。
- drag 默认 press_time=1.5 秒、drag_time=1 秒；speed 是正整数（最大 40000），不能同时显式给 drag_time。显式 press_time 要求设备 API >=20，无法确认能力则 blocked，不忽略参数。本机6.0.7.210的OHOS实现无法兑现小于1.5秒的按住时长，此时显式blocked；1.5默认与大于1.5秒可下传。slide 只有 duration，默认 0.3 秒，映射原生 slide_time；不接受 speed。
- fling direction 和已有 swipe 一样不区分大小写，适配为原生 UP/DOWN/LEFT/RIGHT；distance 是 1–100 的区域百分比，默认 50；speed 仅 fast/normal/slow，默认 fast，使用原生惯性抛滑。
- pinch_in.scale 在 (0,1)，默认 0.4；pinch_out.scale 在 (1,2)，默认 1.6。direction=diagonal/horizontal，默认 diagonal；dead_zone_ratio 若提供须在 (0,0.5)。area 必填。新增手势的area.by_text取实际匹配文本节点边界，不升父；旧swipe.area保留原定位语义。
- two_finger_swipe 默认 duration=0.5 秒；multi_finger_touch 默认 duration=0.1 秒，要求 2–4 个触点。area 是唯一控件区域，不改变屏幕端点原点；适配层传 Rect 并抵消原生的一次区域偏移，整数0/1仍为像素。
- gesture 至少一指，每指至少两个连续点，默认 speed=2000 像素/秒。每指创建一个 Gesture；一指一次 inject_gesture，多指一次 inject_multi_finger_gesture。Hypium 本机源码未声明通用轨迹的指数量上限，设备的明确不支持会报告能力缺失；不猜定上限，也不串行 slide 模拟。speed 为正整数，最大40000。
- press_key.key 是 Hypium KeyCode 的精确符号名（如 ENTER、BACK、CTRL_LEFT、A）或非负整数；mode=normal/long/double。组合键要求2–3个不同键，一次原生组合调用，不接受 mode。Hypium明确注明HMOS会忽略第三键，所以三键仅在已确认OpenHarmony后调用；HMOS或系统能力无法确认时blocked，不退化为两键。
- move_cursor.direction=left/right/up/down/begin/end，times 正整数默认1。方向在适配层转换为原生大小写。
- get_component_property 支持 id/text/key/type/enabled/focused/clickable/scrollable/checked/checkable，值位于 observation.facts.value；持久化结果保留归一化的布尔属性值，文本属性值及target.text继续脱敏。空文本和 false 是有效结果，缺属性或无法观测布尔值是能力缺失。
- 本机接口基线 Hypium 6.0.7.210，不因此无条件提高全部功能最低版本。缺方法或明确不支持报告 blocked/capability；真实执行错误不会伪装成能力缺失。

## 属性过滤及状态设置

```json
{"wait_for":{"by_id":"checkbox","checked":false,"timeout":3}}
{"wait_gone":{"by_id":"checkbox","checked":true,"timeout":3}}
{"set_checked":{"target":{"by_id":"checkbox"},"checked":true,"timeout":3}}
```

选择器增加 checked/checkable/focused，和已有 clickable/enabled/scrollable 共用三态读取。输入只接受 JSON 布尔；读取侧接受布尔和字符串 true/false，其它或缺失为不可观测。**兼容变化**：已有 clickable/enabled/scrollable 显式 false 现在会精确过滤；原先依赖 false 被忽略的调用应移除字段。字符串布尔输入应改成 JSON 布尔。

wait_for 要求完整谓词匹配；等待的index须为合法非负整数，在完整谓词零匹配时按presence/absence处理，有候选但index越界仍失败；动作/组件定位的索引规则不变。唯一控件不需要额外写index:0。wait_gone 只证明匹配目标不存在，目标整体消失也可通过，并不证明目标仍在且值为 false。需要后者用 wait_for checked=false。组件查询/清空/勾选始终使用文本实际匹配节点，不升到可点击祖先。wait_for/wait_gone 只有出现 checked/checkable/focused 状态约束（含all或关系锚点内嵌套）时，整条谓词在实际匹配节点求值；其它旧rich等待继续保留文本升父语义，例如 by_text+clickable:true 或 all:[by_text,by_type:ListItem]。状态约束与clickable/type混用时必须由同一个实际节点满足，不能把子节点状态与父节点类型合并；点击路径保留原升父语义。属性不可观测不会让 wait_gone 错误通过。合成dump根容器的空布尔占位不会作为真实控件参与布尔过滤，scrollable-only区域选择仍可定位真实滚动控件。实际可取得的属性值保留在断言 facts.property_observations。

set_checked 先读 checkable/checked，已满足则不点击并返回 changed=false；否则只点击一次再在 timeout（默认3秒）内复读。facts 含 before/after/changed。非 checkable 不盲目点击；复读未达到目标或点击后复读异常判动作失败，不重试点击；异常时保留performed=true、before、changed=true、after=null及错误事实，不增加独立业务断言覆盖。目标不可勾选、非输入控件清空或手势越界/区域边界无效属于contract.invalid_step，真实零候选仍为selector.not_found。

current_app 返回 bundle/ability；ability 不可得为 null 并说明，没有可观测 bundle 则 blocked。has_app 使用固定 bm dump -a 输出按行精确匹配，不把 bundle 拼进 shell；未安装是成功读取 installed=false。查询全部是 action，不提高断言覆盖率。

## Shell 与证据

shell.command 是明确请求在选定设备执行的原文，允许引号、管道、分号、中文和转义换行；timeout 默认60秒。宿主用 argv 启动 hdc，不经 PowerShell/cmd 解释。设备绑定当前已连接的 serial，无法确认目标会阻塞。

当前已验证 hdc 不透传远端退出码、设备 stderr 合并到 stdout，因此在独立子 shell 外追加每次调用唯一尾标记，剥离包装时保留原始输出及尾随换行。facts 返回 stdout、stderr=null、stderr_available=false、设备 exit_code、transport_exit_code、marker_found、timed_out、remote_status_unknown、transport_error。缺/坏标记与传输异常判失败，设备非零也判失败；超时回收宿主进程，远端状态未知，不重试。完整传输输出作为 log artifact 保留，超过65536字符的内联输出显式标记截断并给出原始产物位置。传输错误使用 infrastructure.transport_failure；设备非零使用 infrastructure.x_hylyre.device_command_failed；状态确认失败使用 infrastructure.x_hylyre.state_confirmation_failed，沿用协议的厂商命名扩展。

在 Markdown 计划表格中，管道写成 `\|`（标准 Markdown 转义），解析时还原为 `|`；步骤 JSON 内的中英文分号和转义换行不会分步。也可使用 JSON `\u007c`。例如测试步骤列：

```text
{"shell":{"command":"printf '中文;\\n' \| cat"}};{"back":{}}
```

设备操作只按当前任务授权执行；验收使用固定无副作用命令。离线 --use-fakes 只模拟动作并标明 fake，无设备观测的属性/应用查询、set_checked、Shell 及属性断言会 blocked/capability，不生成设备事实。
