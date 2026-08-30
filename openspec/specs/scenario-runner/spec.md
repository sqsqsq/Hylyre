# scenario-runner Specification

## Purpose

Parse `test-plan.md`, run scenarios (fake or future real device), emit `test-report.md` + `trace.json`, and verify via `hylyre report verify`.
## Requirements
### Requirement: Test plan parsing

The system SHALL parse `test-plan.md` files for a Markdown table under a heading containing `测试用例清单`, producing rows with columns: 用例编号, 用例名称, 前置条件, 测试步骤, 预期结果, 优先级, 关联 AC.

#### Scenario: Fixture plan parses

- **WHEN** `tests/e2e/fixtures/mock-test-plan.md` is parsed
- **THEN** at least one `TestCase` is returned with non-empty 用例编号 and 关联 AC

---

### Requirement: ScenarioRunner fake mode

The system SHALL provide `ScenarioRunner` such that `use_fakes=True` requires no Hypium or Lyrebird connection and every parsed case emits a `CaseResult` with `execution`, `verification`, `evidence`, `expected_check_mode`, and a complete `steps[]` ledger. Fake artifacts SHALL be explicitly marked fake; action-only or all-skipped cases SHALL not become verified passes merely because the fake operation did not throw.

#### Scenario: Fake run produces auditable artifacts

- **WHEN** the fake runner executes the mock fixture plan
- **THEN** report and trace contain the same non-empty case steps and `verify_report` accepts their projections

#### Scenario: Fake action-only case is inconclusive

- **WHEN** a fake case contains only actions
- **THEN** it records `execution="completed"`, `verification="inconclusive"`, and cannot project a verified pass

### Requirement: CLI run and verify

The system SHALL implement `hylyre run` with `--plan`, `--feature`, `--report-out`, `--trace-out`, optional `--use-fakes`, and `hylyre report verify` with `--report`, `--trace`, `--plan`.

#### Scenario: Help documents options

- **WHEN** `hylyre run --help` and `hylyre report verify --help`
- **THEN** required options are listed

---

### Requirement: Real-device scenario run

The system SHALL run `ScenarioRunner.run_plan_on_agent` when the real-device CLI path is selected, connecting via the wiring factory, optionally starting the bundle and activating a Lyrebird mock group. Each 测试步骤 SHALL be accepted as planned JSON (`action` / `touch` / `input` and other registered roots) or natural language through the existing agent API. The runner SHALL execute each parsed planned step through the shared public dispatcher, create one `StepResult` before execution, finalize it for pass/fail/blocked/skipped with duration and evidence, and derive the case verdict from those steps. An expected result checked by VLM SHALL be an assertion step with `expected_check_mode="checked_vlm"`; disabled, unavailable, and empty modes SHALL be recorded explicitly. It SHALL keep `failure_kind`/`failure_code` separate from human `error`, and diagnostics SHALL not replace the original result.

#### Scenario: Failed step remains in ledger

- **WHEN** a planned step raises
- **THEN** the case retains that step with `status="failed"`, a stable failure kind/code, duration, selector/evidence when available, and a human error

#### Scenario: Expected check mode is explicit

- **WHEN** expected text is non-empty and VLM checking is disabled by flag
- **THEN** the case records `expected_check_mode="disabled_by_flag"` rather than leaving consumers to infer it from CLI arguments

### Requirement: Step failure diagnostics

`ScenarioRunner.run_plan_on_agent` and `run_steps_on_agent` SHALL accept a `failure_dir`. On step failure they SHALL make a best-effort capture of the current UI dump (JSON) and a screenshot (PNG) into `failure_dir/step-<n>.{json,png}`, attaching the relative paths to the case notes / per-step results (and thus into the trace `cases[].notes`). The diagnostics capture SHALL swallow its own exceptions so that a failing capture never masks the original step error. The `failure_dir` SHALL be threaded through the session daemon path (`execute_run_steps` → session IPC params → daemon `run_steps`/`run_step` → `run_steps_on_agent`); under a session it SHALL be an absolute path written locally by the daemon process.

#### Scenario: Failure leaves dump and screenshot

