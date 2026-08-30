## ADDED Requirements

### Requirement: Toast window participates in verdict coverage

The scenario verdict SHALL reject a verified pass when any passing `assert_toast` step lacks `evidence.trigger_window_covered=true`. The step may remain `passed` as an operation result, but the case verification SHALL be `inconclusive` unless the required covered assertion path exists.

#### Scenario: Uncovered Toast is not a verified assertion

- **WHEN** an assertion-only Toast operation returns true with `trigger_window_covered=false`
- **THEN** case verification is not passed

### Requirement: Blocked suffix preserves causal classification and count

When abort stops a plan, blocked rows SHALL retain the root failure kind/code as their causal classification where the frozen taxonomy permits it; batch `executed` SHALL count only dispatched operations, while the result array still contains all blocked audit rows.

#### Scenario: Selector failure blocks without becoming infrastructure

- **WHEN** a selector miss aborts step 1 and step 2 is not dispatched
- **THEN** step 2 is blocked with selector causal classification and `executed` remains 1
