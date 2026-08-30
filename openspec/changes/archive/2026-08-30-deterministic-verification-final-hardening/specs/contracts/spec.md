## ADDED Requirements

### Requirement: Toast coverage is part of assertion evidence

New-schema verification SHALL require a passing Toast assertion to carry non-empty evidence with `trigger_window_covered=true`; `trigger_window_covered=false` is explicit non-verifying evidence, not a successful trigger assertion.

#### Scenario: Trace cannot certify uncovered Toast

- **WHEN** a new trace marks a Toast-only case as verified while its Toast evidence says `trigger_window_covered=false`
- **THEN** trace verification rejects the case
