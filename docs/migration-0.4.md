# Migration to Hylyre 0.4.0

0.4.0 is the recommended next version because the change tightens observable behavior across the 0.x API and prevents historical false passes. It is a minor-version recommendation under the repository's 0.x policy; no package is published as part of this change.

## Consumers

- Require Hylyre `>=0.4.0` and trace schema `0.3-p0` before consuming verification evidence.
- Read `cases[].steps[]` as the source of truth. `tool_calls` is only a compatibility projection and must not be maintained separately.
- Route first on `failure_kind`, then on `failure_code`; do not parse `error`.
- Treat `verification=inconclusive` and `evidence=incomplete` as not verified. Do not turn `unavailable_no_vlm` or `disabled_by_flag` into a checked expected result.
- Recompile plans with explicit `match` values and existing `index`/`scope`/`within`/`all` disambiguators where needed. Hylyre does not widen exact to contains or choose the first candidate.
- Invalid match values, including `starts_with` and typos, use the frozen selector failure code `selector_not_found`; no separate invalid-match code is part of the interface.
- An abort-on-failure ledger contains `blocked` rows for the unexecuted suffix. A non-empty expected column with an available VLM remains `expected_check_mode=checked_vlm` even when the expected check is blocked; the expected-check StepResult records that fact.
- Passing assertions require a non-empty evidence object. A skipped/blocked required assertion or aborted execution prevents `verification=passed`, even if an earlier assertion passed.
- A Toast operation with `trigger_window_covered=false` is not a verifying assertion; put the trigger immediately before the Toast assertion in a plan or batch.
- Normal dynamic Text/Row `contains` is preserved. Hosts that need flattened rich-text protection must provide the explicit `inline_target=true` Text contract signal or independent fragment/semantic anchor; nested `all[].by_text` follows the same contract and its own match mode in execution/evidence.
- Blocked suffix rows retain the root failure kind/code for causal routing, while batch `executed` counts dispatched operations only; blocked rows remain in `results[]` for audit.

## Legacy artifacts

Trace schema `0.1-p0` and `0.2-p4` remain readable and are labeled `legacy trace; readable compatibility only, not new StepResult evidence` by `verify_report` CLI/MCP output. They may retain old `status` and `tool_calls`, but the absence of a complete `steps[]` ledger means they are not eligible as new verification evidence. Historical false passes are not rewritten or deleted.

Old plans continue to parse. Plans that relied on an omitted native exact default, silent contains fallback, first-candidate action, parent-center rich-text tap, or no expected assertion must be updated explicitly. A plan can keep a human-readable or VLM expected column, but its resulting mode is recorded as `checked_vlm`, `disabled_by_flag`, `unavailable_no_vlm`, or `empty`.

For Toast, place the triggering action immediately before the Toast assertion in a plan or `run_steps` batch so the runner can pre-listen. An atomic CLI/MCP `assert_toast` has no prior trigger to bracket and records `trigger_window_covered=false`; it must not be used as evidence that an earlier atomic action produced a Toast. Unsupported capability with `on_unsupported=skip` is a typed skipped assertion; a supported false/not-found result is an assertion mismatch.

Trace/report and batch human text is redacted for selector text, account/amount-like values, errors, and notes. Consumers must use the structured selector fields and failure codes for diagnostics.

## Handoff and real-device checklist

Maison copies `dist/release-src/src/` and `release.manifest.json`, verifies the manifest tree hash, and aligns its minimum Hylyre version and trace schema before consuming the artifacts. The host must then run, and separately record, the pending real-device cases listed in [docs/deterministic-verification.md](deterministic-verification.md); fake results must not be relabeled as device acceptance.
