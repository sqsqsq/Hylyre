# Design: add-driver-hypium

## Decisions

- **Async driver surface**：`UiDriverBase` 全 async，便于未来与 `HylyreAgent` 对齐；Hypium 自带同步 API，用 `asyncio.to_thread` 包住，避免阻塞事件循环。
- **可选依赖**：`hypium` 仅在 `HypiumDriver.connect()` 首次需要时 `importlib.import_module("hypium")`；默认安装 `hylyre` 不拉 numpy/xdevice 重型栈，CI 以 mock 测行为。
- **HDC 与 Hypium 分工**：`device list/install` 走 `hdc` 子进程（`hylyre/drivers/hypium/hdc_cli.py`），与 Hypium 导入解耦；`ai tap/input` 走 `HypiumDriver`（真机控件语义）。
- **截图**：`UiDriverBase.screenshot -> bytes`；Hypium 侧用 `capture_screen` 写入临时文件再读回，保证类型稳定。

## Risks / follow-ups

- Hypium `BY.*` / 控件树版本差异：P1 仅暴露 text/id/坐标；复杂 selector 后续再扩展。
- `hdc install` 行为随工具链变化：失败信息直接透传 stderr，由用户在 doctor 中补齐环境。
