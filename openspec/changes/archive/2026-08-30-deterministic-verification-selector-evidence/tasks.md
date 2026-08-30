## 1. Result contract and ledger foundation

- [x] 1.1 Add serializable `StepResult`/`CaseResult` models with the frozen fields, enums, legacy status projection, and expected-check modes.
- [x] 1.2 Route every plan and steps-file planned step through one ledger wrapper that records index, role, duration, status, typed failure, selector/evidence, and human error.
- [x] 1.3 Derive `tool_calls` and Markdown case/step details from `CaseResult.steps[]`; remove independent success-only logging as a source of truth.

## 2. Hypium adapter contract

- [x] 2.1 Add shared exact/contains validation and Hypium MatchPattern mapping with explicit effective-match evidence for native text selectors.
- [x] 2.2 Make native wait-for/wait-gone consume Hypium return values and raise stable selector failures with selector and timeout context.
- [x] 2.3 Correct Toast listener/check lifecycle, boolean handling, exception propagation, and capability-versus-assertion classification.
- [x] 2.4 Add adapter-facing failure classification and Hypium version discovery without introducing an import-time device dependency.

## 3. Selector resolution and action safety

- [x] 3.1 Unify resolver/fake/native exact/contains semantics and reject all unsupported match values fail-closed.
- [x] 3.2 Make action resolution require uniqueness, preserve explicit index/scope/within/all disambiguation, and expose candidate summaries/counts.
- [x] 3.3 Apply the same selector semantics to touch, input, wait, wait_gone, scroll_to, swipe areas, and scroll-at selectors; remove first-hit and exact-to-contains fallbacks.
- [x] 3.4 Make aggregate rich-text targets fail closed unless real fragment bounds/semantic action evidence exists, and add the deterministic Span fixture.

## 4. Scenario verdicts and assertions

- [x] 4.1 Compute execution, verification, and evidence independently from the ledger, including action-only, failed assertion, skipped, and all-skipped cases.
- [x] 4.2 Record checked_vlm/disabled_by_flag/unavailable_no_vlm/empty expected-check mode and add expected assertions to the ledger when checked.
- [x] 4.3 Preserve typed StepSkipped behavior and map failure kind/code without making unsupported capability look like assertion mismatch.

## 5. Trace/report contracts

- [x] 5.1 Replace the permissive trace schema with the versioned new CaseResult/StepResult schema, environment fields, uniqueness constraints, and failure/evidence enums.
- [x] 5.2 Extend report emission and verification to enforce case-set, ledger, tool-call, and Markdown projection consistency while recognizing legacy traces explicitly.
- [x] 5.3 Add sensitive evidence redaction at the shared evidence serialization boundary without creating a sidecar.

## 6. CLI, MCP, and session wiring

- [x] 6.1 Keep CLI plan, steps-file, and atomic planned-step commands on the shared dispatcher/result path and preserve failure-dir propagation.
- [x] 6.2 Keep MCP tools as thin delegates to the shared runner/CLI implementation and preserve typed results/evidence through batch and session paths.
- [x] 6.3 Add production-entry conformance regressions for plan, steps-file, CLI, and MCP, including at least one wait/selector/verdict path in each.

## 7. Documentation and release delivery

- [x] 7.1 Update canonical specs from the completed change and document the new trace/ledger, selector, verdict, and Toast contracts.
- [x] 7.2 Add CHANGELOG and legacy trace/test-plan migration guidance, recommend the next 0.x version without publishing it, and document the real-device pending checklist.
- [x] 7.3 Run targeted and full tests, strict OpenSpec validation, build `dist/release-src/`, verify its manifest, and record version/file-count/tree-hash delivery facts.
