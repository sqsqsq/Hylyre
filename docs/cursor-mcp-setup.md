# Cursor 中一次性启用 Hylyre MCP

配置完成后，Agent 可直接调用 **`hylyre_run_plan`**、**`hylyre_doctor`**、**`hylyre_dump_ui`**、**`hylyre_run_swipe`** / **`hylyre_run_scroll`** 等工具，无需在每轮对话里复述 CLI 用法（完整清单见 Cursor 工具列表或仓库 **`tests/unit/test_mcp_server.py`**）。

## 前提

```bash
pip install -e ".[dev]"
# 真机 + hylyre_ai_* 另需: pip install -e ".[device]"
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
  "command": "python",
  "args": ["-m", "hylyre", "mcp", "serve", "--transport", "stdio"],
  "cwd": "E:\\1.code\\Hylyre"
}
```

若默认解释器不在 PATH 上，把 `command` 换成完整 `python.exe` 路径。

保存后**重载窗口**或重启 Cursor，在 Agent 可用工具列表中应出现以 `hylyre_` 为前缀的工具。

## 环境变量（按需）

与终端运行 Hylyre 相同：真机 NL/VLM 步骤需 **`HYLYRE_VLM_*`**；Lyrebrid 可设 **`HYLYRE_LYREBIRD_URL`**。MCP 子进程会继承 Cursor 启动环境（可在 shell profile 或系统环境变量中设置）。

## 验证

在 Agent 中请求：「调用 `hylyre_doctor` 并把原文返回」，或运行 `hylyre_run_plan` 且 `use_fakes=true` 指向本仓库 `tests/e2e/fixtures/mock-test-plan.md`。
