# driver-hypium Specification

## Purpose

HarmonyOS 真机 UI 控制：冻结 `UiDriverBase` 契约，提供可选依赖的 `HypiumDriver`、HDC 侧 CLI，以及离线测试用 `FakeUiDriver`。
## Requirements
### Requirement: UiDriverBase ABC

The system SHALL expose `hylyre.drivers.base.UiDriverBase` as an async abstract contract for HarmonyOS UI control, covering at minimum: `connect`, `close`, `start_app`, `touch` (coordinate or single selector), `input_text` (focused field or selector), and `screenshot` returning raster bytes.

#### Scenario: Touch target exclusivity

- **WHEN** a caller invokes `touch` with more than one of: coordinate pair, `by_text`, `by_id`
- **THEN** the implementation raises `ValueError` before issuing device commands

---

### Requirement: HypiumDriver adapter

The system SHALL provide `hylyre.drivers.hypium.HypiumDriver` implementing `UiDriverBase` using the optional `hypium` distribution.

#### Scenario: Lazy import without device extra

- **GIVEN** an environment where `hypium` is not installed
- **WHEN** `HypiumDriver.connect()` is awaited
- **THEN** an `ImportError` is raised with guidance to `pip install 'hylyre[device]'`

#### Scenario: No import-time hard dependency

- **GIVEN** `pip install hylyre` without extras
- **WHEN** user imports `hylyre.drivers.hypium.HypiumDriver`
- **THEN** import succeeds without importing `hypium` (defer until connect)

---

### Requirement: Device & structured AI CLI (P1)

The system SHALL ship Typer commands `hylyre device list`, `hylyre device install`, `hylyre ai tap`, and `hylyre ai input` documented in `--help`, where device install uses `hdc` and tap/input use `HypiumDriver`.

#### Scenario: Help surfaces subcommands

- **WHEN** `hylyre device --help` and `hylyre ai --help`
- **THEN** outputs list the P1 subcommands and key options

---

### Requirement: Fake UI driver for tests

The system SHALL provide `tests.contract.fakes.fake_ui_driver.FakeUiDriver` implementing `UiDriverBase` with deterministic in-memory event recording for L2/L3 tests.

#### Scenario: Contract suite passes offline

- **WHEN** CI runs `pytest` with Hypium mocked / absent
- **THEN** L1/L2/L3 UI driver tests pass and coverage gate `cov-fail-under` is satisfied

### Requirement: Toast assertion graceful degradation

`HypiumDriver.assert_toast` SHALL observe the trigger window using Hypium's supported Toast listener/check protocol, repeatedly evaluate the underlying check until `timeout`, and return success only when the real result is boolean true (or the documented positive event is observed). It SHALL preserve the original exception/return evidence, not swallow a real assertion failure inside the polling helper, and SHALL prevent framework failure-screenshot handling from dereferencing a `None` path. `on_unsupported` SHALL accept only `error` (default) or `skip`; a recognized unsupported capability may raise `StepSkipped` only for `skip`. A supported check that returns false or reaches timeout SHALL remain an assertion mismatch, never a capability skip.

#### Scenario: False Toast result is not success

- **GIVEN** `check_toast` returns `False` without throwing
- **WHEN** `assert_toast` reaches its timeout
- **THEN** it raises an assertion-classified mismatch and does not return successfully

#### Scenario: Toast listener covers the trigger window

- **GIVEN** a supported device emits a Toast immediately after the triggering action
- **WHEN** the listener is started before the action and the assertion polls within the configured timeout
- **THEN** the matching event is observed and the step returns success with channel/result evidence

#### Scenario: Unsupported capability is distinct

- **GIVEN** Hypium reports that Toast checking is unsupported
- **WHEN** `on_unsupported="skip"`
- **THEN** the driver raises `StepSkipped` with a capability classification; ordinary not-found text does not use this path

### Requirement: Driver scrolls at an agent-provided position

`HypiumDriver.mouse_scroll` SHALL only receive and act on a position (coordinates or selector); it SHALL NOT parse dump hints itself. The agent layer computes the scrollable container center from `_hylyre_hints` and passes coordinates when `at_*`/`x/y` are omitted; the driver SHALL retain the current screen-center default `(0.5, 0.5)` when no position is provided.

