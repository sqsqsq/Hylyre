# Proposal: step-outcome-protocol-v1 (Hylyre 0.5.0)

## Why

Hylyre 0.4.1 fixed empty `wait_for`/`wait_gone` assertions, made `CaseResult.steps[]`
the runtime ledger, and stopped redacting structured selector identity. Real-device
integration then proved the remaining problem is not a single wrong failure code but
the **absence of a unified, decidable result protocol** between execution discovery,
result transport, ledger recording, trace persistence and report feedback.

`StepResult` in `0.3-p0` is a flat field bag with no discriminator. It permits — and
the current verifier actively *requires* — mutually contradictory combinations:

```text
status=blocked + evidence.executed=false + failure_kind=selector
status=skipped + expected_check_mode=disabled_by_flag + failure_kind=capability
candidate_count=0 + selected_id=<requested id>
role=assertion + observed_present=false + failure_kind=selector
```

One real root failure was amplified into 56 selector failures and 14 capability defers
downstream. `hylyre/harness/runner.py:151-157` (`status != passed → failure_kind/failure_code`
required) is the rule that forces unexecuted `blocked` and policy `skipped` steps to
fabricate a failure taxonomy.

## What Changes

Introduce **Step Outcome Protocol v1** (`hylyre.step-outcome/1`), bound to trace schema
`0.4-p0`, delivered in two phases with **one** released runtime version (0.5.0).

### Phase 0 — contract freeze (this change, implemented)

- `hylyre/contracts/step-outcome-v1.md`: normative protocol (four mutually exclusive
  outcomes, `failure`/`cause`/`reason` separation, four code registries, selector
  request/resolution split, artifacts + failure boundary, reducer rules, `pre_run_reject`,
  legacy fail-closed dispatch, responsibility split).
- `hylyre/contracts/builder-decision-table.md`: normative execution-fact → `StepResult`
  mapping (37 decision rows + 5 reducer rows), each row bound to a golden fixture.
- `hylyre/contracts/output-schema.json`: `0.4-p0` trace with `oneOf`/discriminator
  variants; reusable `stepResultV1` node; frozen `pre_run_reject` definition; legacy
  `0.3-p0`/`0.2-p4`/`0.1-p0` retained read-only and forbidden from declaring the protocol.
- `hylyre/contracts/golden/**`: 172 fixtures (84 positive, 88 negative) across 12 schema nodes.
- `hylyre/scenario/plan_contract.py` + CLI wiring: pre-run contract reject (P0-7B).
- `scripts/verify_contracts.py`, `tests/schema/test_step_outcome_contract.py`,
  `tests/unit/test_pre_run_reject.py`: machine proof of the freeze.

### Phase 1 — real implementation (not in this change yet)

Single transient `OperationOutcome` tagged union, one `OperationOutcome → StepResult`
builder shared by real plan / native+resolver / fake / steps-file+batch / atomic CLI /
MCP / session, pure `CaseResult`/`RunResult` reducers, verifier owning cross-row rules,
deletion of the `status != passed → failure` rule, legacy isolation, version 0.5.0 and
release assets.

## Capabilities

### Modified Capabilities

- `contracts`: Step Outcome Protocol v1, `0.4-p0` trace schema, `pre_run_reject` envelope,
  golden fixture package, protocol/schema fail-closed dispatch.
- `cli`: `hylyre run --plan` / `--steps-file` report mode emit a structured pre-run
  contract reject (single stdout JSON, exit `2`, zero device calls, no artifact write).

## Out of scope

- A second persisted ledger, sidecar, selector ledger or failure event log.
- Pushing Maison coverage/owner/release verdicts into Hylyre.
- Classifying by parsing `error`/`diagnostic` text.
- Changing exact/contains, OCR, coordinate estimation or rich-text tap strategy.
- Reverting the 0.4.1 selector identity privacy fix.
- A `0.3-p0` migration tool or full read compatibility.
- A second persisted envelope for pre-trace Python crashes (the existing subprocess
  stdout/stderr crash classifier remains the no-trace fallback).

## Versioning

Phase 0 is **not** a release: no version bump, no host install, no runtime evidence.
Phase 1 releases **0.5.0** (breaking result-protocol + trace-schema change; not a 0.4.2 patch).
