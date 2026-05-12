# cli Specification

## Purpose

`hylyre` 命令行入口（Typer）：`run` / `mock` / `device` / `report` / `bootstrap` / `ai` 等子命令与 `--help` 契约。

## Requirements
### Requirement: Hylyre CLI

The system SHALL ship a `hylyre` console script registering top-level commands: `run`, `mock`, `device`, `report`, `progress`, `spec`, `doctor`, `bootstrap`, `mcp`, `ai`, each with working `--help`.

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
- **THEN** help lists `--use-fakes`, `--device-sn`, `--bundle`, `--mock-port`, `--lyrebird-url`, `--mock-group`, `--skip-assert-expected`, and `--model-backend`

#### Scenario: Progress helpers

- **GIVEN** a developer runs `hylyre progress --help`
- **WHEN** the command group is present
- **THEN** help lists `show`, `append`, and `path` subcommands for `docs/progress.md`

#### Scenario: Spec list

- **GIVEN** a developer runs `hylyre spec list --help` or bare `hylyre spec`
- **WHEN** OpenSpec workspace exists
- **THEN** `list` prints `openspec list` when the CLI is on PATH, else a directory summary under `openspec/specs` and `openspec/changes`

#### Scenario: Device list first serial

- **GIVEN** a developer runs `hylyre device list --help`
- **WHEN** P1+ device commands exist
- **THEN** help lists `--first` for scripting (`hylyre device list --first`)

#### Scenario: MCP serve help

- **GIVEN** a developer runs `hylyre mcp serve --help`
- **WHEN** P5 build is complete
- **THEN** help lists `--show-banner`, `--transport` (stdio only), and references the optional `hylyre[mcp]` dependency

#### Scenario: Bootstrap mock help

- **GIVEN** a developer runs `hylyre bootstrap mock --help`
- **WHEN** P2b command is present
- **THEN** help lists `--install` for optional `pip install mitmproxy lyrebird`
