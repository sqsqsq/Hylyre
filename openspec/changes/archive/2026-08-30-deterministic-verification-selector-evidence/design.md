## Context

Hylyre 0.3.2 has four coupled problems: planned operations do not produce a complete per-step result, `ScenarioRunner` treats exception-free execution as a verified pass, native and dump-based selector paths use different text semantics, and Hypium wait/Toast adapters discard meaningful return values. The existing report and trace also maintain `tool_calls` independently from the execution path.

The authoritative input is `hylyre-断言与证据完整性需求.md`. The implementation must stay inside Hylyre, preserve optional Hypium imports, keep the CLI/MCP wrappers thin, and avoid adding a second evidence ledger, selector ledger, Toast report, or case-state model. Maison remains responsible for acceptance coverage, quality axes, and release verdicts.

## Goals / Non-Goals

**Goals:**

- Make `CaseResult.steps[]` the only execution evidence source and derive trace `tool_calls` and Markdown from it.
- Freeze the CaseResult/StepResult fields, three-axis verdict, expected-check mode, failure taxonomy, and trace schema validation.
- Make exact/contains matching explicit and consistent across resolver, native adapter, fake driver, touch, input, wait, wait_gone, and scroll paths.
- Fail closed for missing or ambiguous action selectors and for aggregate rich-text targets without real fragment-level targeting evidence.
- Correct wait and Toast adapter contracts, preserving the distinction between assertion mismatch and unsupported capability.
- Exercise the real public planned-step path through plan, steps-file, CLI, and MCP tests, and ship a verifiable plain-source release.

**Non-Goals:**

- No Maison changes, PyPI publication, live-device claim, OCR, glyph-layout positioning, new assertion primitives, or `starts_with`/`ends_with`/`regex` support.
- No acceptance coverage, P0/quality-axis/release-verdict model in Hylyre.
- No automatic exact-to-contains fallback, first-candidate selection, character-proportion coordinate estimation, or log-based reconstruction of results.

## Decisions

1. **One result model at the scenario boundary.** Add serializable `StepResult` and `CaseResult` fields in the scenario layer while retaining `case`, legacy `status`, and `notes`. A runner-owned ledger is created for every planned step before execution and finalized in one place. This keeps the existing public plan model intact while making the new fields authoritative. An alternative was a separate evidence sidecar; it is rejected because it would create a second truth source.

2. **Operation adapters return evidence, but do not own case state.** Planned agent/driver operations may return a small evidence mapping (selector engine/match/candidates, Toast channel/event, or assertion evidence) that the runner places into the current StepResult. No mutable selector ledger or report-specific state is added. Existing callers may ignore the return value.

3. **A shared selector contract is validated before dispatch.** `exact` and `contains` are the only accepted values. Missing `match` resolves to the documented compatibility default and records that effective value. Native Hypium selectors receive the corresponding `MatchPattern`; resolver and fake paths call the same pure text matcher. Action resolution requires one hit unless the existing `index`, `scope`, `within`, or `all` fields produce a unique target. Assertion resolution can retain a candidate count without weakening action uniqueness.

4. **Wait and Toast success are based on framework results.** Native wait methods inspect `None`/non-`None` according to the Hypium contract and raise stable classified errors with selector and timeout. Toast observation starts before the triggering action where the runner can see an `assert_toast` step adjacent to the action; the adapter polls the supported check, returns only for a true result, preserves the original exception classification, and maps known unsupported capability to `StepSkipped` only when requested. A normal false/not-found result is an assertion failure.

5. **Verdicts are calculated from the ledger.** Execution records whether the case completed, aborted, or failed due to infrastructure. Verification is passed only when at least one executed assertion (or checked VLM expected assertion) passed, all required assertions passed, and assertion evidence is complete. Action-only and all-skipped cases are inconclusive. Evidence is incomplete when a failed capture or required assertion evidence is absent. The old Chinese status remains a projection for existing report consumers.

6. **Trace schema validation is strict for the new schema and explicit for legacy.** New traces contain unique case ids, unique step indexes per case, complete non-empty steps for non-empty cases, environment versions, and derived projections. Old `0.1-p0`/`0.2-p4` traces remain readable and are labeled legacy; they cannot satisfy the new StepResult evidence contract or be treated as verified evidence.

7. **Rich text is fail-closed.** Resolver output may carry a real fragment/semantic-action target and bounds. An aggregate Text node with only concatenated content has no addressable target and raises `inline_target_unresolvable`; the implementation never clicks a parent center or estimates a character range. A deterministic fixture models ordinary and clickable spans collapsed into one dump Text node.

8. **CLI and MCP reuse the same dispatcher.** Plan rows, `run --steps-file`, CLI atomic planned commands, and MCP tools all call `dispatch_planned_step` or the shared runner/report functions. The wrappers only parse/serialize arguments; they do not define selector or verdict semantics.

## Risks / Trade-offs

- [Behavioral break] Cases that previously passed without assertions or after a false wait may become failed/inconclusive. → Document the intentional change, retain legacy status projection, and add migration guidance.
- [Hypium variance] Different Hypium versions may return different timeout/unsupported exceptions or Toast result shapes. → Preserve raw exception/return evidence in diagnostics, classify only known capability signals, and keep unsupported vs assertion mismatch separate; do not silently broaden matching.
- [Timing] Toasts can be shorter-lived than a later assertion step. → Start listening before the trigger when the runner can pair adjacent steps and retain the adapter polling window; record channel and event result.
- [Consumer drift] Existing report readers may expect only `cases[].status` and `tool_calls`. → Keep compatibility fields, derive the old projection from the new ledger, and version the trace schema.
- [Fake confidence] Offline fakes cannot prove a real ArkUI/Hypium chain. → Label fake artifacts, add a fixture for the fail-closed rich-text shape, and publish a pending real-device checklist rather than claiming device acceptance.

## Migration Plan

1. Land the OpenSpec delta and contracts before implementation.
2. Implement the ledger and projections, then adapter and selector behavior in narrow testable batches.
3. Update plan/steps/CLI/MCP tests and documentation; old traces are read as legacy only.
4. Run targeted tests, the full suite, strict OpenSpec validation, and source-release build/verify.
5. Recommend a semver patch/minor release according to the final compatibility impact; do not publish it. Downstream copies `dist/release-src/src` and the manifest, verifies the tree hash, and updates its minimum version/schema gates.

Rollback of production code is a normal source rollback, but old artifacts must not be relabeled as new evidence. If Hypium behavior conflicts with the requirement, retain the raw fixture/exception and mark the affected real-device check pending instead of adding a silent fallback.

## Open Questions

- The exact Hypium package version string and native `MatchPattern` object shape are available only when the optional device dependency is installed; the adapter will introspect the exported enum/constants while tests provide a deterministic shim.
- Whether the connected test device exposes fragment-level ArkUI Span bounds is a real-device validation item, not a blocker for the fail-closed contract or fake fixture.
