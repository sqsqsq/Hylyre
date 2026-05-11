## ADDED Requirements

### Requirement: Lyrebird controller

The system SHALL provide `hylyre.drivers.lyrebird` implementing lifecycle and mock group control against Lyrebird HTTP API (P2).

#### Scenario: Optional extra

- GIVEN install without `[mock]` extra
- WHEN outer facade is imported
- THEN `lyrebird` is not required (P2 enforces)
