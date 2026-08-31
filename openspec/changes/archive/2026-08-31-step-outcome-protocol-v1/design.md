# Design notes: step-outcome-protocol-v1

## 1. Why a discriminated union instead of more failure codes

`0.3-p0` `StepResult` is a flat record whose fields are independently settable, so the
verifier had to reconstruct semantics with cross-field Python rules — and got one of
them wrong (`status != passed → failure_kind/failure_code` required). v1 moves the
discriminator into the data: `outcome.status` selects exactly one carrier
(`observation` / `failure` / `cause` / `reason`) and JSON Schema `oneOf` +
`additionalProperties: false` makes every other combination **unrepresentable**.

Consequence: the Python verifier stops duplicating structural validation and keeps only
what Schema provably cannot express — cross-row `prior_step` references, `CaseResult`
recomputation, `candidate_count` recomputation and projection consistency.

## 2. `attempted` is the only status input

`capability` and `infrastructure` are *reason domains*, not statuses. The same domain
lands on `failed` or `blocked` purely by whether the operation entered a real adapter
attempt:

| discovery point | status | carrier |
|---|---|---|
| after dispatch | `failed` | `failure.domain=capability\|infrastructure` |
| before dispatch, proven by machine probe | `blocked` | `cause.type=capability\|infrastructure` |

This is what lets `performed=false + failed` be legal (a selector that resolved to zero
candidates *was* attempted) while forbidding a non-dispatched `blocked` from faking a
`performed=false` action observation.

## 3. Interpretation decisions (all three ACCEPTED, 2026-08-31)

Two independent Phase 0 reviews ran the counter-examples themselves and accepted D-1, D-2
and O-1 unchanged. The rationale below is retained as the record of why.

D-1 and D-2 are **tightenings**, chosen so the requirement's own rules become mechanically
checkable. Neither changes what a conforming producer may report about a real run.
O-1 is a scope boundary, not a tightening.

### D-1 — `blocked` / `skipped` carry no `observation` at all

The requirement (§5.1) forbids "failure / **successful** observation" on `blocked` and
`skipped`. "Successful" is a semantic predicate JSON Schema cannot evaluate. The
requirement also (P0-7A) forbids a non-dispatched `blocked` from fabricating a
`performed=false` observation, and every machine fact a `blocked`/`skipped` row needs is
already carried by `cause.facts` / `reason.facts`. The schema therefore forbids
`observation` on both, which satisfies the prohibition strictly and leaves no gap.

**Residual risk**: if a future adapter genuinely observes something *while* deciding not
to attempt, it must use a namespaced extension until the protocol version changes.

**Verdict**: accepted. No legal expressive power is lost; the tightening is what makes the
illegal combination unrepresentable, which is the point of the requirement.

### D-2 — new core envelope field `device_session: boolean`

§5.2 and P0-11 require the JSON Schema to enforce the failure-boundary screen artifact
for "a root failure actually attempted inside an established device session". The
envelope sketched in §5.2 contains no field from which a **single object** can decide
whether a device session existed, so the rule would silently degrade into prose.

One boolean is added to the envelope. The rule becomes local and decidable:

```text
device_session=true AND status=failed AND failure.domain ∈ {selector, assertion}
  ⇒ artifacts contains screenshot|ui_dump|visible_elements
     OR extensions["hylyre.capture"].screen == "unavailable"
```

The capture-unavailable escape hatch uses the namespaced extension the requirement
explicitly permits, and forces `CaseResult.evidence=incomplete` via the reducer.

**Alternative rejected**: requiring `observation.facts.failure_boundary_capture` would
have made `observation` mandatory on every `failed/selector|assertion` step, a larger
change to the frozen `failed` variant. Degrading the rule to a verifier check is also
impossible: the fact is not serialized, so a verifier cannot recompute it from a trace.

