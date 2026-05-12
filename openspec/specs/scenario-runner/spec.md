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
