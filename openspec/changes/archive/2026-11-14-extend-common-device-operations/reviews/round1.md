# Claude Code CLI 检视记录（执行记录，不属于实施要求）

CLI: 2.1.325

调用：`claude -p --model claude-opus-5-5 --effort high --output-format json --tools Read,Glob,Grep --permission-mode plan --strict-mcp-config`；提示词从 stdin 输入，未设置 fallback。

实际响应模型：claude-opus-5-5

Session: 6a5a30f0-eb18-4f3f-ade0-525b80025aed

## 结论：有 3 个阻断项，修完即可通过

这轮是只读检视：没有改任何文件，没有跑测试，没有碰设备。依据是四件套全文，加上对源码和本机 Hypium（`D:\Program Files\Python314\Lib\site-packages\hypium\action\device\uidriver.py`）的核对。

### 7 项修复核对

| # | 结论 | 依据 |
|---|---|---|
| 1 长按/双击映射 | **通过** | design.md:23/43、common-device-operations/spec.md:4、tasks.md:21 三处一致。本机签名 `long_click(target, press_time=2, offset)`（uidriver.py:1644）没有 `wait_time` 参数，design 已写明由适配层另行等待。现有适配固定传 `mode="normal"`（driver.py:415-421），改动点很清楚。 |
| 2 统一切分 | **基本通过，有 B1** | 两份切分逻辑确实逐字相同（plan_contract.py:75、runner.py:679），合并方向正确。`--steps-file` / `--steps` 本来就是 JSON 数组（steps_cmd.py:228-240），不受影响。但新规则会让自然语言步骤丢掉原来的切分，见 B1。 |
| 3 属性断言复用 wait_for/wait_gone | **通过，附 B2** | assert_component、eq/ne 已删干净，四件套里只剩"不新增"的否定表述。现状只判断 `is True`（selector_resolve.py:649-654），false 语义扩展有落点；字段登记处是 selector_contract.py:72-85 和 selector_resolve.py:20-40，tasks 2.7 已覆盖。 |
| 4 不新增 unit | **通过** | design.md:55 与 spec:11 一致。Hypium 的 drag/slide 在给了 area 时会把坐标当作相对 area 的位置（uidriver.py:429/648），design 已要求适配层换算，并避免重复偏移。 |
| 5 Shell | **通过** | design.md:79-82、spec:46、tasks 1.3/6.2 一致：每次调用唯一的退出码标记、标记缺失时 `exit_code=null`、拿不到独立 stderr 时 `stderr=null` 且 `stderr_available=false`、超时后远端状态记为未知。旧的 `hdc_cli.shell` 只返回剥空白后的 stdout（hdc_cli.py:152），旧行为得到保留。 |
| 6 set_checked | **通过** | design.md:49、spec:32、tasks 5.3 都写了自己实现的原因（要保留读前、读后事实和 `changed=false` 证据），读值走共享路径。 |
| 7 固定验收矩阵 | **基本通过，有 B3** | 一页一正一反、额外边界只限列出的几项、重叠可复用证据、不支持只能用 stub 验证不能当成功，都已写明。但 touch 这一行内部互相矛盾，见 B3。 |

既有结果链（design.md:63-71）、不伪造的 fake（design.md:69、scenario-runner/spec.md:17-22）、全部入口（design.md:19，以及 cli/mcp 两份 spec）、组合与连续手势语义（design.md:30-32/57）、非目标边界（design.md:12-13）都还在，没有发现回归。

### 阻断项

**B1｜切分规则会让自然语言步骤不再切分（直接回归）**
- 位置：design.md:84、specs/scenario-runner/spec.md:11、tasks.md:16
- 问题：规则写的是"只识别 JSON 字符串之外、**对象之间**的分号和换行"。但计划单元格里也可以是自然语言步骤：不是 JSON 的步骤会走 `agent.ai_action`，没配 VLM 时报 blocked（ledger.py:129-143），步骤也可能被反引号或 ``` 包住（step_text.py:8-26）。旧逻辑对任何文本都按 `;`、`；`、换行切分。按字面实现，`点击登录；输入密码` 不会再被拆开。另外，如果在对象外面也跟踪引号，`点击"确定";返回` 这种写法会吞掉后面的分隔符。
- 最小修复：改为"只有去掉反引号或围栏后以 `{` 开头的片段，才在花括号深度大于 0 时跟踪 JSON 字符串和转义状态；其余文本（包括自然语言）照旧按 `;`、`；`、换行切分"。三处同步修改。
- 验收：同一个函数对下面几种输入，预检和执行得到相同结果——
  - `点击A；点击B` → 2 步
  - `点击"确定";返回` → 2 步
  - `` `{"shell":{"command":"a;b"}}`；{"back":{}} `` → 2 步，且第一步的 command 完整保留
  - `{"input":{"text":"x；y\\n z"}}` → 1 步

**B2｜"布尔属性不接受字符串布尔值"和"共享读取、类型归一化"冲突**
- 位置：design.md:45（对照 design.md:47、tasks.md:17/36）
- 问题：这句话现在放在"属性读取"的上下文里。可 dump 树里的属性本来就是字符串 `"true"`/`"false"`（`_attr_bool`，selector_resolve.py:112-113）。如果读取侧也照这句拒绝字符串，checked/checkable/focused 过滤会永远报能力缺失，整项功能不可用。
- 最小修复：改成"**计划或选择器的输入值**必须是 JSON 布尔；**读取侧**把 dump 或原生返回的 `"true"`/`"false"` 归一为布尔，其它值或缺失视为不可观测"。
- 验收：
  - 单测：dump 节点 `checked="false"` 能被 `{"by_id":"x","checked":false}` 匹配
  - 计划里写 `checked:"false"` 在预检被拒绝
  - 节点缺少 checked 属性时报能力缺失，wait_gone 不能因此通过

**B3｜touch 行的真机正例自相矛盾**
- 位置：design.md:23 对照 design.md:106/108、tasks.md:53
- 问题：矩阵规定每个命名单元只有一条正例。touch 是一行，额外边界里只列了"长按自定义时长"。但 design.md:108 又要求"所有类型的能力成功都须有支持设备正例"，双击就落在两条规则之间：要么没有真机正例，要么超出"额外边界只保留"的列表。
- 最小修复：在 design.md:106/108 和 tasks.md:53 写明：touch 行的正例是 `mode=double`，长按由已列的"长按自定义时长"边界覆盖，normal 复用现有 tap 回归的证据，不再单独加行。
- 验收：矩阵清单里 touch 行正例是 double，边界行是 long + `press_time=3`，没有出现第三条 touch 真机用例。

### 可选建议（不阻断）
- 现有 clickable/enabled/scrollable 的显式 `false` 以前被静默忽略，改后会变成精确过滤。仓库里没找到这种写法，但建议在 Migration Plan 加一句行为变更说明。