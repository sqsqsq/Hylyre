## MODIFIED Requirements

### Requirement: Rich selector resolution over UI dump tree

The system SHALL provide `hylyre/api/selector_resolve.py::resolve_targets(tree, pred)` as a pure, deterministic resolver with base selectors (`by_text`, `by_id`, `by_type`, `by_key`), `exact`/`contains` text matching, filters (`visible`, `clickable`, `enabled`), scoping (`scope="top_overlay"`, `within`), relative anchors (`below`, `above`, `after`, `before`), conjunction (`all`), and selection (`index`, 0-based). Missing `match` SHALL use the compatibility default `contains` and expose the requested/effective mode; any other value SHALL raise a selector-contract error. Hits SHALL carry center, tap bounds, attributes, overlay rank, depth, candidate count/summary support, and enough target metadata for StepResult evidence. The function SHALL remain importable without Hypium.

#### Scenario: Exact and contains are distinct

- **GIVEN** a node has text `银行卡关联协议`
- **WHEN** the predicate uses exact `银行卡` versus contains `银行卡`
- **THEN** exact does not match and contains does match

#### Scenario: Invalid match fails closed

- **WHEN** `resolve_targets` receives `match="typo"` or `match="starts_with"`
- **THEN** it raises a selector-contract error rather than using contains

#### Scenario: Resolver and native default agree

- **WHEN** the same text predicate without `match` is evaluated by the resolver and native adapter
- **THEN** both use effective `contains` and expose that default in evidence

### Requirement: Text node lifts to nearest clickable ancestor

For ordinary text nodes with a real clickable ancestor, the resolver SHALL lift to the nearest clickable ancestor and use that ancestor's center; only when no clickable ancestor exists may it use a bounded nearest enabled ancestor, otherwise the text node itself. In an `all` predicate, `by_text` SHALL match the text node first and remaining predicates SHALL be evaluated against the lifted target. For an inline rich-text request, lifting to a parent Text/Row center is forbidden: the resolver SHALL require an independently represented Span/fragment bounds or semantic action target. If that information is absent, it SHALL raise `SelectorResolutionError` with `inline_target_unresolvable` metadata rather than returning a guessed hit.

#### Scenario: Normal Text child targets Button

- **GIVEN** a Text node `下一步` is a child of a clickable Button
- **WHEN** the predicate targets the normal text
- **THEN** the hit center is inside the Button bounds

#### Scenario: Aggregate inline Text is unresolvable

- **GIVEN** a Text node contains concatenated ordinary and clickable span text but no fragment-level bounds/action
- **WHEN** the predicate targets only the inline phrase
- **THEN** resolution fails with `inline_target_unresolvable` and no parent center is returned

### Requirement: Deterministic ranking and observable candidates

The resolver SHALL order hits by `overlay_rank` descending, then `clickable`, `enabled`, and tree order. Occlusion SHALL be determined by overlay/z-order rather than visibility alone. Without an explicit disambiguator, action callers SHALL require exactly one hit; zero hits SHALL be `selector_not_found`, more than one SHALL be `selector_ambiguous`, and the error SHALL include candidate summaries containing text/id/bounds/overlay rank. Assertion callers MAY observe multiple candidates and SHALL record `candidate_count` without changing action uniqueness.

#### Scenario: Ambiguous action fails

- **WHEN** an action predicate matches two candidates and has no explicit disambiguator
- **THEN** resolution raises `selector_ambiguous` with text/id/bounds/overlay summaries

#### Scenario: Index selects deterministically

- **WHEN** two nodes match and `index:1` is present
- **THEN** the second ranked node is returned as the unique action target

## ADDED Requirements

### Requirement: Inline resolution evidence

When a real fragment target is available, the resolver SHALL identify its `resolution_kind` (for example `span_bounds` or `semantic_action`) and fragment bounds in the hit evidence. It SHALL never estimate coordinates from character ranges, OCR, glyph widths, or parent bounds.

#### Scenario: Real fragment target is auditable

- **WHEN** a fixture exposes an independent clickable fragment bounds
- **THEN** the hit uses those bounds and records the resolution kind
