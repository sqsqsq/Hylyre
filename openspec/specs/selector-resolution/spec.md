# selector-resolution Specification

## Purpose
TBD - created by archiving change device-automation-robustness. Update Purpose after archive.
## Requirements
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

For ordinary text nodes with a real clickable ancestor, the resolver SHALL lift to the nearest clickable ancestor and use that ancestor's center; only when no clickable ancestor exists may it use a bounded nearest enabled ancestor, otherwise the text node itself. In an `all` predicate, `by_text` SHALL match the text node first and remaining predicates SHALL be evaluated against the lifted target. For a host-identified inline rich-text request (`inline_target=true` or equivalent independent fragment/semantic metadata), lifting to a parent Text/Row center is forbidden: the resolver SHALL require an independently represented Span/fragment bounds or semantic action target. If that information is absent, it SHALL raise `SelectorResolutionError` with `inline_target_unresolvable` metadata rather than returning a guessed hit.

#### Scenario: Normal Text child targets Button

- **GIVEN** a Text node `下一步` is a child of a clickable Button
- **WHEN** the predicate targets the normal text
- **THEN** the hit center is inside the Button bounds

#### Scenario: Explicit aggregate inline Text is unresolvable

- **GIVEN** a Text node contains concatenated ordinary and clickable span text, is identified as `inline_target=true`, and has no fragment-level bounds/action
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

### Requirement: Inline resolution evidence

When a real fragment target is available, the resolver SHALL identify its `resolution_kind` (for example `span_bounds` or `semantic_action`) and fragment bounds in the hit evidence. It SHALL never estimate coordinates from character ranges, OCR, glyph widths, or parent bounds.

#### Scenario: Real fragment target is auditable

- **WHEN** a fixture exposes an independent clickable fragment bounds
- **THEN** the hit uses those bounds and records the resolution kind

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

### Requirement: Shared boolean property filters
选择器 SHALL 增加 checked/checkable/focused，连同 clickable/enabled/scrollable 共用属性读取及类型归一化；显式 true 和 false 均为精确过滤，字段未给才不约束。字段 SHALL 贯通预检、选择器 request、节点转换、过滤与所有使用选择器的入口。

#### Scenario: False filter is not omitted
- **WHEN** wait_for 选择 by_id=x 且 checked=false
- **THEN** 仅实际可观测 checked=false 的目标匹配；目标不存在或 checked=true 不匹配

#### Scenario: Missing observation cannot prove absence
- **WHEN** 节点符合身份谓词但请求的 checked 属性无法观测
- **THEN** 明确能力缺失或读取失败，不默认 false，也不让 wait_gone 因缺属性而通过

#### Scenario: Disappearance differs from false state
- **WHEN** wait_gone 使用 checked=true 且目标实际消失
- **THEN** 可按现有 absence 语义通过，但不宣称目标仍存在或 checked=false

### Requirement: Input and observed boolean normalization
系统 SHALL 只接受 JSON 布尔作为选择器输入；读取侧 SHALL 把原生/dump 的 true/false 布尔或字符串归一化为布尔，其它值或缺失标记不可观测。过滤、属性查询和状态设置 SHALL 共用三态读取。现有 _attr_bool 的缺失即 false 行为仅适用于原有二态用途，如点击排序和祖先查找。

#### Scenario: String observation differs from string input
- **WHEN** dump 返回 checked="false" 而选择器 checked=false
- **THEN** 可以匹配；反之选择器 checked="false" 在预检拒绝
