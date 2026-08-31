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

## Phase 1 — real 0.5.0 implementation (blocked on the Phase 0 review)

- [ ] Transient `OperationOutcome` tagged union (`OperationPassed|Failed|Blocked|Skipped`).
- [ ] **D-2 acceptance point**: builder populates `device_session` from real machine
      facts (never a hard-coded constant).
- [ ] Production reducer/verifier must agree with `contracts/reference_reducer.py` on
      every `golden/trace/valid/**` and reject every `golden/trace/invalid-crossrow/**`.
- [ ] Single `OperationOutcome → StepResult` builder.
- [ ] Wire real plan runner, native/resolver driver, fake runner, steps-file/inline batch.
- [ ] Wire atomic CLI, MCP atomic/batch, session daemon (smoke-level per entry).
- [ ] `CaseResult`/`RunResult` as pure reducers.
- [ ] Verifier owns cross-row rules; **delete** `hylyre/harness/runner.py:151-157`
      (`status != passed → failure_kind/failure_code`) without renaming or copying it.
- [ ] Emit `0.4-p0` + `result_protocol` from `hylyre/report/emit.py`; `tool_calls` nested projection.
- [ ] Legacy isolation: `report begin/record/finalize` and 0.3/0.2 stay legacy-labelled.
- [ ] Failure-boundary artifact capture with sha256 + capture-unavailable path.
- [ ] Version 0.5.0, README/CHANGELOG/migration, source manifest and release assets.
- [ ] Full conformance run against the Phase 0 golden fixtures; one source build + verify.
