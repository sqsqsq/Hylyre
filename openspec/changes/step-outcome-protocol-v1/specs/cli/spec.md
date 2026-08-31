# cli — pre-run contract reject

## ADDED Requirements

### Requirement: run rejects contract-invalid plans before touching a device

`hylyre run --plan` and `hylyre run --steps-file` report mode SHALL validate the planned
step contract before constructing any agent or connecting a device. On the first
violation they SHALL print exactly one UTF-8 JSON object on stdout matching
`output-schema.json` `#/$defs/pre_run_reject`, exit with code `2`, and leave
`--report-out` and `--trace-out` untouched.

#### Scenario: empty case

- **WHEN** a plan case has no executable planned step
- **THEN** stdout is one `pre_run_reject` object with `rejection.code: "contract.empty_case"` and `rejection.case_id` set, the exit code is `2`, and no report/trace file is created

#### Scenario: statically invalid step, match or selector

- **WHEN** a planned JSON step is unparseable, has zero or multiple root keys, carries a `match` other than `exact`/`contains`, or a `touch` block without exactly one target predicate
- **THEN** the rejection code is `contract.invalid_step`, `contract.invalid_match` or `contract.invalid_selector` respectively, with `path` and `step_index` pointing at the offending step

#### Scenario: existing artifacts are not rewritten

- **WHEN** `--report-out`/`--trace-out` already exist and the plan is rejected
- **THEN** their contents are unchanged

#### Scenario: no device is contacted

- **WHEN** a contract-invalid plan is run without `--use-fakes`
- **THEN** no Hypium agent is constructed and no device connection is attempted

#### Scenario: valid plans are unaffected

- **WHEN** a contract-valid plan is run
- **THEN** execution, artifact writing and L5 verification proceed exactly as before
