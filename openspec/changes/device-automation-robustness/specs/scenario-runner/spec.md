## ADDED Requirements

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

The execution chain SHALL support a "跳过" (skipped) outcome end to end: `run_steps_on_agent` SHALL record `status:"skipped"` (distinct from `error`) when a step raises `StepSkipped` and SHALL NOT abort under `on_fail="abort"`; `steps_batch_to_scenario_result` SHALL map `skipped` to "跳过"; `ScenarioRunner` SHALL map a `StepSkipped` to `CaseResult(status="跳过")`; and `resolved_outcome` SHALL NOT count "跳过" as a failure.

#### Scenario: Toast skip recorded as 跳过, not 失败

- **WHEN** an `assert_toast` step raises `StepSkipped` during a steps batch or plan run
- **THEN** the case is recorded with status "跳过" and the overall outcome is not marked failed solely due to the skip