**Verdict**: accepted, with a Phase 1 acceptance point — the builder must populate
`device_session` from real machine facts, never a hard-coded constant.

## 4. Code namespacing

Every one of the four code planes must "reject codes without a namespace" while staying
extensible without a closed mega-enum. The rule adopted:

```text
failure.code            <domain>.<name>            core   |  <domain>.x_<vendor>.<name>
cause.code              capability|infrastructure.<name>  |  <type>.x_<vendor>.<name>
reason.code             <group>.<name>             core   |  x_<vendor>.<name>
resolution.reason_code  selector.<name>            core   |  selector.x_<vendor>.<name>
```

`failure.code`'s first segment must equal `failure.domain`, enforced by six `if/then`
branches, so a `domain`/`code` prefix conflict fails schema validation. Core codes are a
closed enum today; vendor codes need the explicit `x_<vendor>` segment. Consumers route
on `domain`/`type` first, so an unknown code still fails closed without a consumer upgrade.

## 5. Pre-run reject is protocol, not crash

`contract.empty_case` and statically invalid steps/match/selector have no legal
`StepResult` to carry them, so they cannot become a case row — but they are also not a
crash. `hylyre/scenario/plan_contract.py` validates before any agent is constructed and
returns the **first** violation in stable order; the CLI writes exactly one stdout JSON
object and exits `2`, leaving `--report-out`/`--trace-out` untouched.

Plan-file parse errors (`No 测试用例清单 table`) deliberately keep their existing
non-protocol handling: no registered `contract.*` code covers "the plan file itself is
unreadable", and inventing one would extend the frozen registry (**O-1, accepted**).
A consequence both sides must know: **exit code 2 alone is not a reject signal** — a
malformed steps file also exits 2 with no envelope. The `pre_run_reject` envelope, not
the exit code, is what distinguishes a plan contract reject from the crash fallback.

## 7. What review round 1 changed (2026-08-31)

Two independent reviews accepted the three decisions but found real gaps. Every fix below
is a tightening or added coverage; none altered a frozen semantic.

| Finding | Fix |
|---|---|
| StepResult still admitted `role=assertion` + action observation, `blocked` + resolved selector, assertion `matched=false` + `failure.domain=selector`, and `contract.empty_case` as a step failure | Four local `allOf` rules in `stepResultV1`; `contract.empty_case` moved to its own pre-run reject registry |
| `tool_calls` bypassed the domain/code and reason registries | Extracted `domainCodeAgreement`; the projection now `$ref`s the same registries as the ledger |
| `unresolvable` accepted any facts regardless of `reason_code` | Conditional facts per `reason_code` (provider probe / fragment keys / dump_status / request_complete) |
| Conformance echoed the fixtures' self-declared axes instead of reducing them | `contracts/reference_reducer.py` implements sections 9 and 12; a third fixture bucket `trace/invalid-crossrow/` holds 12 schema-valid traces the oracle must reject |
| Artifact path guard only understood `/` | Regex rejects Windows drive-absolute, backslash-rooted, UNC and backslash traversal |
| `report-sections.yaml` still declared `0.3-p0` as current inside the "SSOT" package | Version-dispatched into `current` / `legacy`, with a drift check wired into the gate |
| `--steps-file` report mode had no end-to-end reject regression | Full CLI-level suite mirroring the `--plan` one |

The third fixture bucket is the structurally important one: cross-row rules are exactly
what a schema cannot express, so without traces that are *legal per-object but illegal as
a set*, a reducer that never runs would still show green.

## 6. Golden fixtures carry the expectation in the path

`golden/<target>/valid/*.json` must pass `GOLDEN_TARGETS[<target>]`;
`golden/<target>/invalid/*.json` must be rejected by it. Directory convention replaces a
runtime fixture manifest (explicitly out of scope), and the decision table's `fixture`
column is cross-checked against the actual outcome/status/code in each file, so the
spec, the table, the schema and the samples cannot drift apart silently.
