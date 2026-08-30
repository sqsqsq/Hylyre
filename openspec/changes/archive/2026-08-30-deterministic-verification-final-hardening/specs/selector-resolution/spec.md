## ADDED Requirements

### Requirement: Inline targets require an explicit contract signal or independent target

The resolver SHALL NOT infer inline-target intent from Row/Button/ancestor types or from a substring alone. Ordinary Text/Row `contains` SHALL retain normal resolution. A Text node SHALL be treated as an aggregate inline target only when the host supplies `inline_target=true` or valid fragment/semantic target metadata; with that signal and no independently clickable fragment bounds/action, action resolution SHALL return `inline_target_unresolvable` and SHALL not lift to a parent Row/Text center.

#### Scenario: Normal dynamic Row contains remains addressable

- **WHEN** a clickable Row contains ordinary Text `账户余额 100 元` and an action requests `by_text="账户余额"`, `match="contains"` without inline-target metadata
- **THEN** resolution lifts to the Row target instead of returning `inline_target_unresolvable`

#### Scenario: Explicit aggregate Text is unresolvable

- **WHEN** a Text node contains concatenated ordinary and clickable span text, has `inline_target=true`, exposes no fragment bounds or semantic action, and an action targets only the embedded phrase
- **THEN** action resolution fails closed with `inline_target_unresolvable` and issues no parent click

#### Scenario: Nested inline target is protected

- **WHEN** the embedded phrase is specified in an `all[]` text subpredicate
- **THEN** the same inline fail-closed rule applies

### Requirement: Unique container hit is executable

The resolver SHALL provide the unique selected container node for a validated `scroll_to.in` predicate. The scroll-to loop SHALL execute inside that node and SHALL not re-resolve the container through a first-DFS matcher that ignores selector constraints.

#### Scenario: Rich container remains the selected container

- **WHEN** `scroll_to.in` selects a Scroll under `scope="top_overlay"` or another existing rich constraint
- **THEN** target resolution and scrolling are performed within that selected Scroll node
