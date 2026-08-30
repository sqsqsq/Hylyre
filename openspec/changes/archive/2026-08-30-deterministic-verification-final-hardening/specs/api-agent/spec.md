## ADDED Requirements

### Requirement: Toast coverage is required for verified cases

An `assert_toast` step SHALL qualify as a passing verification assertion only when its evidence records that a listener was active before the trigger (`trigger_window_covered=true`). An assertion-only Toast check SHALL remain observable but SHALL make the case inconclusive/blocked rather than verified.

#### Scenario: Assertion-only Toast cannot verify

- **WHEN** a case contains only an `assert_toast` whose evidence says `trigger_window_covered=false`
- **THEN** the case is not `verification="passed"` and is not projected as legacy `通过`

#### Scenario: Adjacent trigger Toast can verify

- **WHEN** a planned trigger is followed by a supported Toast assertion and the listener starts before the trigger
- **THEN** a true Toast result may contribute to `verification="passed"` with coverage evidence

### Requirement: Nested selector semantics are preserved

When `by_text` is supplied inside `all[]`, the agent SHALL use the nested text predicate's exact/contains mode and SHALL record that effective mode in the StepResult selector evidence.

#### Scenario: Nested exact is auditable

- **WHEN** `all[]` contains `{"by_text":"foo","match":"exact"}`
- **THEN** the action uses exact matching for that text and records `requested_match="exact"` and `effective_match="exact"`
