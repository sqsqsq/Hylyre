# mcp-wrapper Specification

## Purpose

FastMCP 薄封装：少量原子 tool 映射 CLI 能力，控制 schema/token 体积；P5 实装。
## Requirements
### Requirement: MCP thin wrapper

The MCP wrapper SHALL expose the curated tool set (at most the existing nine curated tools in the minimal server surface, with the current extended Tier-A/session tools retained where configured) while delegating plan, steps, selector, verdict, and report behavior to the same CLI/scenario/planned-step implementations. It SHALL not define a second selector resolver, result ledger, or case status model. MCP serialization SHALL preserve `CaseResult.steps[]`, typed failure fields, expected-check mode, and evidence in emitted artifacts.

#### Scenario: MCP fake run has the same contract

- **WHEN** an MCP client invokes `hylyre_run_plan` in fake mode and then `hylyre_report_verify`
- **THEN** the artifacts pass the new trace/report contract with the same case/step semantics as CLI execution

#### Scenario: MCP invalid selector is fail-closed

- **WHEN** an MCP planned-step tool receives `match:"starts_with"`
- **THEN** shared execution returns a selector-contract failure rather than a contains match

### Requirement: MCP scroll_to tool and failure_dir passthrough

The MCP wrapper SHALL register `hylyre_run_scroll_to` mirroring the `scroll_to` planned JSON root, and SHALL accept a `failure_dir` parameter on the batch (`hylyre_run_steps`) and generic step-dispatch tools, passing it through to the shared execution logic (including the session path) so diagnostics are written equivalently to the CLI. The atomic single-action tools (e.g. `hylyre_run_tap`, `hylyre_run_scroll`) are out of scope for `failure_dir`.

#### Scenario: scroll_to tool mirrors planned JSON

- **WHEN** `hylyre_run_scroll_to` is invoked with a `scroll_to` payload
- **THEN** it dispatches the same shared logic as the CLI `run scroll-to` / planned `scroll_to` step

#### Scenario: failure_dir flows through MCP

- **WHEN** the batch (`hylyre_run_steps`) or generic step-dispatch tool is called with `failure_dir`
- **THEN** on step failure the dump/screenshot artifacts are written under that directory, matching CLI behavior

### Requirement: MCP planned-step conformance

The MCP wrapper SHALL provide at least one production regression for a planned wait/selector/verdict path and SHALL pass batch/generic step calls through the shared dispatcher, including typed skips and failure evidence. Any supported `failure_dir` parameter SHALL follow the same session path as the CLI.

#### Scenario: MCP batch preserves typed skip

- **WHEN** a batch step raises `StepSkipped`
- **THEN** the returned/emitted result is `skipped` with its failure kind/code and is not converted to a generic error

### Requirement: MCP planned-step conformance uses the production dispatcher

MCP planned wait/selector/verdict and batch paths SHALL invoke the same public planned dispatcher and result ledger as CLI execution. MCP SHALL preserve typed capability skips, selector failures, expected-check modes, and evidence; it SHALL not use a fake plan stub as its only conformance proof.

#### Scenario: MCP regression reaches shared planned execution

- **WHEN** an MCP conformance test invokes a planned wait or selector with a deterministic fake driver at the driver boundary
- **THEN** the returned StepResult is produced by the shared dispatcher with the same selector and verdict semantics as the CLI path

#### Scenario: MCP preserves a Toast capability skip

- **WHEN** a batch trigger is followed by a Toast assertion with `on_unsupported="skip"`
- **THEN** MCP returns the trigger row plus a typed skipped capability assertion row and does not convert it to a generic failed error
