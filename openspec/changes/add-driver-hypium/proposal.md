# Proposal: add-driver-hypium (P1)

## Why

真机与 CI 门禁需要统一的 UI 抽象与 Hypium 适配层：`UiDriverBase` 冻结后外层 (`hylyre/api`) 才能与具体厂商 SDK 解耦；同时提供 HDC 侧常用 CLI（列设备、装包）与结构化 tap/input 入口。

## What

- `UiDriverBase`（async）与 `HypiumDriver`（懒加载 `hypium`，`pip install 'hylyre[device]'`）。
- `tests/contract/fakes/FakeUiDriver` + L1/L2/L3 测试；`pytest --cov=hylyre --cov-fail-under=70` 纳入 CI。
- CLI：`hylyre device list|install`、`hylyre ai tap|input`（P1：坐标/selector；P3 再叠 VLM 语义）。

## Non-goals (P1)

- `HylyreAgent` 全量 Midscene 动词、Lyrebird、ScenarioRunner、`report verify` 实装。
