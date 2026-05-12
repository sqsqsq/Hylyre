# scenario-runner Specification (delta)

## ADDED Requirements

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
