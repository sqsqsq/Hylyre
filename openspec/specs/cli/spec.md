# cli Specification

## Purpose

`hylyre` 命令行入口（Typer）：`run` / `mock` / `device` / `report` / `bootstrap` / `ai` 等子命令与 `--help` 契约。
## Requirements
### Requirement: Hylyre CLI

The system SHALL ship a `hylyre` console script registering top-level commands: `run`, `mock`, `device`, `report`, `progress`, `spec`, `doctor`, `bootstrap`, `mcp`, `ai`, each with working `--help`.

#### Scenario: Doctor runs

- GIVEN a developer runs `hylyre doctor`
- WHEN the environment is inspected
- THEN Python/Node/npm/hdc/mitmproxy checks are printed in a structured table

#### Scenario: Nested report verify

- **GIVEN** a developer runs `hylyre report verify --help`
- **WHEN** P4 build is complete
- **THEN** help lists `--report`, `--trace`, and `--plan`

#### Scenario: Run lists device options

- **GIVEN** a developer runs `hylyre run --help`
- **WHEN** P4 build is complete
- **THEN** help lists `--use-fakes`, `--device-sn`, `--bundle`, `--mock-port`, `--lyrebird-url`, `--mock-group`, `--skip-assert-expected`, and `--model-backend`

#### Scenario: Run callback options are consumed or refused, never dropped

- **GIVEN** an option declared on the shared `hylyre run` callback (`--plan`, `--steps`, `--steps-file`, `--on-fail`, `--out`, `--session`, `--page-name`, `--wait-time`, `--feature`, `--report-out`, `--trace-out`, `--use-fakes`, `--device-sn`, `--bundle`, `--mock-port`, `--lyrebird-url`, `--mock-group`, `--skip-assert-expected`, `--model-backend`, `--failure-dir`) and the execution path selected by the argv (`--plan`; `--steps/--steps-file` with or without `--feature/--report-out/--trace-out`; or a `run <subcommand>`)
- **WHEN** the option's effective value differs from its declared default and that path does not consume it
- **THEN** the command exits `2` with one stderr line naming the option and the path, writes nothing to stdout, contacts no device, and neither creates nor rewrites `--report-out` / `--trace-out`
- **AND** a value equal to the declared default passes through unchanged, including when written before a subcommand (`run --on-fail abort tap …`)

#### Scenario: `--on-fail` is a steps-batch option only

- **GIVEN** `hylyre run --help`
- **WHEN** the operator reads `--on-fail`
- **THEN** help states that `abort|skip` applies to `--steps/--steps-file` only and that `--plan` accepts only the default `abort`
- **AND** `run --plan … --on-fail skip` (or any invalid value) is the usage error above, and `run --steps/--steps-file … --on-fail <invalid>` exits `2` with `on_fail must be abort or skip` before any device call

#### Scenario: Progress helpers

- **GIVEN** a developer runs `hylyre progress --help`
- **WHEN** the command group is present
- **THEN** help lists `show`, `append`, and `path` subcommands for `docs/progress.md`

#### Scenario: Spec list

- **GIVEN** a developer runs `hylyre spec list --help` or bare `hylyre spec`
- **WHEN** OpenSpec workspace exists
- **THEN** `list` prints `openspec list` when the CLI is on PATH, else a directory summary under `openspec/specs` and `openspec/changes`

#### Scenario: Device list first serial

- **GIVEN** a developer runs `hylyre device list --help`
- **WHEN** P1+ device commands exist
- **THEN** help lists `--first` for scripting (`hylyre device list --first`)

#### Scenario: MCP serve help

- **GIVEN** a developer runs `hylyre mcp serve --help`
- **WHEN** P5 build is complete
- **THEN** help lists `--show-banner`, `--transport` (stdio only), and references the optional `hylyre[mcp]` dependency

#### Scenario: Bootstrap mock help

- **GIVEN** a developer runs `hylyre bootstrap mock --help`
- **WHEN** P2b command is present
- **THEN** help lists `--install` for optional `pip install mitmproxy lyrebird`

### Requirement: Device force-stop and cold-restart commands

The CLI SHALL register `hylyre device force-stop --bundle <id> [--device-sn]` (positional `aa force-stop`) and `hylyre device cold-restart --bundle <id> [--ability] [--wait-time]` (force-stop then `aa start`, with a post-start wait for the main Ability), both with working `--help`.

