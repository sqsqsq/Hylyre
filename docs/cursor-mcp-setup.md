# Cursor 中一次性启用 Hylyre MCP

配置完成后，Agent 可直接调用 **`hylyre_*`** 工具，无需在每轮对话里复述 CLI 用法。

**工具总数**：当前约 **42** 个（见 **`tests/unit/test_mcp_server.py`** 中的 `expected` 集合）。

**常用工具（节选）**：

| 类别 | MCP 工具 |
|------|----------|
| 环境 / 设备 | `hylyre_doctor`、`hylyre_device_list` |
| 感知 | `hylyre_dump_ui`、`hylyre_screenshot`、`hylyre_find`、`hylyre_collect_list` |
| 回归 | `hylyre_run_plan`、`hylyre_run_steps`、`hylyre_report_*` |
| 触控 / 输入 | `hylyre_run_tap`、`hylyre_run_input`、`hylyre_run_swipe`、`hylyre_run_scroll` |
| **Tier A 导航 / 等待** | **`hylyre_run_back`**、**`hylyre_run_home`**、**`hylyre_run_stop_app`**、**`hylyre_run_clear_app`**、**`hylyre_run_wait`**、**`hylyre_run_wait_for`**、**`hylyre_run_wait_gone`**、**`hylyre_run_wait_idle`**、**`hylyre_run_assert_toast`** |
| 启动应用 | `hylyre_start_app`（旗标式）、**`hylyre_run_start_app_step`**（planned JSON 根键 `start_app`） |
| App 知识 | `hylyre_app_page_*`、`hylyre_app_find`、`hylyre_app_fingerprint` |
| 会话 | `hylyre_open_session`、`hylyre_close_session` |

Planned JSON 根键与 payload 示例见 **[agent-plan-a.md](./agent-plan-a.md)** §2.1。

## 前提

```bash
pip install -e ".[dev,mcp]"
# 真机 + hylyre_run_* / dump-ui 另需:
pip install -e ".[device]"
```

`hylyre mcp serve` 需在**本仓库根目录**下能找到 `hylyre` 包（可编辑安装或设置 `PYTHONPATH`）。

## Cursor：MCP 配置片段

在 Cursor **Settings → MCP** 的 JSON 中增加一项（把 `cwd` 换成你的 Hylyre 克隆路径）：

```json
"hylyre": {
  "command": "python",
  "args": ["-m", "hylyre", "mcp", "serve", "--transport", "stdio"],
  "cwd": "/absolute/path/to/Hylyre"
}
```

Windows 示例：

```json
"hylyre": {
  "command": "D:\\Program Files\\Python314\\python.exe",
  "args": ["-m", "hylyre", "mcp", "serve", "--transport", "stdio"],
  "cwd": "D:\\1.code\\Hylyre"
}
```

若默认解释器不在 PATH 上，把 `command` 换成完整 `python.exe` 路径。

保存后**重载窗口**或重启 Cursor，在 Agent 可用工具列表中应出现 **hylyre** server（绿色）及以 `hylyre_` 为前缀的工具。

## App 知识目录与 MCP `cwd`

快照与索引的默认**写路径**含 **`<cwd>/.hylyre/apps`**。MCP 子进程的 **`cwd` 即此项中的 cwd**：若配置成用户主目录等非仓库路径，写入会落到 **`~/.hylyre/apps`** 等位置，与你在克隆根目录用 CLI 产生的 **`./.hylyre/apps`** 不一致，表现为「明明保存了却 **`hylyre_app_find` 命中不了**」。请始终将 **`cwd` 设为 Hylyre 仓库根**，或统一设置环境变量 **`HYLYRE_APP_STORE_DIR`**。

## 环境变量（按需）

与终端运行 Hylyre 相同：真机 NL/VLM 步骤需 **`HYLYRE_VLM_*`**；Lyrebird 可设 **`HYLYRE_LYREBIRD_URL`**。MCP 子进程会继承 **Cursor 启动时** 的环境变量（修改 **PATH** / **hdc** 后需**重启 Cursor** 才会传入 MCP 子进程）。

## 验证

1. **通路**：Agent 请求「调用 **`hylyre_doctor`** 并把原文返回」。
2. **离线烟测**：`hylyre_run_plan`，`use_fakes=true`，plan 指向 `tests/e2e/fixtures/mock-test-plan.md`。
3. **Tier A（真机）**：`hylyre_open_session` → **`hylyre_run_back`**，payload `{"back":{}}` → **`hylyre_find`**，`by_text="首页"`（需 **hdc** 在 MCP 进程的 PATH 中）。
