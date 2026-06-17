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

`HylyreAgent` planned tap (`run_planned_tap` and the `touch` block via `_apply_touch_block`) SHALL route by selector type: coordinates (`x/y`) and `by_id` use the native `UiDriverBase.touch`; `by_key` and any rich predicate (`scope`, `within`, `below/above/after/before`, `index`, `all`, `by_type`, `visible/clickable/enabled`, `scroll_into_view`) resolve via `resolve_targets` and click the resulting center; `by_text` SHALL by default resolve via `dump_ui` + `resolve_targets` (selecting the top-overlay clickable hit), falling back to a single native attempt only when resolution yields zero hits. The legacy `action` envelope with `type="touch"` SHALL forward the whole block (minus `type`) to `_apply_touch_block` so rich fields are not dropped. An opt-out `prefer_native_text` SHALL restore native `by_text` behavior.

#### Scenario: by_text avoids occluded duplicate by default

- **GIVEN** a half-sheet overlay covers a page that has an identically-named button
- **WHEN** a `{"touch":{"by_text":"下一步"}}` step runs
- **THEN** the agent resolves against the dump and taps the overlay's button (not the occluded one) without the plan specifying any id

#### Scenario: Legacy action carries rich fields

- **WHEN** `{"action":{"type":"touch","by_text":"下一步","scope":"top_overlay"}}` runs
- **THEN** the tap is resolved via `resolve_targets` (coordinate tap), not native `by_text`

#### Scenario: by_key resolves to coordinates

- **WHEN** a `{"touch":{"by_key":"..."}}` step runs
- **THEN** the agent resolves a center via `resolve_targets` and calls `UiDriverBase.touch(x, y)` (no `by_key` argument is added to the driver surface)

### Requirement: wait_for and wait_gone accept rich selectors

`HylyreAgent` `wait_for` / `wait_gone` SHALL, when the block contains rich selector fields, poll `dump_ui` + `resolve_targets` until the target appears (or disappears) or the timeout elapses; single-attribute blocks SHALL continue to use the native Hypium wait.

#### Scenario: Wait for a control inside the top overlay

- **WHEN** `{"wait_for":{"by_text":"提交","scope":"top_overlay","timeout":10}}` runs
- **THEN** the agent polls the dump and returns once a matching hit exists in the top overlay

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

