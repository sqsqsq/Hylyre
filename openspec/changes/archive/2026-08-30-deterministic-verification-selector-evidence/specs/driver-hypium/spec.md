## MODIFIED Requirements

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

## ADDED Requirements

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
