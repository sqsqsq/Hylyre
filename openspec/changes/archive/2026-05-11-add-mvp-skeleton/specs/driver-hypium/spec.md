## ADDED Requirements

### Requirement: Hypium driver adapter

The system SHALL provide `hylyre.drivers.hypium` implementing `UiDriverBase` for Hypium-backed device control (P1).

#### Scenario: Optional extra

- GIVEN install without `[device]` extra
- WHEN inner package is imported
- THEN no hard dependency on `hypium` at import time of outer facade (P1 enforces)
