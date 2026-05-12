# Proposal: add-driver-lyrebird (P2)

## Why

HTTP Mock（Lyrebird）需要与 Hypium 对称的一层：`MockControllerBase` 冻结契约，Lyrebird 走 HTTP Admin API；CLI 提供 `mock start|stop|activate|capture`，CI 用 respx 假接口，不强制真进程。

## What Changes

- 引入 `MockControllerBase` 与 `LyrebirdController`（`httpx` + 可选 `python -m lyrebird` 子进程）。
- Typer：`hylyre mock …` 子命令；PID 文件（默认 `./.hylyre/lyrebird.pid`）；`mock cert` 输出 HarmonyOS 信任 MITM 的手工清单（自动化留给 `add-cert-bootstrap`）。
- 测试：`FakeMockController`、respx 单测、CLI mock。

## Non-goals (本 change)

- 完整 HAR 导出格式、真机证书一键安装、ScenarioRunner 串联（P4）。
