# Tasks: step-outcome-protocol-v1

## Phase 0 — contract freeze (no release, no version bump, no host install)

### 1. Contract assets

- [x] `hylyre/contracts/output-schema.json`: `0.4-p0` trace, `result_protocol` binding,
      `oneOf` outcome/cause/reason/observation/resolution variants, reusable
      `stepResultV1`, `toolCallV1`, `caseResultV1`, frozen `pre_run_reject`; legacy
      `0.3-p0`/`0.2-p4`/`0.1-p0` retained read-only and barred from declaring the protocol.
- [x] `hylyre/contracts/step-outcome-v1.md`: normative protocol spec (envelope, four
      outcomes, attempted semantics, failure/cause/reason split, four code registries and
      extension rules, observation facts, selector request/resolution + unresolvable facts,
      artifacts + failure boundary, CaseResult/RunResult reduction, extensions, pre-run
      reject, `tool_calls` projection, responsibility split, legacy fail-closed dispatch).
- [x] `hylyre/contracts/builder-decision-table.md`: 37 normative decision rows + 5 reducer
      rows, each bound to a golden fixture; single-builder wiring list; layered conformance.
- [x] `hylyre/contracts/golden/**`: 172 fixtures over 12 schema nodes (84 positive / 88 negative).
- [x] `hylyre/contracts/__init__.py`: offline schema/subschema loading (`validate_against`).
- [x] `hylyre/contracts/README.md`: self-contained; no reference to unshipped `docs/`.
- [x] `pyproject.toml`: `golden/**/*.json` declared as package-data.

### 2. Minimal production surface required by the Phase 0 machine proof

- [x] `hylyre/scenario/plan_contract.py`: pre-run plan/steps contract validation,
      first-violation-in-stable-order, `pre_run_reject` envelope builder.
- [x] `hylyre/cli/commands/run_cmd.py`: `emit_pre_run_reject` / `reject_plan_before_run` /
      `reject_steps_before_run`.
- [x] `hylyre/cli/__main__.py`: reject wired before agent construction and before any
      report/trace write, for both `--plan` and steps report mode.

### 3. Machine verification

- [x] `tests/schema/test_step_outcome_contract.py`: fixture positives/negatives, code
      registry ↔ schema enums, decision table ↔ fixtures, reducer rows ↔ trace axes,
      `prior_step` root-reference rule, `tool_calls` projection, bc-openCard-1 single-root
      check, package-data check.
- [x] `tests/unit/test_pre_run_reject.py`: validator codes, stable order, CLI single-stdout
      JSON + exit 2 + no artifact create/rewrite + zero device calls, and the negative case
      proving a non-protocol failure does not emit the envelope.
- [x] `scripts/verify_contracts.py`: one-command Phase 0 check.
- [x] `python -m pytest` green (669 passed, 2 skipped, 2 deselected).

### 4. Freeze gate

- [x] Independent review sign-off on **D-1** (no `observation` on `blocked`/`skipped`),
      **D-2** (new core envelope field `device_session`) and **O-1** (unparseable plan
      file keeps its non-protocol path). Two independent reviews, both accept; verdicts
      recorded in `step-outcome-v1.md` and `design.md`.

### 5. Review round 1 follow-up (2026-08-31, both reviews NEEDS_CHANGES)

- [x] **R1 P1-1** dispatch negatives: unknown `schema_version`, mismatched root
      `result_protocol`, mismatched `environment.result_protocol`.
- [x] **R1 P1-2** end-to-end CLI regression for `run --steps-file` report mode reject
      (4 codes x envelope/exit/no-write, plus no-rewrite and zero-device variants).
- [x] **R2 P0-1** StepResult local consistency in schema: `role` <-> `observation.kind`;
      `blocked`/`skipped` selector must be `not_attempted`; assertion `matched=false`
      must use `failure.domain=assertion`; `contract.empty_case` removed from the
      `failure.code` registry and split into its own pre-run reject registry.
- [x] **R2 P0-2** `tool_calls` reuses `domainCodeAgreement` and the reason registries.
- [x] **R2 P1-3** `unresolvable` facts conditioned on `reason_code`
      (provider probe / fragment keys / dump_status / request_complete).
