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

- **GIVEN** a developer runs `hylyre report verify --help`
- **WHEN** P4 build is complete
- **THEN** help lists `--report`, `--trace`, and `--plan`

#### Scenario: Run lists device options

- **GIVEN** a developer runs `hylyre run --help`
- **WHEN** P4 build is complete
- **THEN** help lists `--use-fakes`, `--device-sn`, `--bundle`, `--mock-port`, `--lyrebird-url`, `--mock-group`, and `--skip-assert-expected`

#### Scenario: MCP serve help

- **GIVEN** a developer runs `hylyre mcp serve --help`
- **WHEN** P5 build is complete
- **THEN** help lists `--show-banner` and references the optional `hylyre[mcp]` dependency
