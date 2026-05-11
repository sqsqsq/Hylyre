# cli Specification

## Purpose

`hylyre` 命令行入口（Typer）：`run` / `mock` / `device` / `report` / `ai` 等子命令与 `--help` 契约。

## Requirements
### Requirement: Hylyre CLI

The system SHALL ship a `hylyre` console script registering top-level commands: `run`, `mock`, `device`, `report`, `progress`, `spec`, `doctor`, `mcp`, `ai`, each with working `--help`.

#### Scenario: Doctor runs

- GIVEN a developer runs `hylyre doctor`
- WHEN the environment is inspected
- THEN Python/Node/npm/hdc/mitmproxy checks are printed in a structured table

#### Scenario: Nested report verify

- GIVEN a developer runs `hylyre report verify --help`
- WHEN P0 build is complete
- THEN help is shown (implementation completes in P4)

