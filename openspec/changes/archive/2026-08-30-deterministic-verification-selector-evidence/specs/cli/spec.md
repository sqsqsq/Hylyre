## ADDED Requirements

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
