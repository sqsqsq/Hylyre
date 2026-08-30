## 1. Result model and ledger

- [x] 1.1 Harden `case_verdict` and compatibility status so aborted/infrastructure execution, skipped/blocked required assertions, and empty evidence cannot produce verified pass.
- [x] 1.2 Add complete blocked-suffix and expected-check ledger rows for runner and steps-file execution, and centralize runtime/harness outcome projection.
- [x] 1.3 Apply field-aware redaction to selector predicates, human errors, notes, and evidence before trace/report serialization.

## 2. Selector and driver behavior

- [x] 2.1 Validate nested selectors, `all`, overlay scope, relative anchors, and exact/contains fail-closed semantics in the pure resolver.
- [x] 2.2 Correct rich-text metadata/fragment clickability and preflight unique selector-bearing swipe, scroll, and scroll-to containers.
- [x] 2.3 Preserve native MatchPattern and wait/Toast return semantics while mapping invalid match to the frozen failure taxonomy.
- [x] 2.4 Implement Toast trigger-window lookahead and typed unsupported skip in plan and batch execution.

## 3. Contract and entry-point verification

- [x] 3.1 Tighten output schema and verifier checks for selector evidence, unique identities, derived projections, and legacy labeling.
- [x] 3.2 Add production-dispatcher conformance tests for plan, steps-file, CLI, and MCP paths, including the review regressions.

## 4. Specifications and delivery

- [x] 4.1 Update canonical OpenSpec specifications and implementation documentation with the hardened semantics and migration notes.
- [x] 4.2 Run targeted tests, strict OpenSpec validation, full pytest, and release-source build/verification.
- [x] 4.3 Record release manifest values, recommended version, and pending real-device revalidation checklist without claiming device acceptance.
