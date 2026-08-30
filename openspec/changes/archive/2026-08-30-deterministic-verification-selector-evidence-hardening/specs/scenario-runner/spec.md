## ADDED Requirements

### Requirement: Complete ledger and strict three-axis verdict

The scenario runner SHALL append one `StepResult` for every planned row, including typed `blocked` rows for the unexecuted suffix after abort and a typed expected-check row whenever expected text is non-empty. It SHALL compute `execution`, `verification`, and `evidence` from that ledger: only completed execution with every required assertion passing and non-empty assertion evidence may be verified; action-only, all-skipped, aborted, and blocked cases cannot pass. Runtime and harness outcome projection SHALL use the same algorithm.

#### Scenario: Abort still leaves a complete plan ledger

- **WHEN** step 1 fails under abort-on-failure and steps 2 and 3 were planned
- **THEN** steps 2 and 3 are present as `blocked` rows with stable failure fields and the case cannot be a verified pass

#### Scenario: Non-empty expected mode is not erased by abort

- **WHEN** expected text exists, VLM is available, and an earlier action aborts before the expected check
- **THEN** `expected_check_mode` is `checked_vlm` and the expected-check row records that it was blocked rather than changing the mode to `empty`

#### Scenario: Skipped assertions prevent verified pass

- **WHEN** one assertion passes and another required Toast assertion is skipped
- **THEN** verification is `inconclusive` or `failed`, never `passed`

#### Scenario: Empty evidence is incomplete

- **WHEN** an assertion returns success with `{}` or no evidence
- **THEN** case evidence is `incomplete` and verification is not `passed`

#### Scenario: Runtime and harness agree

- **WHEN** a report contains one verified case and one blocked case
- **THEN** runtime emission and `verify_report` compute the same overall outcome

