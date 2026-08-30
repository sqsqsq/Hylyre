## ADDED Requirements

### Requirement: MCP planned-step conformance uses the production dispatcher

MCP planned wait/selector/verdict and batch paths SHALL invoke the same public planned dispatcher and result ledger as CLI execution. MCP SHALL preserve typed capability skips, selector failures, expected-check modes, and evidence; it SHALL not use a fake plan stub as its only conformance proof.

#### Scenario: MCP regression reaches shared planned execution

- **WHEN** an MCP conformance test invokes a planned wait or selector with a deterministic fake driver at the driver boundary
- **THEN** the returned StepResult is produced by the shared dispatcher with the same selector and verdict semantics as the CLI path

#### Scenario: MCP preserves a Toast capability skip

- **WHEN** a batch trigger is followed by a Toast assertion with `on_unsupported="skip"`
- **THEN** MCP returns the trigger row plus a typed skipped capability assertion row and does not convert it to a generic failed error

