# contracts — Step Outcome Protocol v1 / trace schema 0.4-p0

## ADDED Requirements

### Requirement: Result protocol declaration

Every Hylyre output envelope that carries execution results SHALL declare
`result_protocol: "hylyre.step-outcome/1"`: the trace root (and its `environment`),
atomic CLI/MCP responses, `run_steps` batch responses, session daemon responses,
fake/conformance output, and the pre-run reject envelope. Trace `schema_version`
`0.4-p0` and that protocol id are a bound pair.

#### Scenario: 0.4-p0 requires the protocol

- **WHEN** a trace declares `schema_version: "0.4-p0"` without `result_protocol`, or with any other value
- **THEN** schema validation fails

#### Scenario: legacy may not declare the protocol

- **WHEN** a `0.3-p0`, `0.2-p4` or `0.1-p0` trace declares `result_protocol`
- **THEN** schema validation fails, so legacy output can never be mistaken for v1 evidence

### Requirement: Four mutually exclusive step outcomes

`StepResult.outcome` SHALL be a discriminated union over `status`
(`passed | failed | blocked | skipped`) in which each status permits exactly one
carrier and forbids the others: `passed` requires `observation`; `failed` requires
`failure` and may carry `observation`; `blocked` requires `cause`; `skipped` requires
`reason`. `status` SHALL be determined only by whether the step was actually attempted;
`capability` and `infrastructure` are attribution domains and SHALL NOT select a status.

#### Scenario: contradictory carriers are unrepresentable

- **WHEN** a step declares `passed` with a `failure`, `blocked` with a `failure`, `skipped` with an `observation`, or any status without its required carrier
- **THEN** schema validation fails

#### Scenario: assertion outcome and observation agree

- **WHEN** a `passed` step carries an assertion observation with `matched: false`, or a `failed` step carries one with `matched: true`
- **THEN** schema validation fails

#### Scenario: attempted-but-ineffective action stays failed

- **WHEN** a dispatched action resolves zero selector candidates and produces no effect
- **THEN** the step is `failed` with `failure.domain: selector` and MAY carry `observation.performed: false`; it is not converted to `blocked`

### Requirement: failure, cause and reason are separated

`failure` SHALL describe only a failure this step actually experienced and is the only
routable root event. `cause` SHALL describe why an unexecuted step was blocked and
SHALL NOT be routed as this step's failure. `reason` SHALL describe a policy or
not-applicable decision. A root failure's `failure.domain`/`code` SHALL NOT be copied
onto blocked suffix steps.

#### Scenario: blocked suffix points at the root

- **WHEN** a root step fails and the remaining steps of that case are not executed
- **THEN** each remaining step is `blocked` with `cause.type: prior_step` whose `step_index` is the root step's index, carries no `failure`, and produces no failure route

#### Scenario: prior_step chains are rejected

- **WHEN** a `prior_step` cause references a step that is itself `blocked` with `cause.type: prior_step`, references a larger or equal index, or references another case
- **THEN** verification fails

#### Scenario: machine facts back a capability or infrastructure block

- **WHEN** a step is `blocked` with `cause.type: capability` or `infrastructure`
- **THEN** it carries a namespaced `code` and structured `facts.probe_status` + `facts.probe_source`; a `capability` cause additionally carries a non-empty `capability_id`; prose alone cannot drive a defer

### Requirement: StepResult local consistency

Beyond carrier exclusivity, the schema SHALL reject contradictions inside a single
`StepResult`: `role` and `observation.kind` must agree; a `blocked` or `skipped` step
with a non-null `selector` must report `resolution.state: not_attempted`; a `failed`
step carrying an assertion observation with `matched: false` must use
`failure.domain: assertion`; and `contract.empty_case` SHALL NOT be a `failure.code`.

#### Scenario: role and observation must describe the same thing

- **WHEN** a step declares `role: assertion` with an action observation, or `role: action` with an assertion observation
- **THEN** schema validation fails

#### Scenario: an unattempted step reports no resolution

- **WHEN** a `blocked` or `skipped` step carries a selector whose `resolution.state` is `unique`, `not_found`, `ambiguous` or `unresolvable`
- **THEN** schema validation fails

#### Scenario: an evaluated assertion fails as an assertion

- **WHEN** a `failed` step carries an assertion observation with `matched: false` and `failure.domain: selector`
- **THEN** schema validation fails; a selector failure that prevented evaluation carries no assertion observation at all

#### Scenario: an empty case is never a step failure

- **WHEN** a `failed` step declares `failure.code: contract.empty_case`
- **THEN** schema validation fails; that code exists only in the pre-run reject registry

### Requirement: Cross-row rules have an executable oracle

The contract package SHALL ship a normative reference reducer/verifier implementing the
CaseResult reduction, run outcome, `prior_step` root references, `candidate_count`
recomputation, the expected-check policy rule and the `tool_calls` projection. Golden
fixtures SHALL include a bucket of schema-valid traces that this oracle MUST reject, so
that a reducer/verifier which is not running cannot pass silently. The oracle SHALL NOT
create a ledger, sidecar or second source of truth.

