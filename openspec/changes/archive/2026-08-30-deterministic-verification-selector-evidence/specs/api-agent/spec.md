## MODIFIED Requirements

### Requirement: Selector-aware tap routing

`HylyreAgent` planned tap (`run_planned_tap` and the `touch` block via `_apply_touch_block`) SHALL route coordinates (`x/y`) and simple `by_id` through native `UiDriverBase.touch`, while `by_key` and rich predicates (`scope`, `within`, `below/above/after/before`, `index`, `all`, `by_type`, `visible/clickable/enabled`, `scroll_into_view`) resolve through the shared dump resolver. `by_text` SHALL use that resolver by default; an explicit native-text opt-out may use the driver contract. Every selector path SHALL use the effective `match` (`contains` when `match` is omitted, `exact` when requested), record requested/effective mode and engine, and require one target unless the existing `index`, `scope`, `within`, or `all` fields produce a unique result. Zero targets SHALL fail as `selector_not_found`; multiple targets SHALL fail as `selector_ambiguous` with candidate summaries. The agent SHALL NOT silently retry an exact miss as contains or select the first hit.

#### Scenario: Overlay text uses the documented default

- **GIVEN** a dump contains two visible text targets and the plan omits `match`
- **WHEN** a planned `touch` runs
- **THEN** the agent uses the shared effective `contains` mode, records that mode, and either taps the unique target or fails closed with candidates

#### Scenario: Invalid match is rejected before touch

- **WHEN** a planned touch contains `match:"starts_with"` or another unknown value
- **THEN** the step fails with a selector-contract error and no device touch is issued

#### Scenario: Explicit disambiguation is honored

- **GIVEN** a contains selector matches multiple nodes
- **WHEN** the plan supplies an existing `index`, `scope`, `within`, or `all` constraint that leaves one target
- **THEN** the agent taps that target and records its selected id/bounds and candidate count

### Requirement: wait_for and wait_gone accept rich selectors

`HylyreAgent` `wait_for` / `wait_gone` SHALL, when the block contains rich selector fields, poll `dump_ui` plus the shared resolver; single-attribute blocks SHALL continue to use the native Hypium wait. Both paths SHALL validate and apply the same exact/contains selector semantics as touch and input. `wait_for` succeeds only when a target is present and `wait_gone` succeeds only when no target is present; timeout failures SHALL include the selector and timeout and carry a stable failure classification.

#### Scenario: Rich and native waits agree

- **GIVEN** the same exact selector is represented by a simple block and a rich block
- **WHEN** each wait path runs against the same UI state
- **THEN** both paths reach the same present/absent conclusion and use the same effective match

#### Scenario: Missing wait target fails

- **WHEN** `wait_for` times out for a nonexistent id
- **THEN** the step fails with the selector and timeout in the human error and a machine-readable selector failure code

#### Scenario: Present wait-gone target fails

- **WHEN** `wait_gone` times out while the selected component remains present
- **THEN** the step fails instead of treating a non-`None` framework return as success

## ADDED Requirements

### Requirement: Planned assertion evidence and coverage signal

Planned assertion operations SHALL return or expose a single structured evidence mapping to the runner, including absence evidence, Toast channel/result, and non-selector assertion evidence. The API SHALL not maintain a separate case verdict; assertion coverage is determined from `StepResult.role="assertion"` and the expected-check mode at the scenario boundary.

#### Scenario: Successful absence assertion has evidence

- **WHEN** a `wait_gone` assertion completes because the target is absent
- **THEN** the operation evidence records the selector, effective match, candidate count of zero, and the observed absence

#### Scenario: Toast result is observable

- **WHEN** an `assert_toast` planned step completes
- **THEN** the returned evidence records the detection channel and the underlying boolean/event result

### Requirement: Rich inline targets fail closed

The agent SHALL tap a rich-text fragment only when the resolver supplies a real fragment bounds/semantic action target. If the dump contains only aggregate Text content for an inline target, the agent SHALL propagate `inline_target_unresolvable` and SHALL NOT fall back to a native text tap, parent center, or estimated character coordinate. A successful inline action still requires a planned post-action assertion to make the case verified.

#### Scenario: Aggregate rich text is not guessed

- **GIVEN** ordinary and clickable spans are exposed as one aggregate Text node with no fragment bounds
- **WHEN** a planned touch targets the inline text
- **THEN** the step fails with `failure_kind=selector` and `failure_code=inline_target_unresolvable` without issuing a touch
