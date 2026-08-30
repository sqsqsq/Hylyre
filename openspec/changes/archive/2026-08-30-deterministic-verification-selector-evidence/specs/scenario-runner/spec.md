## MODIFIED Requirements

### Requirement: ScenarioRunner fake mode

The system SHALL provide `ScenarioRunner` such that `use_fakes=True` requires no Hypium or Lyrebird connection and every parsed case emits a `CaseResult` with `execution`, `verification`, `evidence`, `expected_check_mode`, and a complete `steps[]` ledger. Fake artifacts SHALL be explicitly marked fake; action-only or all-skipped cases SHALL not become verified passes merely because the fake operation did not throw.

#### Scenario: Fake run produces auditable artifacts

- **WHEN** the fake runner executes the mock fixture plan
- **THEN** report and trace contain the same non-empty case steps and `verify_report` accepts their projections

#### Scenario: Fake action-only case is inconclusive

- **WHEN** a fake case contains only actions
- **THEN** it records `execution="completed"`, `verification="inconclusive"`, and cannot project a verified pass

### Requirement: Real-device scenario run

The system SHALL run `ScenarioRunner.run_plan_on_agent` when the real-device CLI path is selected, connecting via the wiring factory, optionally starting the bundle and activating a Lyrebird mock group. Each 测试步骤 SHALL be accepted as planned JSON (`action` / `touch` / `input` and other registered roots) or natural language through the existing agent API. The runner SHALL execute each parsed planned step through the shared public dispatcher, create one `StepResult` before execution, finalize it for pass/fail/blocked/skipped with duration and evidence, and derive the case verdict from those steps. An expected result checked by VLM SHALL be an assertion step with `expected_check_mode="checked_vlm"`; disabled, unavailable, and empty modes SHALL be recorded explicitly. It SHALL keep `failure_kind`/`failure_code` separate from human `error`, and diagnostics SHALL not replace the original result.

#### Scenario: Failed step remains in ledger

- **WHEN** a planned step raises
- **THEN** the case retains that step with `status="failed"`, a stable failure kind/code, duration, selector/evidence when available, and a human error

#### Scenario: Expected check mode is explicit

- **WHEN** expected text is non-empty and VLM checking is disabled by flag
- **THEN** the case records `expected_check_mode="disabled_by_flag"` rather than leaving consumers to infer it from CLI arguments

### Requirement: Skipped status across runner and reporting

The execution chain SHALL support a "跳过" outcome end to end: `run_steps_on_agent` SHALL record a `StepSkipped` as `StepResult.status="skipped"` with an appropriate capability/infrastructure classification, SHALL continue according to the existing batch policy without treating the skip as an assertion pass, and SHALL project the case status as `跳过` when no stronger failure exists. A skipped-only case SHALL have `verification="inconclusive"`; `resolved_outcome` SHALL not count skipped cases as success unless every case has a verified pass and no case is merely skipped/inconclusive.

#### Scenario: Toast capability skip is typed

- **WHEN** an unsupported Toast step raises `StepSkipped`
- **THEN** the ledger records `status="skipped"`, `failure_kind="capability"`, `failure_code="capability_unsupported"`, and the case is not verified

#### Scenario: All skipped is not success

- **WHEN** every case is skipped
- **THEN** the overall outcome is `partial` or `failed` according to legacy projection policy, but never a verified success

## ADDED Requirements

### Requirement: CaseResult and StepResult ledger

The runner SHALL preserve case identity (`id`, priority, `ac_ref`, notes through `TestCase`/compatibility fields and legacy status) and add exactly the frozen fields: `execution`, `verification`, `evidence`, `expected_check_mode`, and `steps[]`. Each `StepResult` SHALL contain `index`, `kind`, `role` (`action` or `assertion`), `status` (`passed`, `failed`, `blocked`, or `skipped`), optional `failure_kind`, optional `failure_code`, `duration_ms`, optional `selector`, optional `evidence`, and optional human `error`. No independent tool-call or selector ledger is permitted.

#### Scenario: Action-only coverage is inconclusive

- **WHEN** a case executes touch, swipe, and back but no assertion role step passes
- **THEN** it records `execution="completed"`, `verification="inconclusive"`, and legacy status is not `通过`

#### Scenario: Assertion pass requires evidence

- **WHEN** an assertion returns success without its required evidence
- **THEN** the case records `evidence="incomplete"` and cannot have `verification="passed"`

### Requirement: Scenario verdict axes

The runner SHALL compute `execution` independently from `verification` and `evidence`: execution is `completed`, `aborted`, or `infrastructure_failed`; verification is `passed`, `failed`, or `inconclusive`; evidence is `complete` or `incomplete`. Verification `passed` requires at least one actually executed passing assertion, or a passing checked VLM expected assertion, all required assertions passing, and complete assertion evidence. Hylyre SHALL not emit Maison acceptance coverage, quality axes, or release verdict.

#### Scenario: Verified pass has all prerequisites

- **WHEN** a case has a passing assertion step with minimum evidence and no failed/blocked required assertion
- **THEN** it may record `verification="passed"` only if execution is completed and evidence is complete

#### Scenario: Assertion mismatch is failed verification

- **WHEN** an assertion executes and returns a mismatch
- **THEN** verification is `failed`, execution is not falsely upgraded to infrastructure failure, and the step carries `assertion_mismatch`
