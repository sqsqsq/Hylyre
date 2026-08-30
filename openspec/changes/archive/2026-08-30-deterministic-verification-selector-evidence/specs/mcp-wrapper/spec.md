## MODIFIED Requirements

### Requirement: MCP thin wrapper

The MCP wrapper SHALL expose the curated tool set (at most the existing nine curated tools in the minimal server surface, with the current extended Tier-A/session tools retained where configured) while delegating plan, steps, selector, verdict, and report behavior to the same CLI/scenario/planned-step implementations. It SHALL not define a second selector resolver, result ledger, or case status model. MCP serialization SHALL preserve `CaseResult.steps[]`, typed failure fields, expected-check mode, and evidence in emitted artifacts.

#### Scenario: MCP fake run has the same contract

- **WHEN** an MCP client invokes `hylyre_run_plan` in fake mode and then `hylyre_report_verify`
- **THEN** the artifacts pass the new trace/report contract with the same case/step semantics as CLI execution

#### Scenario: MCP invalid selector is fail-closed

- **WHEN** an MCP planned-step tool receives `match:"starts_with"`
- **THEN** shared execution returns a selector-contract failure rather than a contains match

## ADDED Requirements

### Requirement: MCP planned-step conformance

The MCP wrapper SHALL provide at least one production regression for a planned wait/selector/verdict path and SHALL pass batch/generic step calls through the shared dispatcher, including typed skips and failure evidence. Any supported `failure_dir` parameter SHALL follow the same session path as the CLI.

#### Scenario: MCP batch preserves typed skip

- **WHEN** a batch step raises `StepSkipped`
- **THEN** the returned/emitted result is `skipped` with its failure kind/code and is not converted to a generic error
