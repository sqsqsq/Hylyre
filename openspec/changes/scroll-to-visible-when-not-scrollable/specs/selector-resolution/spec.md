## MODIFIED Requirements

### Requirement: scroll_until_visible container-aware pre-match

When `scroll_until_visible` is called with a container `in`, the system SHALL locate the container via selector matching **without** requiring `scrollable=true`. On each iteration, before attempting to swipe, the system SHALL try to resolve the target within the container subtree; on iteration 0, if the subtree misses, it SHALL attempt a full-tree resolve accepting only hits whose **matched node center** (pre-lift) lies within the container bounds, returning the lifted tap target (falling back to the matched node center if the lifted center is outside the container).

When `container` is omitted, the system SHALL attempt a whole-tree resolve before the first swipe.

Scrolling SHALL still require a `scrollable=true` root from `find_scroll_root`. The List→Scroll swipe fallback at iteration 0 SHALL apply **only when `container` is omitted**; when `in` is specified, the system SHALL NOT downgrade to a different container type for scrolling.

After the scroll loop exits without a hit, when `container` is omitted and the target predicate is pure `by_text` without rich fields, the system MAY attempt a final resolve fallback before raising `SelectorResolutionError`. When `in` is specified, the system SHALL NOT perform a global native text fallback that could click an out-of-container homonym.

#### Scenario: Visible target in non-scrollable Scroll container

- **GIVEN** a Scroll container matching `in` with `scrollable=false` and the target visible inside on the first dump
- **WHEN** `scroll_until_visible` runs
- **THEN** it returns immediately with zero swipes

#### Scenario: Same text outside container does not short-circuit

- **GIVEN** matching text exists outside the container bounds and inside only after scroll
- **WHEN** `scroll_until_visible` runs with `in`
- **THEN** it does not return the outside hit on iteration 0 and continues scrolling until the in-container hit appears

#### Scenario: No cross-container swipe fallback when in is specified

- **GIVEN** `in` specifies `by_type: List` but the page only has a scrollable Scroll
- **WHEN** `scroll_until_visible` runs
- **THEN** it does not swipe the Scroll as a List fallback
