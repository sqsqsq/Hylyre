## ADDED Requirements

### Requirement: CLI planned-step and verification conformance

CLI plan, steps-file, atomic planned-step, and report verification paths SHALL continue to use the shared dispatcher, ledger, selector contract, and verifier. At least one regression SHALL execute a real planned wait/selector/verdict path with a fake driver supplied at the driver boundary, and legacy verification output SHALL be explicit.

#### Scenario: CLI production dispatcher is exercised

- **WHEN** the CLI test runs a planned wait or selector with a deterministic fake driver
- **THEN** the result is produced by the public planned dispatcher and contains typed selector/evidence fields rather than a hand-built result object

#### Scenario: CLI reports legacy explicitly

- **WHEN** `hylyre report verify` accepts a readable legacy trace
- **THEN** its output identifies the trace as legacy and ineligible for new StepResult evidence claims

