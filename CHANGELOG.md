# Changelog

## 0.5.0 — Step Outcome Protocol v1 (breaking)

**Breaking**: trace schema `0.3-p0` → `0.4-p0`, and every result envelope now
declares `result_protocol: "hylyre.step-outcome/1"`. Consumers must dispatch on
`(schema_version, result_protocol)`; see [`docs/migration-0.5.md`](docs/migration-0.5.md).

The flat `StepResult` had no discriminator, so it permitted — and the verifier
actively required — contradictory rows (`blocked` carrying a `failure`,
`candidate_count=0` with a `selected_id`, `role=assertion` with a selector
failure). One real root failure was amplified into 56 downstream defects.

- `outcome` is a discriminated union: `passed` carries an observation, `failed`
  a failure, `blocked` a cause, `skipped` a reason. Nothing carries two.
- `status` is decided only by whether a step was **attempted**. `capability` and
  `infrastructure` are attribution domains: found before dispatch they block,
  found after dispatch they fail.
- A blocked suffix points at the root step with `cause.type=prior_step` and no
  longer inherits the root's failure classification.
- `selector` splits into `request` (plan intent) and `resolution` (what the
  executor found), so a requested id is never reported as a resolved one.
- `failure`/`cause`/`reason`/`resolution.reason_code` are four namespaced code
  registries; unnamespaced codes and domain/code prefix conflicts are rejected.
- A root selector/assertion failure inside a live device session must carry a
  screenshot or UI dump, with a real sha256; capture is never faked.
- `CaseResult`/`RunResult`/`tool_calls` are reduced from `steps[]` by the
  reducer shipped in the contract package, so Hylyre and its consumers cannot
  drift. `tool_calls` keeps the nested outcome shape; no flat `failure_kind`.
- **Removed**: the `status != passed → failure_kind/failure_code` rule that
  forced unexecuted and policy-skipped steps to fabricate a failure taxonomy.
- Empty cases and statically invalid steps are rejected before any device call
  with a single stdout JSON object and exit code `2`.
- Every entry (plan, fake, steps-file/batch, atomic CLI, MCP, session) builds
  rows through one builder; the offline stub no longer hand-assembles rows and
  no longer reports assertions it cannot observe.
- `run --steps-file` / `--steps` honour `--use-fakes` through the same stub
  outcome decision as the plan runner. The flag was previously accepted and
  ignored on that path, so an offline smoke test silently connected to the
  first available device; `--use-fakes` with `--session` is now refused rather
  than silently resolved.
- Contract package (`hylyre/contracts/`) ships the schema, the normative spec,
  the builder decision table, the reference reducer and 218 golden fixtures, all
  readable offline. `build_wheel.py --contracts` produces a non-installable
  contract-freeze bundle.

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
