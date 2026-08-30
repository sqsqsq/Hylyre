## ADDED Requirements

### Requirement: Strict new trace evidence and explicit legacy labeling

The new trace schema SHALL require selector evidence fields `engine`, `requested_match`, `effective_match`, and `candidate_count` whenever `StepResult.selector` is non-null, require non-empty evidence for passing assertions, enforce unique case IDs and step indexes, and verify that report case IDs, Markdown rows, and `tool_calls` are derived from `CaseResult.steps[]`. The verifier and CLI/MCP output SHALL label `0.1-p0` and `0.2-p4` traces as legacy and SHALL not describe them as new StepResult evidence. The frozen failure-code enum SHALL not gain a separate invalid-match member.

#### Scenario: Incomplete selector evidence is rejected

- **WHEN** a new trace changes a selector object to `{}`
- **THEN** schema/report verification fails because the required selector evidence fields are absent

#### Scenario: Duplicate identity is rejected

- **WHEN** a trace repeats a case ID or repeats a step index within a case
- **THEN** verification fails before reporting success

#### Scenario: Legacy output is explicit

- **WHEN** a legacy trace is verified
- **THEN** verification may retain readable compatibility status but emits an explicit legacy/ineligible marker

#### Scenario: Projections have one source

- **WHEN** `tool_calls` or Markdown step data diverges from `cases[].steps[]`
- **THEN** verification fails rather than trusting a second projection source