#### Scenario: valid traces reduce to their declared axes

- **WHEN** the oracle reduces any `golden/trace/valid/*.json`
- **THEN** the recomputed `execution`, `verification`, `evidence`, legacy status, run outcome and `tool_calls` equal the values the fixture declares

#### Scenario: tampered derivations are caught

- **WHEN** a trace's derived axis, `prior_step` reference, run outcome, `candidate_count` or `tool_calls` projection is tampered with while remaining schema-valid
- **THEN** the oracle reports the violation, and the fixture lives in `golden/trace/invalid-crossrow/`

### Requirement: The shipped report contract is version-dispatched

`report-sections.yaml` SHALL declare the current protocol (`0.4-p0` +
`hylyre.step-outcome/1`) under an explicit `current` key and SHALL confine the legacy
flat failure taxonomy to an explicit `legacy` key marked not evidence-eligible. The
package SHALL NOT present a legacy schema version as the current protocol.

#### Scenario: no parallel SSOT inside the contract package

- **WHEN** a consumer reads the shipped contract directory offline
- **THEN** exactly one declared current protocol is visible, the legacy flat `failure_kind` taxonomy is reachable only under `legacy`, and the machine check fails if the YAML drifts from the schema enums

### Requirement: Registered code planes with explicit extension

The protocol SHALL define four independent code planes — `failure.code`, `cause.code`,
`reason.code`, `resolution.reason_code` — each with a registered core set and an
explicit vendor namespace form. `failure.domain` is a closed enum
(`contract | selector | assertion | capability | infrastructure | internal`) and
`failure.code`'s first segment SHALL equal it. Codes without a namespace SHALL be rejected.

#### Scenario: domain and code prefix must agree

- **WHEN** a failure declares `domain: selector` with `code: assertion.mismatch`, or a bare `code: not_found`
- **THEN** schema validation fails

#### Scenario: the projection obeys the same registries

- **WHEN** a `tool_calls` entry declares a domain/code mismatch, or a `reason.code` outside the registry for its `reason.type`
- **THEN** schema validation fails for the entry and for the whole trace, so a projection can never carry a classification the ledger would reject

#### Scenario: vendor codes stay parseable

- **WHEN** an adapter emits a code outside the core registry
- **THEN** it must carry an `x_<vendor>` namespace segment, and consumers may still route on `domain`/`type` and fail closed

### Requirement: Selector request and resolution are separated

`StepResult.selector` SHALL contain a `request` (plan intent) and a `resolution`
(executor findings). `resolution.state` is `not_attempted | not_found | unique |
ambiguous | unresolvable` with frozen `candidate_count`/`selected`/`candidates`
invariants. `unresolvable` SHALL carry a namespaced `reason_code` and structured facts
(`dump_status`, `request_complete`, `resolver_entered`, `candidate_countable`, plus
fragment/provider clues where applicable).

#### Scenario: a requested id is never reported as selected

- **WHEN** `candidate_count` is `0` and `selected.id` is non-null, or `candidate_count > 1` with a non-null `selected`, or `not_attempted` carries a `candidate_count`
- **THEN** schema validation fails

#### Scenario: uncountable candidates are null, not zero

- **WHEN** `resolution.state` is `unresolvable` with `facts.candidate_countable: false`
- **THEN** `candidate_count` must be `null`; `not_found` may not stand in for an incomplete resolution

#### Scenario: each unresolvable reason names its own evidence

- **WHEN** `reason_code` is a resolver/provider capability gap without `facts.provider_probe`, an inline/fragment miss without both fragment fact keys, or a dump/request reason contradicting `facts.dump_status` / `facts.request_complete`
- **THEN** schema validation fails, so the four unresolvable boundaries stay machine-distinguishable

### Requirement: Failure-boundary screen artifact

A root failure inside an established device session SHALL be backed by screen evidence.
A step that actually attempted a UI action or assertion, ran inside an established
device session, and failed with `failure.domain` `selector` or `assertion` SHALL carry
at least one `screenshot`, `ui_dump` or `visible_elements` artifact, or SHALL record
capture unavailability in the `hylyre.capture` namespaced extension and force
`CaseResult.evidence: incomplete`. Artifacts SHALL NOT be fabricated. The obligation
covers only that failure boundary, at most one artifact group per root failure.

#### Scenario: root failure without evidence is rejected

- **WHEN** a `device_session: true` step fails with `failure.domain: selector` and carries neither a screen artifact nor a capture-unavailable extension
- **THEN** schema validation fails

#### Scenario: obligation does not spread

- **WHEN** a step is `passed`, `blocked`, `skipped`, fails before a device session exists, or fails with a `contract`/`capability`/`infrastructure` domain
- **THEN** no failure-boundary artifact is required

