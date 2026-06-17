## ADDED Requirements

### Requirement: Rich selector resolution over UI dump tree

The system SHALL provide `hylyre/api/selector_resolve.py` exposing a pure function `resolve_targets(tree, pred)` that, given a `dump_ui()` tree and a predicate object, returns an ordered list of hits, each carrying the clickable center coordinates (`center=[x,y]`), `tap_bounds`, matched `attrs`, `overlay_rank`, and `depth`. The predicate SHALL support base selectors (`by_text`, `by_id`, `by_type`, `by_key`), text match mode (`match` = `contains` default or `exact`), filters (`visible`, `clickable`, `enabled`), scoping (`scope="top_overlay"`, `within`), relative anchors (`below`, `above`, `after`, `before`), conjunction (`all` = AND of sub-selectors), and selection (`index`, 0-based). The function MUST be importable without `hypium`.

#### Scenario: Same-text button on top overlay wins

- **GIVEN** a tree where a bottom-sheet overlay and the page behind it each contain a clickable node with text "下一步"
- **WHEN** `resolve_targets(tree, {"by_text": "下一步"})` is called
- **THEN** the first hit is the overlay's node (higher `overlay_rank`) and its `center` falls within that node's bounds

#### Scenario: top_overlay scope restricts matches

- **WHEN** the predicate includes `scope="top_overlay"`
- **THEN** only nodes within the topmost overlay subtree (type containing Sheet/Dialog/Popup/Menu/ModalWindow/Overlay; last window when multiple) are considered

#### Scenario: Pure function, no device

- **WHEN** `resolve_targets` is called with an in-memory tree dict and no device connection
- **THEN** it returns hits without importing `hypium` or touching any driver

### Requirement: Text node lifts to nearest clickable ancestor

The system SHALL, after matching a text node, lift the tap target to the **nearest** ancestor with `clickable=true` and use that ancestor's center as the click point. Only when no `clickable=true` ancestor exists SHALL it fall back to the nearest `enabled` ancestor, and that fallback SHALL be bounded (e.g. skip over-large container ancestors / stop before the root) to avoid lifting onto an oversized region; if neither yields a suitable target, it SHALL use the text node itself. In an `all` (AND) predicate, `by_text` SHALL match the text node first and the remaining predicates (`by_type`, `clickable`, `enabled`) SHALL be evaluated against the lifted target, not the original text node.

#### Scenario: Click lands on parent Button

- **GIVEN** a node tree where text "下一步" is on a child `Text` and `clickable=true` is on the parent `Button`
- **WHEN** `resolve_targets(tree, {"all": [{"by_text": "下一步"}, {"by_type": "Button"}]})` is called
- **THEN** the resulting hit's `center` is within the parent `Button` bounds

### Requirement: Deterministic ranking and observable candidates

The system SHALL order hits by `overlay_rank` descending, then `clickable`, then `enabled`, then tree order; `index` SHALL select from this ordered list. Occlusion SHALL be decided by overlay/z-order ranking rather than by `visible` (bounds area greater than zero is not sufficient to prove a node is unoccluded). When more than one hit matches, the system SHALL include a `candidates_summary` (text/id/bounds/overlay_rank per candidate) usable for logging and error messages. Zero matches SHALL raise `SelectorResolutionError` carrying the candidate/dump summary.

#### Scenario: Index selects from ranked list

- **WHEN** two nodes match and the predicate includes `index: 1`
- **THEN** the second hit in ranked order is returned

#### Scenario: Zero match raises with diagnostics

- **WHEN** no node matches the predicate
- **THEN** `SelectorResolutionError` is raised and its message includes a candidate/dump summary
