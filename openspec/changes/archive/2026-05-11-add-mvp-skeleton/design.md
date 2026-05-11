# Design: add-mvp-skeleton

- **Language**: Python ≥3.10；CLI entry `hylyre = hylyre.cli.__main__:main`.
- **CLI**: Typer；子命令 `run/mock/device/report/progress/spec/doctor/mcp/ai`，`report verify` 嵌套；P0 除 `doctor` 外均为占位字符串。
- **Doctor**: 检测 Python 版本、Node/npm、hdc、mitmproxy（PATH）。
- **Contracts**: `output-schema.json`（P0 最小 trace 形状）、`report-sections.yaml`（章节与枚举骨架）。
- **Testing**: `pytest` + `tests/unit/test_cli_help.py` + `tests/schema/test_contracts_loadable.py`。
- **OpenSpec**: `openspec init --tools cursor,codex,claude --force`；变更产物在 `openspec/changes/add-mvp-skeleton/`。
