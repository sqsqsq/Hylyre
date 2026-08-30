## Why

Hylyre 0.3.2 collapses execution, verification, and evidence into exception-free success, while selector engines and match defaults differ across planned-step paths. This permits false passes, guessed multi-match actions, missed Toast results, and reports that cannot prove what was executed; the change makes the executor deterministic and auditable before Maison consumes its artifacts.

## What Changes

- **BREAKING**: Introduce the frozen `CaseResult`/`StepResult` ledger and three-axis verdict (`execution`, `verification`, `evidence`), with the legacy status retained only as a compatibility projection.
- **BREAKING**: Make `wait_for`/`wait_gone` consume Hypium return values, unify exact/contains selector semantics, reject invalid match modes, and fail closed on ambiguous actions.
- **BREAKING**: Correct Toast lifecycle/result handling and distinguish assertion mismatch from unsupported capability.
- Make rich-text interaction fail closed unless real fragment-level targeting evidence is available; add a deterministic aggregate-Text fixture.
- Version and validate trace output, derive `tool_calls` and Markdown from `CaseResult.steps[]`, and record selector/environment/assertion evidence.
- Keep CLI, steps-file, plan, and MCP execution on the same planned-step production path; add conformance coverage for each entry point.
- Add sensitive-evidence handling, version/migration documentation, CHANGELOG guidance, and a verified `release-src` delivery. OCR, new assertion primitives, and extra match modes remain out of scope.

## Capabilities

### New Capabilities

None. The existing canonical capabilities are extended so there is one contract and one execution path.

### Modified Capabilities

- `api-agent`: planned wait/action/assertion semantics, selector matching, ambiguity, rich-text fail-closed behavior, and ledger-facing results.
- `driver-hypium`: wait return-value checks, native MatchPattern forwarding, Toast observation/result classification, and stable failure kinds/codes.
- `scenario-runner`: execution/verification/evidence verdicts, expected-check modes, skipped semantics, and the StepResult ledger.
- `contracts`: versioned trace schema, CaseResult/StepResult shape, enum/uniqueness rules, and report/trace derivation consistency.
- `selector-resolution`: exact/contains validation, fail-closed matching and action resolution, and inline target resolution evidence.
- `cli`: shared planned-step execution for plan and steps-file paths plus trace/report verification entry points.
- `mcp-wrapper`: thin delegation to the same CLI/runner planned-step path without a second selector or result model.

## Impact

Production changes touch `hylyre/api`, `hylyre/drivers/hypium`, `hylyre/scenario`, `hylyre/report`, `hylyre/contracts`, CLI/MCP/session adapters, and versioned documentation. Tests will cover fake, resolver, native-adapter, plan, steps-file, CLI, and MCP public entrances; no Maison files, PyPI publication, OCR, or live-device claims are included.
