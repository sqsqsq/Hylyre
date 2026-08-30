## Why

The first deterministic-verification delivery exposed contract gaps under adversarial cases: an aborted or partially skipped case could still become a verified pass, selector constraints could be widened by fallback paths, and the ledger/report/trace projections could disagree. These are release-blocking because Maison consumes the serialized evidence rather than the in-process control flow.

## What Changes

- **BREAKING** Make verdict computation require completed execution, all required assertions to pass, and non-empty assertion evidence; action-only, all-skipped, aborted, and blocked cases cannot be verified passes.
- Make every planned step appear in the single `CaseResult.steps[]` ledger, including blocked steps after an abort and an expected-check row when the check is configured but cannot run.
- Unify runtime and harness outcome calculation and make legacy traces explicitly identifiable and ineligible for new evidence claims.
- Enforce selector validation recursively and fail closed for missing overlays, unsatisfied anchors, invalid match values, and ambiguous swipe/scroll/scroll-to containers; keep exact/contains and the frozen failure-code interface.
- Correct rich-text resolution so ordinary Text `contains` remains addressable while aggregate/ordinary spans without real clickable semantics or fragment bounds remain unresolvable.
- Start Toast observation before trigger actions in plan and batch execution, honor `on_unsupported: skip`, preserve boolean false as assertion mismatch, and classify capability failures distinctly.
- Require selector evidence fields in the new trace schema and redact sensitive selector, error, note, and evidence text before trace/report emission.
- Add production-entry conformance regressions for plan, steps, CLI, and MCP paths, then update canonical specs, migration documentation, changelog, and release-source artifacts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-agent`: harden planned selector/action/wait semantics, rich-text fail-closed behavior, and assertion/verdict evidence.
- `driver-hypium`: preserve typed Toast capability outcomes and native selector evidence without extending the frozen failure-code set.
- `scenario-runner`: complete the planned-step ledger, expected-check modes, assertion coverage, and shared outcome algorithm.
- `contracts`: make new-schema selector/evidence gates strict, validate projections, and label legacy traces explicitly.
- `selector-resolution`: validate all nested constraints, enforce overlay/anchor fail-closed behavior, and distinguish ordinary Text from unresolved inline targets.
- `cli`: keep plan, steps-file, atomic, and report verification on the shared production path, including explicit legacy output.
- `mcp-wrapper`: retain the same dispatcher and result semantics with production-entry conformance coverage.

## Impact

The affected implementation is under `hylyre/api`, `hylyre/drivers`, `hylyre/scenario`, `hylyre/harness`, `hylyre/report`, `hylyre/cli`, and `hylyre/mcp`. The JSON trace schema, Markdown projection, failure classification behavior for invalid selectors, and compatibility verification output become stricter. No Maison files, vendor tree, PyPI package, or real-device claim are changed.
