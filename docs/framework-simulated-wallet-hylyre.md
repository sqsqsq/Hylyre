# SimulatedWalletForHmos · Skill 6（device-testing）与 Hylyre 集成

面向 **Skill 6 — 执行测试** 阶段：在真机上逐步驱动 HarmonyOS App 时，用 Hylyre 替代「每条命令 full reconnect」与「半屏列表只靠单次 dump」两类痛点。

## 性能：`session start` + `--session`

Hypium 原子 CLI 默认每条命令完整 **connect/disconnect**，耗时常被 **10s+** 的连接开销主导。

**推荐编排**（shell / CI / framework 子进程）：

1. 测试段落开始前执行一次：  
   `hylyre session start --device-sn <SN> [--mock-port …]`  
   记下打印的会话 JSON 路径（默认 `./.hylyre/session.json`）。
2. Skill 6 中 **所有** `hylyre dump-ui`、`hylyre screenshot`、`hylyre run tap|swipe|scroll|…`、`hylyre collect-list` 追加同一参数：  
   `--session <该路径>`（或 `-S`）。
3. 段落结束：`hylyre session stop`。

> **注意**：会话进程内的 mock/Lyrebird 配置在 **`session start`** 时固定；若中途换端口，应 **stop → start**。

若在 **Cursor MCP** 且已配置 Hylyre MCP：可直接 **`hylyre_open_session`**，后续工具传 **`session_id`** —— 与 CLI session **文件不互通**，二选一即可。

## 准确性：`collect-list` 枚举虚拟列表

半屏 Sheet / 交通卡列表等场景，`dump-ui` 往往只看到 **视口内** 节点。若 AC 要求「列出全部卡片 / 计数完整」：

- 优先 **`hylyre collect-list --session …`**（或 MCP **`hylyre_collect_list`**：传 **`session_id`**（与 `open_session` 一致）、或 **`session_path`**（CLI 会话文件）、或 **`device_sn`** 一次性连接）。
- 可选 **`--scroll-by-id`** / **`--scroll-by-key`** 指向唯一列表容器；默认 **`--scroll-by-type Scroll`**。
- 可选 **`--item-pattern <regex>`** 只保留关心行（对 `id|key|text` 拼接串匹配）。

同时阅读 **`dump-ui` 根字段 `_hylyre_hints`**：若出现 **`likely_more_content_below`**，说明控件树提示仍有屏外内容，**禁止**仅凭首张 dump 断言「已全部枚举」。

## App 知识：`app page` + `find`

减少 **`com.huawei.hmos.wallet`** 等主页 **数百 KB** 整树 JSON 的重复传输：

- **第一轮（探索）**：照常 `dump-ui`（可加 `--filter-text` / `--summary`）与 `collect-list`；到达稳定页后：  
  `hylyre app page save -S $SF --bundle com.huawei.hmos.wallet --name <slug> --auto-fingerprint --store-dir ./cache/apps`
- **第二轮（回归）**：优先 **`hylyre app page load`** + **`hylyre app find --by-text "…"`** 取出 `by_id`/`by_key`，直接 **`hylyre run tap`**；尽量 **不再调用整树 `dump-ui`**，端到端耗时可明显下降（目标 ≥50% 降幅，依设备与网络而异）。

Framework 子进程请固定 **`--store-dir`**；Cursor MCP 默认可用仓库下 **`.hylyre/apps`**。详见 **[app-knowledge.md](./app-knowledge.md)**、**[agent-loop.md](./agent-loop.md)**「Knowledge-first loop」。

## 文档索引

- 原子循环总览：**[agent-loop.md](./agent-loop.md)**（session、`collect-list`、`_hylyre_hints`、半屏 `swipe.area` 纪律）
- JSON 步骤规约：**[agent-plan-a.md](./agent-plan-a.md)**
