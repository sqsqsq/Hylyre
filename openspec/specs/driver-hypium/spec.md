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

`HypiumDriver.assert_toast` SHALL implement its own polling loop (honoring `timeout` and a new `poll_interval`) that repeatedly invokes the underlying toast check and catches any `TestError`/exception, converting it into a clear error and ensuring the underlying framework's failure auto-screenshot cannot crash the call with a `None` path. The `assert_toast` block SHALL accept `on_unsupported` = `error` (default) or `skip`; when the underlying check is recognized as unsupported/timed-out and `on_unsupported="skip"`, the driver path SHALL raise `StepSkipped`.

#### Scenario: Toast unsupported degrades to skip

- **GIVEN** a device/OS where the toast check returns an error
- **WHEN** `{"assert_toast":{"text":"暂不支持","timeout":3,"on_unsupported":"skip"}}` runs
- **THEN** the step raises `StepSkipped` and no `NoneType` screenshot crash occurs

#### Scenario: Toast assertion still works when supported

- **WHEN** a matching toast appears within the timeout
- **THEN** `assert_toast` returns successfully

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

