## 1. Implementation

- [x] 1.1 `hylyre/scenario/*` plan parser + `ScenarioRunner` (fake mode)
- [x] 1.2 `hylyre/report/emit.py` report + trace builders
- [x] 1.3 Expand `output-schema.json` + keep L4 load test green
- [x] 1.4 Implement `hylyre.harness.verify_report`
- [x] 1.5 CLI `hylyre run` + `hylyre report verify` options
- [x] 1.6 Fixture `tests/e2e/fixtures/mock-test-plan.md` + e2e + unit tests
- [x] 1.7 Archive change + merge spec deltas into `openspec/specs/`（`openspec/changes/archive/2026-05-12-add-scenario-runner/`；稳态 `openspec/specs/scenario-runner/spec.md`）

## 2. Validation

- [x] 2.1 `pytest` full suite green
- [x] 2.2 `hylyre run --use-fakes …` + `hylyre report verify …` on fixture exits 0