#### Scenario: force-stop uses positional form

- **WHEN** `hylyre device force-stop --bundle com.example.app` runs
- **THEN** it issues `aa force-stop <bundle>` (positional) rather than the `-b` form

#### Scenario: cold-restart resets to a clean start

- **WHEN** `hylyre device cold-restart --bundle com.example.app` runs
- **THEN** the app is force-stopped and then started, with a stabilization wait before returning

### Requirement: Failure diagnostics flag and scroll_to subcommand

The CLI SHALL expose `--failure-dir` on `hylyre run` and `hylyre run --steps-file` (default: a `failures/` directory beside the report output) and pass it through to the runner (including the session path). The CLI SHALL register `hylyre run scroll-to` mirroring the `scroll_to` planned JSON.

#### Scenario: run records failures to dir

- **WHEN** `hylyre run --plan ... --failure-dir <dir>` runs and a step fails
- **THEN** diagnostics artifacts are written under `<dir>`

#### Scenario: scroll-to subcommand exists

- **WHEN** `hylyre run scroll-to --help` is invoked
- **THEN** it documents the `scroll_to` JSON shape and runs it like other Tier A run subcommands

### Requirement: app page save single-device fallback and root-cause stderr

`hylyre app page save` SHALL, when none of `--from-dump`/`--session`/`--device-sn` is given and exactly one device is connected, auto-select that device instead of exiting with code 2; when zero or multiple devices are connected it SHALL print an actionable error listing connected devices. On dump/persist failure it SHALL emit the root cause (which stage failed) to stderr.

#### Scenario: Auto-select the only connected device

- **GIVEN** exactly one device is connected and no source flag is passed
- **WHEN** `hylyre app page save <bundle> <name>` runs
- **THEN** it captures from that device and saves the snapshot (no exit code 2)

#### Scenario: Clear error on ambiguous device

- **WHEN** no source flag is passed and zero or multiple devices are connected
- **THEN** the command prints an actionable error listing the connected devices

### Requirement: Shared planned-step result path

The CLI SHALL route plan runs, `run --steps-file`, and atomic planned-step commands through the same planned-step dispatcher and scenario/report result model. CLI parsing SHALL not implement an alternate selector matcher, status model, or evidence ledger. `hylyre report verify` SHALL invoke the same trace/report contract validation used by other entry points.

#### Scenario: Steps-file uses the shared ledger

- **WHEN** `hylyre run --steps-file` executes a planned step
- **THEN** the emitted case/trace contains a `StepResult` with the same selector, failure, and evidence semantics as a plan row

#### Scenario: CLI rejects invalid match

- **WHEN** a CLI planned JSON step contains `match:"typo"`
- **THEN** it fails through the shared selector path and does not silently reinterpret the value

### Requirement: CLI conformance entry

The CLI SHALL retain working help and at least one production regression for wait, selector, verdict, and report/trace verification behavior, including `--failure-dir` propagation where the command supports it.

#### Scenario: CLI regression reaches production code

- **WHEN** the CLI test invokes a planned JSON step with a fake driver
- **THEN** the assertion observes the production dispatcher/runner result, not a hand-built result object

### Requirement: CLI planned-step and verification conformance

CLI plan, steps-file, atomic planned-step, and report verification paths SHALL continue to use the shared dispatcher, ledger, selector contract, and verifier. At least one regression SHALL execute a real planned wait/selector/verdict path with a fake driver supplied at the driver boundary, and legacy verification output SHALL be explicit.

#### Scenario: CLI production dispatcher is exercised

- **WHEN** the CLI test runs a planned wait or selector with a deterministic fake driver
- **THEN** the result is produced by the public planned dispatcher and contains typed selector/evidence fields rather than a hand-built result object

#### Scenario: CLI reports legacy explicitly

- **WHEN** `hylyre report verify` accepts a readable legacy trace
- **THEN** its output identifies the trace as legacy and ineligible for new StepResult evidence claims

### Requirement: Batch execution count excludes blocked ledger rows

The CLI batch result SHALL retain blocked suffix rows in `results[]` but SHALL report `executed` as the number of planned operations actually dispatched before the abort.

#### Scenario: Abort count remains actual

- **WHEN** the first of two steps fails and the second is only represented as blocked
- **THEN** the result reports `executed=1` and contains two result rows

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

