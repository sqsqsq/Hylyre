## ADDED Requirements

### Requirement: Selector constraints and inline semantics fail closed

The pure resolver SHALL recursively validate match and all nested constraints before searching. Missing `top_overlay` roots and zero-match relative anchors SHALL produce zero hits. Action resolution SHALL require exactly one hit after explicit `index`/scope/within/all disambiguation. Ordinary Text contains SHALL not be treated as rich inline content unless the dump explicitly marks aggregate/rich text; fragments SHALL default to non-clickable and require explicit clickable semantics plus real bounds or a semantic action.

#### Scenario: Nested invalid match is rejected

- **WHEN** the main target misses but a nested `within`/relative/`all` selector uses `match="starts_with"`
- **THEN** validation fails before resolution rather than hiding the invalid value behind a zero-hit main target

#### Scenario: Relative anchor zero is not satisfied

- **WHEN** a `below` or `within` anchor has no matching node
- **THEN** the constrained target has no hits

#### Scenario: Normal contains is not false inline failure

- **WHEN** ordinary Text contains a requested substring and has a real clickable ancestor without rich-text metadata
- **THEN** resolution lifts to that ancestor instead of returning `inline_target_unresolvable`

#### Scenario: Ordinary Span is not implicitly clickable

- **WHEN** a Span has bounds but does not declare clickable semantics or an action
- **THEN** action resolution does not return it as a touch target

