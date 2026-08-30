## ADDED Requirements

### Requirement: Hardened planned-step selector and verdict path

The planned-step API SHALL accept a single selector root including an explicit `all` conjunction, recursively validate every nested selector before resolution, and route every selector-bearing public action through the shared exact/contains contract. `scope="top_overlay"`, relative anchors, swipe/scroll areas, and `scroll_to.in` SHALL fail closed when their constraint has zero or multiple candidates. A plan action SHALL never choose an implicit first hit. Invalid match values SHALL use the existing selector failure classification and SHALL not add a failure-code enum.

#### Scenario: All conjunction reaches the resolver

- **WHEN** a planned touch uses `{"all":[{"by_type":"Button"},{"by_text":"下一步","match":"exact"}]}`
- **THEN** the agent accepts the selector shape and resolves it through the shared resolver rather than rejecting it as multiple top-level selectors

#### Scenario: Missing overlay is not the whole tree

- **WHEN** a selector requests `scope="top_overlay"` and the dump has no overlay root
- **THEN** resolution fails with `selector_not_found` and never searches the ordinary root as a fallback

#### Scenario: Empty relative anchor fails closed

- **WHEN** a selector has a relative anchor that matches zero nodes
- **THEN** the target selector has zero hits and the action fails with `selector_not_found`

#### Scenario: Swipe and scroll require unique containers

- **WHEN** two scrollable nodes match a swipe `area` or scroll `at` selector without an explicit disambiguator
- **THEN** the action fails with `selector_ambiguous`, records candidate summaries, and issues no native scroll command

#### Scenario: Aborted or incomplete assertions cannot pass

- **WHEN** an earlier action aborts execution, or a required assertion is skipped/blocked, or a passing assertion has empty evidence
- **THEN** the case is not `verification="passed"` regardless of any other passing assertion

### Requirement: Rich text and Toast lifecycle are represented in the planned result

The planned API SHALL allow ordinary Text contains resolution while rejecting aggregate inline targets without independent fragment bounds or semantic action. Plan and batch execution SHALL start Toast observation before the trigger action and honor the following assertion's `on_unsupported` policy without converting a capability limitation into an assertion mismatch.

#### Scenario: Ordinary Text contains remains addressable

- **WHEN** a normal clickable Button contains Text `账户余额 100 元` and the action requests `by_text="账户余额"`, `match="contains"`
- **THEN** the resolver may lift to the real clickable ancestor and the action is not classified as an unresolved inline target

#### Scenario: Aggregate inline Text fails closed

- **WHEN** a dump marks aggregate rich text but exposes no independently clickable fragment bounds or semantic action
- **THEN** the action fails with `inline_target_unresolvable` and no parent Text/Row center is touched

#### Scenario: Unsupported Toast skip preserves the trigger ledger

- **WHEN** listener startup is unsupported before an action and the next planned Toast assertion has `on_unsupported="skip"`
- **THEN** the trigger action remains represented, the Toast assertion is a typed skipped capability row, and execution does not fail solely because the optional Toast capability is unavailable