#### Scenario: Driver scrolls at the provided center

- **WHEN** `mouse_scroll` is invoked with an agent-computed container center
- **THEN** the scroll occurs at that position rather than failing on a missing container selector, and the driver performs no hint parsing of its own

### Requirement: HDC force-stop and shell helpers

`hylyre/drivers/hypium/hdc_cli.py` SHALL provide a generic `shell(args, serial)` and a `force_stop(bundle, serial)` that uses the positional `aa force-stop <bundle>` form (not `-b`). An argv builder SHALL be unit-testable without invoking a device.

#### Scenario: Positional force-stop argv

- **WHEN** the force-stop argv is built for a bundle and serial
- **THEN** it equals `hdc -t <serial> shell aa force-stop <bundle>` (positional bundle), constructible and assertable without running hdc

### Requirement: Hypium wait results are checked

`HypiumDriver.wait_for_selector` SHALL treat a non-`None` return from `wait_for_component` as success and `None` as a timeout/selector failure. `wait_for_selector_gone` SHALL treat `None` from `wait_for_component_disappear` as success and a non-`None` return as failure. Errors SHALL retain selector, timeout, and stable failure classification while preserving the raw return/exception for diagnostics.

#### Scenario: Wait-for None fails

- **WHEN** the underlying `wait_for_component` returns `None`
- **THEN** the adapter raises a classified selector timeout containing the selector and timeout

#### Scenario: Wait-gone object fails

- **WHEN** the underlying `wait_for_component_disappear` returns a component object
- **THEN** the adapter raises a classified selector timeout containing the selector and timeout

### Requirement: Native match pattern forwarding

For text selectors, the driver SHALL validate `match` as `exact` or `contains`, compute and expose `effective_match` (`contains` when omitted), and pass the corresponding Hypium `MatchPattern` to `BY.text`. Unknown values SHALL raise before a device command. The same mapping SHALL be used by touch, input, wait, wait-gone, swipe-area, and scroll-at selectors.

#### Scenario: Exact maps to Hypium

- **WHEN** a native text selector requests `match="exact"`
- **THEN** `BY.text` receives Hypium's exact/equality MatchPattern

#### Scenario: Contains maps to Hypium

- **WHEN** a native text selector requests `match="contains"` or omits match
- **THEN** `BY.text` receives Hypium's contains MatchPattern and evidence records the requested/effective values

#### Scenario: Unknown mode is fail-closed

- **WHEN** `match="typo"` is passed to a native selector builder
- **THEN** it raises a selector-contract error without falling back to contains

### Requirement: Stable driver failure classification

Driver-originated failures SHALL be mappable without parsing human `error` text: unsupported framework capability uses `failure_kind=capability` and `failure_code=capability_unsupported`; unavailable device uses `infrastructure/device_unavailable`; other adapter/framework errors use `infrastructure/driver_failure`; selector misses and assertion mismatches retain their respective classes.

#### Scenario: Driver error carries a stable code

- **WHEN** a Hypium command raises a non-capability adapter exception
- **THEN** the resulting StepResult records `failure_kind="infrastructure"` and `failure_code="driver_failure"`

### Requirement: Frozen native selector and Toast classifications

The Hypium adapter SHALL preserve boolean wait/Toast results, exact/contains MatchPattern forwarding, and structured selector evidence. Unsupported Toast capability SHALL be classified as `capability_unsupported` and may become `skipped` only through the planned `on_unsupported="skip"` policy; a supported false Toast result SHALL remain `assertion_mismatch`. Invalid match values SHALL be selector-classified with the existing `selector_not_found` code, not a new code.

#### Scenario: False Toast is an assertion mismatch

- **WHEN** the native Toast check returns boolean `False` through the complete observation window
- **THEN** the adapter raises an assertion mismatch with Toast channel/result evidence

#### Scenario: Unsupported Toast is distinct

- **WHEN** Hypium reports that Toast listening/checking is unsupported
- **THEN** the adapter exposes `failure_kind="capability"` and `failure_code="capability_unsupported"` without rewriting it as a normal assertion failure

#### Scenario: Invalid match does not extend the interface

- **WHEN** a native selector requests `match="starts_with"` or `match="typo"`
- **THEN** it fails before device I/O with selector classification using the frozen `selector_not_found` code