- [x] **R2 P1-4** `hylyre/contracts/reference_reducer.py` (normative oracle for
      sections 9 and 12) + `golden/trace/invalid-crossrow/` (12 schema-valid,
      verifier-invalid traces) + case-level checked_vlm, capture-unavailable,
      optional-Toast and uncovered-Toast traces; reducer tests now recompute.
- [x] **R2 P1-5** artifact paths reject Windows absolute/UNC/backslash traversal.
- [x] **R2 P1-6** `report-sections.yaml` version-dispatched into `current` / `legacy`,
      drift check added to `verify_contracts.py` and the test suite.
- [x] Non-blocking: decision-table reducer wording, contracts README note that
      `scripts/` and `tests/` are repo-only.
- [x] Re-verified: `verify_contracts.py` OK, `python -m pytest -q` 733 passed.

### 6. Review round 2 follow-up (2026-08-31)

- [x] **P1** section 6.1's `candidate_count` exemption (`unresolvable` +
      `candidate_countable=false`) is now implemented in `reference_reducer.py`;
      the spec and the shipped oracle no longer disagree on a schema-legal input.
- [x] Pinned both directions: `trace/valid/unresolvable-partial-enumeration.json`
      (exempt, must pass) and `trace/invalid-crossrow/countable-unresolvable-count-mismatch.json`
      (countable, must still be recomputed), plus a named spec-clause test.
- [x] Non-blocking: decision table now points at the shipped
      `hylyre/contracts/reference_reducer.py`, not the test that drives it;
      out-of-range prior_step fixture renamed to match the branch it actually hits.
- [x] Re-verified: `verify_contracts.py` OK, `python -m pytest -q` 738 passed.

## Freeze record (Phase 0 handoff)

Frozen at commit `1543c2649b058bf2935ffae12932c76bde89a49f` on branch `step-outcome-protocol-v1`.

| Field | Value |
|---|---|
| `result_protocol` | `hylyre.step-outcome/1` |
| trace `schema_version` | `0.4-p0` |
| contract files | 223 |
| `source.tree_sha256` | `e0833814cb9785cfba5fd0c4c934fad6ad98a6391f12cf252ed56996dee0df31` |
| bundle | `hylyre-contracts-0.4-p0-e0833814cb97.zip` |
| bundle sha256 | `e0e71b421e99d6f4d40acc4799007b14a4d45659839482ccb2fb46439a8a9849` |

Rebuild the identical bundle with `python scripts/build_wheel.py --contracts --clean`
(LF-normalized and deterministically zipped, so the hashes above are reproducible on
any machine regardless of git `core.autocrlf`).

**Phase 1 acceptance**: the 0.5.0 plain-source release manifest must report
`contracts_tree_sha256` equal to `source.tree_sha256` above. If it differs, the shipped
contracts are not the frozen ones and every differing file must be justified.

## Phase 1 — real 0.5.0 implementation

- [x] Transient `OperationOutcome` tagged union (`hylyre/api/outcome.py`), with typed
      control-flow exceptions converted **once** at the dispatch boundary
      (`hylyre/api/outcome_from_error.py`) — by exception type, never message text.
- [x] **D-2 acceptance point**: `device_session` comes from `HylyreAgent.is_connected`,
      read *after* the operation (sampling it before would report "no session" for the
      first step of every run and silently exempt it from the artifact obligation).
- [x] Production reducer delegates to `contracts/reference_reducer.py` rather than
      restating section 9, so the two cannot drift; conformance asserts agreement on
      every `golden/trace/valid/**` and rejection of every `invalid-crossrow/**`.
- [x] Single `OperationOutcome → StepResult` builder (`hylyre/scenario/step_builder.py`),
      enforcing the L-1/L-2 local rules it is uniquely positioned to know.
- [x] Wire real plan runner, native/resolver driver, fake runner, steps-file/inline batch.
- [x] Wire atomic CLI, MCP atomic/batch, session daemon; all declare the protocol via
      the shared `step_response`/`batch_response` envelope.
- [x] `CaseResult`/`RunResult`/`tool_calls` reduced from `steps[]` only.
- [x] Verifier owns cross-row rules; the `status != passed → failure_kind/failure_code`
      rule is **deleted** (only a docstring records why), not renamed or copied.
- [x] `emit.py` writes `0.4-p0` + `result_protocol`; `tool_calls` keeps the nested shape.
- [x] Legacy isolation: `report begin/record/finalize` stays legacy and never declares
      the protocol; dispatch is fail-closed on unknown combinations.
