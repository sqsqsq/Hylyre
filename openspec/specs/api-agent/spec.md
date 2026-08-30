# api-agent Specification

## Purpose

Midscene 风格的 `HylyreAgent` 外层 API（`ai_*` 动词），与具体 UI/Mock 驱动及 VLM 实现解耦；P3 实装。
## Requirements
### Requirement: HylyreAgent public surface

The system SHALL expose `HylyreAgent` from `hylyre.api` (and `hylyre` package root) with Midscene-aligned methods: `ai_action`, `ai_query`, `ai_assert`, `ai_tap`, `ai_input`, `ai_wait_for`, `ai_locate`, plus `run_planned_action`, `run_planned_tap`, `run_planned_input`, static `interpret_query_payload` / `interpret_assert_payload`, `start_app`, `aclose`, and optional `mock_activate_group` / `mock_deactivate_all` when a `MockControllerBase` is configured.

#### Scenario: Import path stable

- **GIVEN** a consumer installs `hylyre` without device/mock extras
- **WHEN** they `from hylyre import HylyreAgent` or `from hylyre.api import HylyreAgent`
- **THEN** import succeeds without importing `hypium` or `lyrebird` inside `hylyre.api`

#### Scenario: Structured tap avoids VLM

- **WHEN** `ai_tap` is called with `by_text` / `by_id` / coordinates only (no `instruction=`)
- **THEN** `HylyreAgent` uses `UiDriverBase.touch` / `input_text` without a `VlmClientBase`

#### Scenario: Natural language requires VLM

- **WHEN** `ai_tap(instruction=...)` (or other `ai_*` NL overloads) is used
- **THEN** a `VlmClientBase` must be configured or a clear `ValueError` is raised

#### Scenario: External planner without VLM

- **WHEN** `run_planned_action`, `run_planned_tap`, or `run_planned_input` is called with a payload matching the same JSON shape as the built-in `HttpVlmClient` / `VlmClientBase` vision responses
- **THEN** no `VlmClientBase` is required and the resulting `UiDriverBase` operations are equivalent to those performed when an integrated VLM returns the same payload for the corresponding `ai_*` path

---

### Requirement: VLM client abstraction

The system SHALL provide `VlmClientBase` in `hylyre.drivers.base` and a concrete `HttpVlmClient` that reads `HYLYRE_VLM_ENDPOINT`, optional `HYLYRE_VLM_API_KEY`, `HYLYRE_VLM_MODEL`, posting OpenAI-compatible chat completions with vision.

#### Scenario: Env optional client

- **WHEN** `HYLYRE_VLM_ENDPOINT` is unset
- **THEN** `HttpVlmClient.from_env()` returns `None`

---

### Requirement: Agent wiring

The system SHALL provide `hylyre.wiring.create_hypium_agent` (and `create_hypium_agent_with_env_vlm`) that lazily construct `HypiumDriver` and optional `LyrebirdController` without placing those imports in `hylyre.api`.

#### Scenario: Lazy Hypium import

- **WHEN** `create_hypium_agent(device_sn=...)` is called
- **THEN** `HypiumDriver` is imported inside the factory implementation (not from `hylyre.api`)

---

### Requirement: CLI ai natural language

The system SHALL register `hylyre ai action`, `hylyre ai query`, and `hylyre ai assert` with working `--help`, using the wiring factory and failing with a clear message when the VLM endpoint env is missing.

#### Scenario: Help lists NL subcommands

- **WHEN** `hylyre ai --help`
- **THEN** output lists `action`, `query`, and `assert` alongside `tap` and `input`

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

### Requirement: scroll_to step and scroll_into_view

The system SHALL register a planned root key `scroll_to` (in `planned_step_keys`, dispatched to a `run_planned_scroll_to`) that scrolls inside a target container until a selector becomes resolvable, with optional `tap` to click on arrival; `touch` SHALL accept an inline `scroll_into_view` that scrolls the target into view before tapping. Both SHALL reuse the in-container swipe + viewport-stability detection logic.

#### Scenario: Scroll until off-screen item is found then tap

- **GIVEN** a virtualized `List` whose target row is off-screen
- **WHEN** `{"scroll_to":{"by_text":"招商银行","in":{"by_type":"List"},"tap":true}}` runs
- **THEN** the agent scrolls within the List until the row resolves, then taps it, without a predetermined scroll-step count

### Requirement: scroll container auto-detection

When a `scroll` block omits `at` (and no `x/y`), the system SHALL auto-detect the nearest scrollable container from `_hylyre_hints.scrollable_containers` and scroll at its center, falling back to the existing screen-center `(0.5, 0.5)` when none is found.

#### Scenario: Scroll without specifying container type

