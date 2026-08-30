## ADDED Requirements

### Requirement: Inline contract flows through StepResult

The scenario runner SHALL preserve the resolver's normal/inline classification and selector evidence in the single StepResult ledger; it SHALL not add a runner-side heuristic or alternate rich-text status.

#### Scenario: Normal and inline outcomes remain typed

- **WHEN** one planned action resolves an ordinary Row contains and another targets an explicit unresolved inline Text
- **THEN** their StepResults retain the respective successful selector evidence and `inline_target_unresolvable` selector failure without a second ledger