#### Scenario: artifact paths are relative on every platform

- **WHEN** an artifact path is POSIX-absolute, Windows drive-absolute, backslash-rooted, a UNC path, or contains a parent-traversal segment under either separator
- **THEN** schema validation fails

### Requirement: CaseResult and RunResult are pure reductions

`CaseResult` axes SHALL be reduced from `StepResult[]` only: `execution` from attempted/
failed/blocked facts, `verification` from required assertion observations, `evidence`
from required observation/selector/artifact completeness, with `expected_check_mode` as
a policy input and the legacy Chinese `status` as a forward-only projection. Run outcome
SHALL be reduced from `CaseResult`; Markdown, `tool_calls` and pass-rate SHALL NOT write
back into the trace.

#### Scenario: one root failure is one defect

- **WHEN** a case has one root `failed` step, N `blocked/prior_step` steps and a policy-skipped expected check
- **THEN** the case reduces to `execution: aborted`, `verification: failed`, legacy `失败`, exactly one failure route, and the notes summarise "N steps not executed" rather than N defects

### Requirement: tool_calls is a lossy projection

`tool_calls` SHALL keep the same nested `outcome.failure | cause | reason` field names as
`StepResult`, SHALL NOT introduce flat `failure_kind`/status aliases, and SHALL NOT
contain a failure/cause/reason absent from `cases[].steps[]`.

#### Scenario: flat projection is rejected

- **WHEN** a `0.4-p0` trace emits `tool_calls` entries with `status`/`failure_kind`/`failure_code`
- **THEN** schema validation fails

### Requirement: Pre-run contract reject envelope

An empty case or a statically invalid planned step, match or selector SHALL be rejected
before any device is contacted. `hylyre run --plan` and `run --steps-file` report mode
SHALL emit exactly one UTF-8 JSON object on stdout matching the frozen `pre_run_reject`
definition, exit with code `2`, contact no device, and neither create nor rewrite
`--trace-out`/`--report-out`. Human text goes to stderr only and never participates in
classification.

#### Scenario: empty case is rejected, not skipped

- **WHEN** a plan case contains no executable planned step
- **THEN** the whole plan is rejected with `contract.empty_case`; no empty `CaseResult` and no fabricated skipped step is produced

#### Scenario: reject is distinguishable from a crash

- **WHEN** a Hylyre process exits non-zero without producing a trace
- **THEN** consumers first parse the stdout `pre_run_reject`; only a missing, invalid or mismatched envelope falls through to the existing no-trace crash classification

### Requirement: Contract package ships with the release

`hylyre/contracts/` SHALL contain the complete normative protocol
(`step-outcome-v1.md`), the normative builder decision table
(`builder-decision-table.md`), `output-schema.json`, `report-sections.yaml` and
`golden/**`, all declared as package-data so wheel and plain-source installs can read
and validate the protocol offline. `contracts/README.md` SHALL NOT depend on files
outside the shipped package.

#### Scenario: golden fixtures are the shared acceptance set

- **WHEN** the contract package is installed
- **THEN** every `golden/<target>/valid/*.json` validates against its schema node and every `golden/<target>/invalid/*.json` is rejected, and both Hylyre and downstream consumers accept against this same set rather than a synonymous copy

## MODIFIED Requirements

### Requirement: Legacy trace compatibility

The verifier SHALL recognize `0.1-p0`, `0.2-p4` and `0.3-p0` traces as `legacy`,
retain their readable data, and reject treating them as new-schema verified evidence.
Legacy paths SHALL NOT emit `0.4-p0`, SHALL NOT declare `result_protocol`, and SHALL NOT
be converted or field-filled into Step Outcome v1 evidence. Reading entries SHALL
dispatch on `(schema_version, result_protocol)` and fail closed: unknown combinations,
missing protocol fields and unknown future schemas SHALL fail explicitly rather than
returning empty checks, SKIP, Chinese status, flat fields or `tool_calls`.

#### Scenario: legacy stays legacy

- **WHEN** a `0.3-p0` trace is verified
- **THEN** it remains readable but is explicitly reported as legacy/ineligible, and no v1 fields are synthesized for it

#### Scenario: unknown schema fails closed

- **WHEN** a trace declares an unrecognized `schema_version`, or `0.4-p0` with a mismatched protocol
- **THEN** the read entry fails explicitly instead of falling back to legacy parsing

## REMOVED Requirements

### Requirement: Non-passing steps must carry a failure taxonomy

**Reason**: `hylyre/harness/runner.py:151-157` required `failure_kind`/`failure_code`
whenever `status != passed`, forcing unexecuted `blocked` steps and policy `skipped`
steps to fabricate a failure classification. This is the direct cause of one root
failure being amplified into many downstream defects.

**Migration**: `blocked` carries `cause`, `skipped` carries `reason`, and neither carries
`failure`. The rule is deleted rather than renamed or reimplemented elsewhere.
