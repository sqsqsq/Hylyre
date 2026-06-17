## ADDED Requirements

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
