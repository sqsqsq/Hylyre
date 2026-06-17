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

The system SHALL provide `ScenarioRunner` such that when `use_fakes=True`, no Hypium or Lyrebird connection is required and each parsed case receives an execution status suitable for report emission.

#### Scenario: Fake run produces artifacts

- **WHEN** `ScenarioRunner(use_fakes=True)` runs against the mock fixture plan
- **THEN** `test-report.md` and `trace.json` paths are written and `verify_report` succeeds

---

### Requirement: CLI run and verify

The system SHALL implement `hylyre run` with `--plan`, `--feature`, `--report-out`, `--trace-out`, optional `--use-fakes`, and `hylyre report verify` with `--report`, `--trace`, `--plan`.

#### Scenario: Help documents options

- **WHEN** `hylyre run --help` and `hylyre report verify --help`
- **THEN** required options are listed

---

### Requirement: Real-device scenario run

The system SHALL run `ScenarioRunner.run_plan_on_agent` when `hylyre run` is invoked **without** `--use-fakes`, connecting via `create_hypium_agent_with_env_vlm`, optionally calling `start_app` with `--bundle`, optionally activating `--mock-group` on Lyrebird, parsing each 测试步骤 line as either JSON (`action` / `touch` / `input`, no VLM required) or natural language (`ai_action`, requires `HYLYRE_VLM_ENDPOINT`), and optionally `ai_assert` on the 预期结果 column unless `--skip-assert-expected`.

#### Scenario: Trace records tool calls

- **WHEN** a real or agent-backed run completes
- **THEN** `trace.json` includes a `tool_calls` array summarizing steps (may be empty only in `--use-fakes` stub mode)

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

