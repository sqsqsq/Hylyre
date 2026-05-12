## ADDED Requirements

### Requirement: Executable CA bootstrap path

The system SHALL extend the Lyrebird / MITM onboarding beyond static Markdown by providing a Hylyre CLI entry that attempts host-side `hdc file send` (or equivalent documented sequence) for a given PEM/CRT, with explicit exit codes for success, partial success (file pushed only), or unsupported environment.

#### Scenario: Missing hdc

- **WHEN** the CLI runs and `hdc` is not on PATH
- **THEN** the command exits non-zero with actionable guidance (aligned with `hylyre doctor`)

#### Scenario: Dry-run or test hook

- **WHEN** unit tests invoke the bootstrap layer with subprocess execution mocked
- **THEN** no real `hdc` process is required and argument parsing remains stable

---

### Requirement: Spec alignment

The system SHALL keep `mitm_trust_instructions()` text and the new executable path behavior described together in this change’s spec delta until archived into `openspec/specs/`.

#### Scenario: No contradictory guidance

- **WHEN** both the static checklist and the executable bootstrap CLI are updated in the same change
- **THEN** release notes or tasks explicitly list which user-facing entry (`mock cert` vs executable command) applies in which environment
