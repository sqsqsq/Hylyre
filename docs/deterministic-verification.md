# Deterministic verification and evidence contract

Hylyre 0.4.1 is the current deterministic execution and evidence layer. It preserves structured selector identity fields for machine comparison while continuing to redact user-facing text and values. Maison remains responsible for acceptance coverage, P0/quality axes, visual checks, and release verdicts.

## One evidence chain

Every plan or steps-file operation follows this chain:

`planned step → StepResult → CaseResult.steps[] → trace.json → Markdown/tool_calls projection`

`CaseResult.steps[]` is the only runtime evidence source. `tool_calls` and the Markdown `步骤证据` table are generated projections; there is no selector ledger, Toast sidecar, or step-evidence sidecar.

The new trace schema is `0.3-p0`. A case retains `id`, `priority`, `ac_ref`, `notes`, and the legacy Chinese `status`, and adds:

```json
{
  "execution": "completed|aborted|infrastructure_failed",
  "verification": "passed|failed|inconclusive",
  "evidence": "complete|incomplete",
  "expected_check_mode": "checked_vlm|disabled_by_flag|unavailable_no_vlm|empty",
  "steps": [
    {
      "index": 0,
      "kind": "touch",
      "role": "action|assertion",
      "status": "passed|failed|blocked|skipped",
      "failure_kind": null,
      "failure_code": null,
      "duration_ms": 12.3,
      "selector": null,
      "evidence": {"operation": "touch"},
      "error": null
    }
  ]
}
```

`failure_kind` is one of `assertion`, `selector`, `capability`, and `infrastructure`. Machine consumers use `failure_code` before human `error`: `assertion_mismatch`, `selector_not_found`, `selector_ambiguous`, `inline_target_unresolvable`, `capability_unsupported`, `device_unavailable`, and `driver_failure`. Invalid `match` values are selector failures using the existing `selector_not_found` code; the frozen interface is not extended.

## Verdict rules

`verification=passed` requires completed execution, at least one actually executed passing assertion (or a passing VLM expected check), every required assertion passing, and non-empty evidence for each passing assertion. A passing `assert_toast` additionally requires `evidence.trigger_window_covered=true`; an assertion-only Toast is explicit non-verifying evidence. An aborted/infrastructure-failed case, a case with a skipped/blocked required assertion, an action-only case (`execution=completed / verification=inconclusive`), and an all-skipped case cannot project to legacy `通过`. A capability skip is recorded as `skipped` or `blocked` with `failure_kind=capability` and is never an assertion mismatch.

## Selector rules

Only `exact` and `contains` are supported. An omitted `match` is explicitly recorded as `requested_match=null, effective_match=contains`. `starts_with`, `ends_with`, `regex`, and arbitrary spellings fail closed as `selector_not_found`. The same contract is used by touch, input, wait, wait-gone, scroll-to, swipe-area, scroll-at, native Hypium selectors, resolver, and fakes. Action selectors—including swipe/scroll containers—require one candidate; use the existing `index`, `scope`, `within`, or `all` fields to disambiguate. Nested selectors are validated before search; a missing overlay or relative anchor is not treated as unconstrained.

Aggregate rich text is not clickable evidence. Because a normal dynamic Row and a flattened rich-text Row can be identical in a dump, Hylyre does not infer inline intent from Row/Button ancestry. A host must provide `inline_target=true` on the aggregate Text node or expose real fragment bounds/semantic action; with that contract signal but no independent target, Hylyre returns `inline_target_unresolvable` and does not click a parent center or estimate a character coordinate. This also applies when the `by_text` predicate is nested in `all[]`. Without the signal, ordinary Text/Row `contains` remains ordinary contains semantics. Real fragment bounds are recorded under `evidence.resolution_kind` and `fragment_bounds`, but a successful action still needs a planned post-action assertion.

## Wait and Toast

Hypium wait adapters consume the documented return contracts: `wait_for_component` must return a component, while `wait_for_component_disappear` must return `None`. Errors include the selector and timeout. Toast plans/batches start listening before the trigger action; `check_toast` must return boolean true. False/not-found is `assertion_mismatch`; recognized unsupported capability is `capability_unsupported` or a typed skip when `on_unsupported=skip`. A standalone atomic CLI/MCP `assert_toast` has no trigger action to bracket: its evidence records `trigger_window=assertion_only` and `trigger_window_covered=false`; use an adjacent trigger + Toast assertion in a plan or `run_steps` for trigger-window coverage.

Trace `environment` records Hylyre version, Hypium version or `unavailable`, trace schema version, and selector engine. New-schema selector objects require `engine`, `requested_match`, `effective_match`, and `candidate_count`; nested `all[]` text match is the recorded effective match. Verifier checks case/step uniqueness and projection equality. Schema `0.1-p0`/`0.2-p4` is explicitly labeled `legacy` and is readable only as compatibility data, not new StepResult evidence. Structured selector identity fields (`by_id`, `by_key`, `id`, `key`, `selected_id`) are retained verbatim; evidence values likely to contain account, amount, credential, selector text, human error, or notes are redacted at serialization.

The deterministic aggregate-rich-text fixture is [`tests/fixtures/rich_text_aggregate_dump.json`](../tests/fixtures/rich_text_aggregate_dump.json). It models ordinary and clickable conceptual spans while the host dump contains only one aggregate Text node and the explicit `inline_target=true` host signal; the resolver must return `inline_target_unresolvable` and issue no parent-center touch. The paired regression covers an ordinary dynamic Row `contains` without that signal. This fixture is not a real ArkUI device acceptance.

## Real-device boundary

Fake and adapter tests prove the contract only. The following remain pending until a connected OpenHarmony device is run:

- `wait_for` present and missing target;
- `wait_gone` absent and present target;
- Toast present, not present, and capability unsupported;
- native/resolver `exact` and `contains` parity;
- action ambiguity plus explicit `index`/scope/within/all disambiguation;
- aggregate rich-text fail-closed behavior and no parent Text/Row center click;
- actual StepResult and trace disk artifacts emitted from Hypium.

No fake or unit result is labeled as real-device acceptance.
