# Proposal: add-scenario-runner (P4)

## Why

Skill 6 / Hylyre need a single `hylyre run` entry that reads `test-plan.md`, drives UI+mock orchestration (stubbed in fake mode first), emits `test-report.md` + `trace.json`, and runs L5 `report verify` as a gate.

## What

- Parse chapter **测试用例清单** tables from Markdown plans.
- `ScenarioRunner` with `--use-fakes` for CI (no Hypium/Lyrebird process).
- Report + trace emitters aligned with `hylyre/contracts/`.
- Implement `hylyre report verify` and wire `hylyre run` to call verify at end.
- Fixture `tests/e2e/fixtures/mock-test-plan.md` + pytest e2e.

## Out of scope

- Real-device `hylyre run` without `--use-fakes` (stub: require flag or error with clear message).
- Full step interpreter from free-text 测试步骤.
