# 0.6.0 收尾检视

Claude Code CLI --model claude-opus-5-5 --effort high
会话 60f8f52a-7d9c-47fa-a10d-c5c9718a0121

## 首轮

**结论：代码和版本部分都通过，没有阻断。只有验收记录 `software-verification.md` 里还留着 3 处"等待中/将要做"的过时说法，建议改掉再收尾。** 按要求只读了文件，没有执行命令，没有碰设备。

## 通过的部分

1. **0.6.0 版本入口**：`pyproject.toml:7` 和 `hylyre/__init__.py:3` 都是 0.6.0，`tests/unit/test_run_option_ownership.py:829` 有测试保证两者一致。包代码里没有残留的 0.5.x 版本号，README 第 71、73 行提到 0.5.x 是历史段落。
2. **README / CHANGELOG 兼容说明**：
   - `CHANGELOG.md:9` 写清了几项变化：显式 false 现在会精确过滤；字符串布尔要改成 JSON 布尔；合法 index 下零匹配会进入等待判断。
   - 同一处也写明协议、trace schema 和两种 manifest schema 都没变。
   - `README.md:9,69` 的说法和 `docs/common-device-operations.md:111` 一致。
3. **导入链没有循环，现有 API 没被破坏**：
   - `common_operation_contract` 是叶子模块：模块级只导入 `component_properties` 和 `exceptions`，`selector_resolve` 是在函数里延迟导入的。
   - `runner`、`plan_contract`、`planned_step_keys`、`step_dispatch` 对它都是单向依赖。`step_dispatch` 对 `plan_contract` 本来就是函数内延迟导入。
   - 测试、脚本和 `scenario/__init__` 用到的名字都还在，包括 `ScenarioRunner`、`resolved_outcome`、`_execute_one_step`、`_probe_toast_listener`、`_toast_capability_outcome`、`fake_step_outcome`、`FAKE_NAMESPACE`、`validate_*_contract`、`PRE_RUN_REJECT_CODES`，以及经 `plan_contract` 转出的 `iter_plan_steps`。
4. **离线观测策略只登记在一处，原有顺序和行为不变**：
   - 唯一的登记表是 `common_operation_contract.py:12` 的 `COMMON_OPERATION_REQUIRES_OBSERVATION`。只有 `runner.py:137` 读它，steps 路径（`steps_cmd.py:180`）也复用同一个 `fake_step_outcome`，没有第二份清单。
   - 标为 True 的正好 5 个：`get_component_property`、`shell`、`set_checked`、`current_app`、`has_app`。`recent_tasks` 在设计里是动作，不是查询，标 False 正确。
   - 不在表里的旧根键用 `.get(kind, False)` 取值，会走原来的分支，不会被误拦。
   - `PLANNED_STEP_ROOT_KEYS`、CLI 和 MCP 的列表，以及 `_DISPATCH_BY_ROOT`，都是在原有顺序后面追加，旧分发目标没变。
   - 测试覆盖了全部 18 个操作：`tests/unit/test_common_device_operations.py:367` 验证 5 个观测操作加 `wait_*` 返回 blocked，`:718` 验证另外 13 个仍模拟通过，`:709` 验证将来新登记的操作也按这张表处理。
5. **原始证据位置说得对**：`device-acceptance.md:7` 明确写了原始证据只留在本机、git 忽略该目录，`.gitignore:110` 也确实忽略了 `.hylyre/`。验收记录里引用的日志和 trace 路径都在 `.hylyre/` 下，没有哪里说它们在 git 里。`tasks.md` 没有未勾选的项。

## 需要修的（只是措辞，不影响代码）

`openspec/changes/extend-common-device-operations/software-verification.md` 里有 3 处过时的说法，和同一文件第 62 行"代码检视通过"、第 79 行"R3 已补遥测"相矛盾：
- **第 38 行**："等待同一检视会话复核，不将自行检查替代外部检视"
- **第 58 行**："未重跑全量、未操作真机，等待同一审查会话定点复核"
- **第 69 行**："验收脚本将增加screen/page/viewport遥测定性"

建议改成过去时，或者在后面注明"已由某轮复核或 R3 完成"。

## 留着就好、不用改的

- `interface-verification.md:64` 写着"当前支持设备三键正例仍属真机待验项"。这是如实说明：三键正例不在计划内的 21 项里，矩阵 `press_combination_key` 那一行测的是两键 CTRL+A，这不是过时状态。
- `reviews/implementation-1.md:61` 写着"各行目前都是 Pending"。这是首审的原始记录，`software-verification.md` 里也是作为"原始结论"链接过去的，保持原样即可。

## 文档返修定点复核

**结论：通过，没有阻断。** 只读了 `software-verification.md`，代码没有重审。

**上轮指出的三处时态都已改正：**
- **第 42 行**（原第 38 行）：改为"同一检视会话随后确认 B1–B4 均已修复，详见第二轮记录"。
- **第 62 行**（原第 58 行）：改为"该轮执行目标回归，随后通过同一审查会话的最终定点复核"。
- **第 73 行**（原第 69 行）：改为"R3 已采集 screen/page/viewport 遥测，全屏对照结果见真机验收记录"。

这三处现在和第 66 行"代码检视通过"、第 83 行"R3 补充遥测"都一致了。

**最新整批结果和历史 1383 已经分开写：**
- **第 5–7 行**是单独的"0.6.0 工作区最终整批回归"一节：1475 passed、2 skipped、2 deselected、0 failed，覆盖率 76.31%，日志 `0.6.0-final-regression.log`。这一节明确说"下文的 1383 是较早实现阶段的运行记录，保留用于追溯"。
- **第 26 行**把 1383 那一条改标为"真机返修前的整批命令"，日志文件也和最新那次不是同一个。

**可选的小措辞（不影响结论）：** 第 27 行"继续复用有效全量结果，不无依据重复整批"是写在 1383 那段历史里的，现在已被顶部的 1475 取代。想改的话，可以在前面加"当时"。
