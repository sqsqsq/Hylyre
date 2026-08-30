## Context

The existing deterministic-verification implementation already has a shared `StepResult` ledger and a versioned trace, but adversarial paths still bypass those contracts. In particular, verdicts are too permissive, selector constraints are not validated uniformly across all action roots, Toast capability handling can abort before the planned assertion, and the harness validates a weaker shape than the producer emits. The downstream consumer needs one deterministic, auditable result chain and the frozen failure taxonomy must remain compatible.

## Goals / Non-Goals

**Goals:**

- Make `CaseResult.steps[]` complete and authoritative for execution, verification, evidence, reports, and `tool_calls`.
- Require completed execution, passing required assertions, and non-empty evidence before a verified pass.
- Apply exact/contains, recursive constraint validation, uniqueness, and fail-closed behavior consistently to native, resolver, fake, wait, touch, input, swipe, scroll, and scroll-to paths.
- Observe Toast across the trigger window while preserving the distinction between capability unsupported, assertion mismatch, and ordinary driver failure.
- Enforce the current trace schema and make legacy compatibility explicit without rewriting old artifacts.
- Redact sensitive selector and human-facing text fields before trace or Markdown emission.

**Non-Goals:**

- No Maison changes, vendor synchronization, PyPI publication, or real-device acceptance claim.
- No new assertion verbs, selector match modes, OCR, glyph-layout inference, selector ledger, evidence sidecar, or second case status model.
- No new frozen failure-code enum member; invalid match remains selector-classified with the existing `selector_not_found` code.

## Decisions

1. **Central verdict and outcome functions.** Keep verdict computation in the result model and expose one outcome helper consumed by both runtime and harness. This removes the pass-first runtime/harness divergence. A separate status engine or report-side recomputation is rejected because it would recreate the evidence split.

2. **Blocked rows for unexecuted plan suffixes.** When abort-on-failure stops execution, append typed `blocked` rows for every remaining planned step. The runner will also append a planned expected-check row when expected text exists, so configured checks are auditable even if execution prevents them. A sidecar ledger is rejected because `CaseResult.steps[]` is the required source of truth.

3. **Preflight every selector-bearing action.** Resolver-backed preflight must prove zero/one/many before native swipe, scroll, and scroll-to calls. Native drivers remain responsible for native execution and MatchPattern mapping, but may not silently choose a first hit. Overlay and relative-anchor constraints are predicates, not optional hints; empty constraint results fail closed.

4. **Explicit rich-text metadata.** Ordinary Text nodes continue to support normal contains matching. Inline protection is activated only by explicit aggregate/rich-text metadata or fragment semantics. A fragment is clickable only when its dump explicitly says so or supplies a semantic action and valid independent bounds; default-clickable fragments and proportional coordinate estimates are rejected.

5. **Toast lookahead with typed skip.** Plan and batch runners inspect the next planned Toast assertion before starting a trigger listener. If listener capability is unsupported and that assertion requests `on_unsupported: skip`, execute the trigger, then append a skipped capability assertion row with evidence. Otherwise retain a blocked capability failure and block the suffix. Atomic assertions cannot retroactively cover an earlier action; their output must state the limitation rather than inventing a successful observation.

6. **Strict producer/consumer schema.** New traces require selector evidence keys (`engine`, `requested_match`, `effective_match`, `candidate_count`) whenever a selector object is present, require non-empty evidence for passing assertions, and validate unique IDs/indexes and derived projections. Legacy schemas remain readable but are labeled legacy and are not eligible for new StepResult evidence claims.

7. **Field-aware redaction.** Redaction is applied recursively to sensitive selector keys and to `error`/`notes` text before serialization. Machine fields such as failure kind/code and selector match metadata remain stable; human text is deliberately non-authoritative and may be masked.

## Risks / Trade-offs

- [Risk] Existing callers that relied on first-hit selection or framework no-throw behavior will now receive typed failures. → Keep the compatibility `status` projection, document the intentional behavior change, and add explicit regression coverage.
- [Risk] A configured VLM expected check that is blocked cannot truthfully be called executed. → Record the frozen mode selected (`checked_vlm`) plus a blocked expected-check StepResult; verdict computation requires that row to pass before verification can pass.
- [Risk] Toast listener support varies by Hypium/device version. → Preserve raw exception/boolean evidence, classify unsupported capability separately, and leave real-device cases pending until executed.
- [Risk] Redaction can remove useful human diagnostics. → Keep structured failure fields, candidate counts, bounds, and resolution classifications intact; only sensitive text values and human prose are masked.

## Migration Plan

1. Validate this change and update canonical specs after implementation.
2. Run targeted selector, Toast, verdict, ledger, schema, CLI, and MCP regressions, then the complete test suite.
3. Build and verify `dist/release-src`, recording its manifest values.
4. Consumers identify traces with schema `0.1-p0`/`0.2-p4` as legacy; only `0.3-p0` traces with complete steps are eligible for new evidence claims.
5. Recommend the next Hylyre patch/minor version according to the repository's 0.x policy; do not publish it in this change.

