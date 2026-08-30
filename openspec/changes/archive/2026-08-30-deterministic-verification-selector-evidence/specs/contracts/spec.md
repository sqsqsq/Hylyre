## MODIFIED Requirements

### Requirement: Output contracts SSOT

The system SHALL version output shapes under `hylyre/contracts/`. The trace schema SHALL define the new `CaseResult`/`StepResult` ledger, status and verdict enums, failure taxonomy, expected-check modes, selector/evidence fields, unique case/step identity, and the compatibility projection fields. The Markdown report and `tool_calls` are projections of the same `cases[].steps[]` data and SHALL not be independently maintained.

#### Scenario: Contract files load

- **WHEN** the schema and report contract are loaded
- **THEN** JSON Schema draft 2020-12 validates, YAML parses, and the required legacy report sections/statuses remain available

## ADDED Requirements

### Requirement: CaseResult and StepResult trace shape

New-schema trace cases SHALL retain `id`, `priority`, `ac_ref`, `notes`, and legacy `status`, and SHALL include:

```text
execution: completed | aborted | infrastructure_failed
verification: passed | failed | inconclusive
evidence: complete | incomplete
expected_check_mode: checked_vlm | disabled_by_flag | unavailable_no_vlm | empty
steps: StepResult[]
```

Each step SHALL include `index`, `kind`, `role`, `status`, `duration_ms`; it SHALL carry `failure_kind`/`failure_code` for classified non-pass outcomes and may carry `selector`, `evidence`, and human `error`. `role` is only `action` or `assertion`; `status` is only `passed`, `failed`, `blocked`, or `skipped`; failure kinds are only `assertion`, `selector`, `capability`, or `infrastructure`.

#### Scenario: Non-empty case has complete steps

- **WHEN** a new-schema trace contains a case with planned or executed content
- **THEN** it contains a non-empty `steps` array whose indexes are unique and whose roles/statuses use the contract enums

#### Scenario: Duplicate identity is rejected

- **WHEN** two cases share an id or two steps in one case share an index
- **THEN** trace verification fails

### Requirement: Trace environment and selector evidence

New-schema traces SHALL record the Hylyre version, Hypium version (or an explicit unavailable marker), trace schema version, selector engine, requested/effective match, candidate count, selected id/bounds where applicable, and assertion evidence. Selector details belong in `StepResult.selector`; Toast, absence, rich-text, and non-selector assertion details belong in `StepResult.evidence`.

#### Scenario: Selector execution is auditable

- **WHEN** a selector step passes, fails, or is skipped
- **THEN** its step evidence records engine, requested/effective match, candidate count, and selected target/bounds when available

#### Scenario: Assertion success is auditable

- **WHEN** a Toast, absence, or non-selector assertion passes
- **THEN** its step contains the corresponding minimum evidence and the case may only be verified when that evidence is complete

### Requirement: Trace/report consistency and derived projections

`verify_report` SHALL reject a new-schema report/trace pair when their case id sets differ, when case status/identity diverges, when `tool_calls` is not derivable from `steps[]`, or when the Markdown step/case projection does not correspond to the trace ledger. It SHALL identify legacy schema traces explicitly and SHALL not claim that they contain new StepResult evidence.

#### Scenario: Case-set mismatch fails verification

- **WHEN** report and trace contain different case ids
- **THEN** `verify_report` fails

#### Scenario: Tool calls have one source

- **WHEN** a trace is emitted
- **THEN** `tool_calls` and Markdown step details are reproducible from `cases[].steps[]` without a second runtime log

### Requirement: Legacy trace compatibility

The verifier SHALL recognize existing `0.1-p0` and `0.2-p4` traces as `legacy`, retain their readable `status`/`tool_calls` data, and reject treating them as new-schema verified evidence when `steps[]` is absent or incomplete. Legacy reading SHALL not rewrite historical artifacts.

#### Scenario: Old trace is labeled legacy

- **WHEN** a trace has schema version `0.2-p4` and no StepResult ledger
- **THEN** it remains readable but is explicitly reported as legacy/ineligible for new evidence claims
