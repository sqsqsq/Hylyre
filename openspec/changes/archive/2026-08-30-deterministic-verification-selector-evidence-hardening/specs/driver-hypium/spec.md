## ADDED Requirements

### Requirement: Frozen native selector and Toast classifications

The Hypium adapter SHALL preserve boolean wait/Toast results, exact/contains MatchPattern forwarding, and structured selector evidence. Unsupported Toast capability SHALL be classified as `capability_unsupported` and may become `skipped` only through the planned `on_unsupported="skip"` policy; a supported false Toast result SHALL remain `assertion_mismatch`. Invalid match values SHALL be selector-classified with the existing `selector_not_found` code, not a new code.

#### Scenario: False Toast is an assertion mismatch

- **WHEN** the native Toast check returns boolean `False` through the complete observation window
- **THEN** the adapter raises an assertion mismatch with Toast channel/result evidence

#### Scenario: Unsupported Toast is distinct

- **WHEN** Hypium reports that Toast listening/checking is unsupported
- **THEN** the adapter exposes `failure_kind="capability"` and `failure_code="capability_unsupported"` without rewriting it as a normal assertion failure

#### Scenario: Invalid match does not extend the interface

- **WHEN** a native selector requests `match="starts_with"` or `match="typo"`
- **THEN** it fails before device I/O with selector classification using the frozen `selector_not_found` code

