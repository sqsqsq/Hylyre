# Hylyre

## Purpose

Hylyre 将 **Hypium**（鸿蒙 UI 自动化）与 **Lyrebird**（HTTP Mock）封装为面向 AI 与 CI 的统一真机测试工具链：CLI 优先、可选 MCP 薄壳、API 风格对齐 Midscene 语义动词；输出契约以本仓 `hylyre/contracts/` 为 **SSOT**，并对下游 framework 门禁做**软提醒**级兼容照镜。

## Architecture

- **外层**：`hylyre/api`、`hylyre/cli` — Midscene 式 `ai_action` / `ai_query` 等；`hylyre run` 串联场景。
- **内层**：`hylyre/drivers/hypium`、`hylyre/drivers/lyrebird` — 仅在内层引用三方 SDK。
- **质量**：五层自测试（L1–L5）与 `hylyre/harness` mini-harness；不依赖外部仓跑通主 CI。

## Conventions

- 规划 SSOT：`docs/plan.md`；进度叙事：`docs/progress.md`。
- OpenSpec change 归档前必须 `pytest` 绿（含契约加载测）。
- 不在本仓 `git submodule` 业务 framework；契约漂移写入 `docs/progress.md`。
