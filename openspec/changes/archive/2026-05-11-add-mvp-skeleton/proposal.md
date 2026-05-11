# Proposal: add-mvp-skeleton (P0)

## Why

HarmonyOS 真机测试需要可脚本化、可自查的执行器：Hypium 驱动 + Lyrebird Mock + 契约化报告/trace，且 **不依赖** 业务仓在线即可完成质量门禁。

## What

- Python 包 `hylyre`、CLI `hylyre`（P0 占位子命令 + `doctor` 实装）。
- `hylyre/contracts` 与 `tests/schema` 占位；GitHub Actions `ci.yml` / `compat-framework.yml`。
- OpenSpec 初始化（cursor / codex / claude 路由）；本 change 的 spec deltas。

## Non-goals (P0)

- 真实 Hypium/Lyrebird 端到端、VLM、`hylyre run` 全量、`report verify` 实装（P1–P4）。