- [x] Failure-boundary artifacts carry a real sha256 and a relative path; capture
      failure records `hylyre.capture` instead of fabricating a file.
- [x] Version 0.5.0, README/CHANGELOG/`docs/migration-0.5.md`, source manifest.
- [x] Conformance suite (`tests/schema/test_phase1_conformance.py`), full pytest,
      one source build + verify.

### Contract amendment during Phase 1 (requires review)

Implementation found one frozen rule that could not represent a real run:
`selectorSelectedV1.id` required a non-empty string, but `ResolvedHit.id` is `""` for a
node matched purely by text (`hylyre/api/selector_resolve.py:56,163`), which 0.3-p0
reported as `selected_id: null`. A unique resolution of an id-less node was therefore
**unrepresentable**.

Amended together, per the freeze rule:

- `output-schema.json`: `selected.id` nullable, with `anyOf` requiring `id` *or*
  `bounds` — a contentless `selected` stays illegal, and backfilling the request
  into `selected` stays illegal;
- `step-outcome-v1.md` section 6.1: documents the case;
- `golden/resolution/valid/unique-without-structured-id.json` (positive) and
  `golden/resolution/invalid/unique-selected-without-any-identity.json` (negative).

A second review round then required the native-path resolution rules to be written
into the spec (section 6.1), which moved the fingerprint again.

| Stage | contracts `tree_sha256` | files |
|---|---|---|
| Phase 0 freeze | `e0833814…df31` | 223 |
| + nullable `selected.id` (a resolved node may have no id) | `a047d52e…a384` | 225 |
| + native-path resolution rules written into spec section 6.1 | `623d6c5f…40c4` | 225 |
| + Q5 artifact path base, Q8 multi-root allowance | **`cc738c272324…1bae`** | 226 |

**Maison must take the latest bundle**: `hylyre-contracts-0.4-p0-cc738c272324.zip`,
zip sha256 `d113d2ee6ac23c1cd0df1fafff4a18304db36b11a93e947b44834bf3d4f07a0c`.
Every earlier fingerprint is superseded.

Revision 4 answers Maison's Phase 0 reconciliation:

- **Q5** — `artifacts[].path` resolves as `resolve(dirname(trace_path), path)`, must stay
  inside that tree, and has no second base and no working-directory dependency. This was
  not documentation alone: the producer recorded paths relative to the *failure* directory,
  so a trace written elsewhere could not locate its own evidence. The failure directory now
  sits beside the trace and the base is threaded to the capture point.
- **Q8** — `prior_step` MAY reference any earlier eligible root in the same case; nearest is
  not required. Pinned by `golden/trace/valid/prior-step-references-an-earlier-root.json`,
  which deliberately skips the nearer root.

### Review sign-off

Both independent reviews closed **PASS** on 2026-08-31 against
`cc738c272324…1bae`, with 829 passed / 2 skipped, both bundles `--verify` clean,
and the shipped contracts compared file-by-file against the working tree (226/226).

### Phase 1 review round 2 — findings closed

| Finding | Fix |
|---|---|
| steps-file report mode emitted a trace its own verifier rejected | one batch is one case (`STEPS-BATCH`), so `prior_step` closes inside it |
| native wait backfilled the request into `selected` | `resolution` derived from the observation; absent ⇒ `not_found` |
| real Hypium `wait_for` raised a selector error for a timeout | driver returns an observation; the agent classifies `assertion.mismatch` |
| MCP atomic response was double-wrapped, losing top-level protocol | serialize the envelope directly |
| `ai_assert` outcome discarded; CLI always returned "ok" | CLI emits the envelope and exits non-zero; `ai_wait_for` consumes outcomes |
| device death: next case re-attempted instead of re-probing | fresh `device_preflight` probe forms that case's own root |
| unconfigured failure-dir reported as `transport_failure` | honest reason code |
| generic `ValueError` blamed on the plan; bad return escaped as TypeError | only `PlannedStepContractError` maps to `contract.*`; wiring bugs become `internal.unexpected_exception` and still produce a row |
| fake selector failure had no selector evidence | stub emits request + `not_found` resolution |
| dispatch exposed internal aliases, not the frozen codes | `trace_dispatch_code()` returns `legacy_unsupported_for_evidence` / `unsupported_schema_or_protocol` |
