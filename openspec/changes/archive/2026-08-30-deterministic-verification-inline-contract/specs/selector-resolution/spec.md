## ADDED Requirements

### Requirement: Inline targets require an explicit contract signal or independent target

The resolver SHALL NOT infer inline-target intent from Row/Button/ancestor types. Ordinary Text/Row `contains` SHALL retain normal resolution. A Text node SHALL be treated as an aggregate inline target only when the host supplies `inline_target=true` (or valid fragment/semantic target metadata); with that signal and no independently clickable fragment bounds/action, action resolution SHALL return `inline_target_unresolvable` without clicking a parent center.

#### Scenario: Normal dynamic Row contains succeeds

- **WHEN** a clickable Row contains ordinary Text `账户余额 100 元` and the action requests `by_text="账户余额"`, `match="contains"` without inline-target metadata
- **THEN** resolution returns the Row target and does not classify it as `inline_target_unresolvable`

#### Scenario: Explicit aggregate Text fails closed

- **WHEN** a Text node has `inline_target=true`, contains the requested inline phrase, and exposes no valid fragment bounds or semantic action
- **THEN** action resolution returns `inline_target_unresolvable` and issues no parent Row/Text click

#### Scenario: Nested inline target uses the same contract

- **WHEN** the `by_text` phrase is inside `all[]` and the matched Text node has `inline_target=true` without a valid fragment target
- **THEN** the action fails closed with `inline_target_unresolvable`