- **WHEN** a step fails and `failure_dir` is set
- **THEN** `step-<n>.json` and `step-<n>.png` are written and their relative paths appear in the case notes/trace

#### Scenario: Diagnostics failure does not mask the real error

- **WHEN** capturing the dump/screenshot itself raises
- **THEN** the original step error is still reported (the diagnostics exception is swallowed)

#### Scenario: Session daemon path carries failure_dir

- **WHEN** `hylyre run --steps-file ... --session ... --failure-dir <abs>` runs
- **THEN** the daemon process writes the diagnostics under the provided absolute directory

### Requirement: Skipped status across runner and reporting

The execution chain SHALL support a "跳过" outcome end to end: `run_steps_on_agent` SHALL record a `StepSkipped` as `StepResult.status="skipped"` with an appropriate capability/infrastructure classification, SHALL continue according to the existing batch policy without treating the skip as an assertion pass, and SHALL project the case status as `跳过` when no stronger failure exists. A skipped-only case SHALL have `verification="inconclusive"`; `resolved_outcome` SHALL not count skipped cases as success unless every case has a verified pass and no case is merely skipped/inconclusive.

#### Scenario: Toast capability skip is typed

- **WHEN** an unsupported Toast step raises `StepSkipped`
- **THEN** the ledger records `status="skipped"`, `failure_kind="capability"`, `failure_code="capability_unsupported"`, and the case is not verified

#### Scenario: All skipped is not success

- **WHEN** every case is skipped
- **THEN** the overall outcome is `partial` or `failed` according to legacy projection policy, but never a verified success

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

### Requirement: Complete ledger and strict three-axis verdict

The scenario runner SHALL append one `StepResult` for every planned row, including typed `blocked` rows for the unexecuted suffix after abort and a typed expected-check row whenever expected text is non-empty. It SHALL compute `execution`, `verification`, and `evidence` from that ledger: only completed execution with every required assertion passing and non-empty assertion evidence may be verified; action-only, all-skipped, aborted, and blocked cases cannot pass. Runtime and harness outcome projection SHALL use the same algorithm.

#### Scenario: Abort still leaves a complete plan ledger

- **WHEN** step 1 fails under abort-on-failure and steps 2 and 3 were planned
- **THEN** steps 2 and 3 are present as `blocked` rows with stable failure fields and the case cannot be a verified pass

#### Scenario: Non-empty expected mode is not erased by abort

- **WHEN** expected text exists, VLM is available, and an earlier action aborts before the expected check
- **THEN** `expected_check_mode` is `checked_vlm` and the expected-check row records that it was blocked rather than changing the mode to `empty`

#### Scenario: Skipped assertions prevent verified pass

- **WHEN** one assertion passes and another required Toast assertion is skipped
- **THEN** verification is `inconclusive` or `failed`, never `passed`

#### Scenario: Empty evidence is incomplete

- **WHEN** an assertion returns success with `{}` or no evidence
- **THEN** case evidence is `incomplete` and verification is not `passed`

#### Scenario: Runtime and harness agree

- **WHEN** a report contains one verified case and one blocked case
- **THEN** runtime emission and `verify_report` compute the same overall outcome

### Requirement: Toast window participates in verdict coverage

The scenario verdict SHALL reject a verified pass when any passing `assert_toast` step lacks `evidence.trigger_window_covered=true`. The step may remain `passed` as an operation result, but the case verification SHALL be `inconclusive` unless the required covered assertion path exists.

#### Scenario: Uncovered Toast is not a verified assertion

- **WHEN** an assertion-only Toast operation returns true with `trigger_window_covered=false`
- **THEN** case verification is not passed

### Requirement: Blocked suffix preserves causal classification and count

When abort stops a plan, blocked rows SHALL retain the root failure kind/code as their causal classification where the frozen taxonomy permits it; batch `executed` SHALL count only dispatched operations, while the result array still contains all blocked audit rows.

#### Scenario: Selector failure blocks without becoming infrastructure

- **WHEN** a selector miss aborts step 1 and step 2 is not dispatched
- **THEN** step 2 is blocked with selector causal classification and `executed` remains 1
