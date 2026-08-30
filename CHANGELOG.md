# Changelog

## 0.4.1 — structured selector identity redaction

- Preserved `by_id`, `by_key`, `id`, `key`, and `selected_id` verbatim in serialized selector evidence, including failure candidates.
- Kept user-facing text and value fields, including `expected` and `actual`, behind the existing redaction boundary.
- Kept trace schema `0.3-p0` and the existing `StepResult`/`CaseResult` field sets unchanged.

## 0.4.0 — deterministic verification and evidence

This release is intentionally behavior-tightening and is not published by this repository change.

- Added the single `CaseResult.steps[]` → trace/report evidence chain with `StepResult` roles, durations, typed failures, selector evidence, assertion evidence, and explicit `expected_check_mode`.
- Split execution, verification, and evidence verdicts; action-only cases are `completed/inconclusive` and all-skipped runs are not successful.
- Corrected Hypium wait return-value handling and Toast listener/boolean handling; unsupported capability is separate from an assertion mismatch.
- Unified selector `exact`/`contains` semantics, rejected invalid modes, made action ambiguity fail closed, and removed native/first-hit/coordinate-estimation fallbacks.
- Added deterministic aggregate-rich-text fail-closed coverage and a real-fragment evidence path.
- Added strict trace/report validation and legacy `0.1-p0`/`0.2-p4` recognition.
- Hardened review cases: aborted/skipped/empty-evidence cases cannot verify, aborts retain blocked ledger rows, and runtime/harness outcomes share one projection algorithm.
- Made nested selectors and swipe/scroll containers fail closed, kept invalid match on frozen `selector_not_found`, and corrected ordinary Text/Span rich-text semantics.
- Toast plan/batch lookahead now preserves the trigger on capability skip; selector/error/notes text is redacted before trace/report output; legacy verification output is explicit.
- Added production-dispatcher conformance coverage for real plan, CLI steps-file, and MCP session-batch paths.
- Final review hardening: uncovered Toast assertions cannot verify, explicitly identified aggregate Text and nested `all[]` targets fail closed, nested match evidence follows actual execution, scoped scroll-to uses the selected container node, and blocked suffixes preserve root classification without inflating `executed`.
- Final inline contract: removed Row/ancestor heuristics that rejected normal dynamic `contains`; flattened rich text now requires host `inline_target=true` or independent fragment/semantic target data before fail-closed handling.

See [docs/migration-0.4.md](docs/migration-0.4.md) for migration details and the pending real-device checklist.
