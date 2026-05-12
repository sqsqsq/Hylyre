# mcp-wrapper Specification

## Purpose

FastMCP 薄封装：少量原子 tool 映射 CLI 能力，控制 schema/token 体积；P5 实装。

## Requirements
### Requirement: MCP thin wrapper

The system SHALL expose `hylyre mcp serve` wiring a curated tool set (**≤9**) mirroring CLI subsets, using the same implementations as Typer commands where applicable (shared `hylyre.cli.commands.*` and `run_cmd.execute_*`).

#### Scenario: Tools list

- GIVEN `fastmcp` is installed (`pip install 'hylyre[mcp]'` or the `dev` extra)
- WHEN tests load `build_mcp()` and call `list_tools()`
- THEN exactly nine tools exist: `hylyre_run_plan`, `hylyre_report_verify`, `hylyre_device_list`, `hylyre_doctor`, `hylyre_ai_action`, `hylyre_ai_query`, `hylyre_ai_assert`, `hylyre_mock_activate`, `hylyre_progress_show`

#### Scenario: Stdio server entry

- GIVEN a developer runs `hylyre mcp serve --help`
- WHEN the command parses
- THEN help describes the server and optional `--show-banner` and `--transport` (stdio only)

#### Scenario: Fake run parity

- GIVEN the e2e fixture `tests/e2e/fixtures/mock-test-plan.md`
- WHEN an MCP client calls `hylyre_run_plan` with `use_fakes=true` and then `hylyre_report_verify`
- THEN both tools succeed and artifacts pass L5 verification

#### Scenario: Progress excerpt

- GIVEN the Hylyre repo checkout is cwd (or discoverable via `pyproject.toml`)
- WHEN an MCP client calls `hylyre_progress_show` with a small `tail_lines`
- THEN the tool returns a string containing `docs/progress.md` path and file tail (or missing-file hint)
