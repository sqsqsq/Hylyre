## ADDED Requirements

### Requirement: scroll_until_visible container-aware pre-match

When `scroll_until_visible` is called with a container `in`, on iteration 0, if `resolve_targets(scroll_root, pred)` misses, the system SHALL attempt `resolve_targets(tree, pred)` but only accept hits whose `center` lies within `scroll_root` bounds. Hits outside the container bounds SHALL NOT short-circuit scrolling.

#### Scenario: Visible target inside container bounds

- **GIVEN** target text is visible within the scroll container bounds on the first dump
- **WHEN** `scroll_until_visible` runs with matching `in`
- **THEN** it returns immediately with zero swipes

#### Scenario: Same text outside container does not short-circuit

- **GIVEN** matching text exists outside the container bounds and inside only after scroll
- **WHEN** `scroll_until_visible` runs with `in`
- **THEN** it does not return the outside hit on iteration 0 and continues scrolling until the in-container hit appears