- **WHEN** `{"scroll":{"direction":"up","steps":3}}` runs on a page whose scrollable is a `List`
- **THEN** the agent scrolls inside the detected List rather than failing on a wrong container type

### Requirement: StepSkipped signal

The system SHALL define `hylyre/api/exceptions.py::StepSkipped` (and `SelectorResolutionError`). Steps MAY raise `StepSkipped` to indicate an environment-unsupported step that should be recorded as skipped rather than failed.

#### Scenario: Skip propagates as a typed signal

- **WHEN** a step raises `StepSkipped`
- **THEN** callers can distinguish it from a generic failure exception

### Requirement: Planned assertion evidence and coverage signal

Planned assertion operations SHALL return or expose a single structured evidence mapping to the runner, including absence evidence, Toast channel/result, and non-selector assertion evidence. The API SHALL not maintain a separate case verdict; assertion coverage is determined from `StepResult.role="assertion"` and the expected-check mode at the scenario boundary.

#### Scenario: Successful absence assertion has evidence

- **WHEN** a `wait_gone` assertion completes because the target is absent
- **THEN** the operation evidence records the selector, effective match, candidate count of zero, and the observed absence

#### Scenario: Toast result is observable

- **WHEN** an `assert_toast` planned step completes
- **THEN** the returned evidence records the detection channel and the underlying boolean/event result

### Requirement: Rich inline targets fail closed

The agent SHALL tap a rich-text fragment only when the resolver supplies a real fragment bounds/semantic action target. The host SHALL identify aggregate inline intent with `inline_target=true` (or provide an independent fragment/semantic target); without that signal, ordinary Text/Row `contains` remains normal selector resolution. If an explicitly identified inline target exposes only aggregate Text content, the agent SHALL propagate `inline_target_unresolvable` and SHALL NOT fall back to a native text tap, parent center, or estimated character coordinate. A successful inline action still requires a planned post-action assertion to make the case verified.

#### Scenario: Explicit aggregate rich text is not guessed

- **GIVEN** ordinary and clickable spans are exposed as one aggregate Text node with `inline_target=true` and no fragment bounds
- **WHEN** a planned touch targets the inline text
- **THEN** the step fails with `failure_kind=selector` and `failure_code=inline_target_unresolvable` without issuing a touch

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

The planned API SHALL allow ordinary Text contains resolution while rejecting aggregate inline targets explicitly identified by the host without independent fragment bounds or semantic action. Plan and batch execution SHALL start Toast observation before the trigger action and honor the following assertion's `on_unsupported` policy without converting a capability limitation into an assertion mismatch.

#### Scenario: Ordinary Text contains remains addressable

- **WHEN** a normal clickable Button contains Text `账户余额 100 元` and the action requests `by_text="账户余额"`, `match="contains"`
- **THEN** the resolver may lift to the real clickable ancestor and the action is not classified as an unresolved inline target

#### Scenario: Explicit aggregate inline Text fails closed

- **WHEN** a dump marks aggregate rich text with `inline_target=true` but exposes no independently clickable fragment bounds or semantic action
- **THEN** the action fails with `inline_target_unresolvable` and no parent Text/Row center is touched

#### Scenario: Unsupported Toast skip preserves the trigger ledger

- **WHEN** listener startup is unsupported before an action and the next planned Toast assertion has `on_unsupported="skip"`
- **THEN** the trigger action remains represented, the Toast assertion is a typed skipped capability row, and execution does not fail solely because the optional Toast capability is unavailable

### Requirement: Toast coverage is required for verified cases

An `assert_toast` step SHALL qualify as a passing verification assertion only when its evidence records that a listener was active before the trigger (`trigger_window_covered=true`). An assertion-only Toast check SHALL remain observable but SHALL make the case inconclusive/blocked rather than verified.

#### Scenario: Assertion-only Toast cannot verify

- **WHEN** a case contains only an `assert_toast` whose evidence says `trigger_window_covered=false`
- **THEN** the case is not `verification="passed"` and is not projected as legacy `通过`

#### Scenario: Adjacent trigger Toast can verify

- **WHEN** a planned trigger is followed by a supported Toast assertion and the listener starts before the trigger
- **THEN** a true Toast result may contribute to `verification="passed"` with coverage evidence

### Requirement: Nested selector semantics are preserved

When `by_text` is supplied inside `all[]`, the agent SHALL use the nested text predicate's exact/contains mode and SHALL record that effective mode in the StepResult selector evidence.

#### Scenario: Nested exact is auditable

- **WHEN** `all[]` contains `{"by_text":"foo","match":"exact"}`
- **THEN** the action uses exact matching for that text and records `requested_match="exact"` and `effective_match="exact"`
