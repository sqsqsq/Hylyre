# driver-lyrebird Specification

## Purpose

HTTP Mock 侧 Lyrebird 适配：`MockControllerBase` / `LyrebirdController`（生命周期、分组、数据、抓包）；P2 实装。

## Requirements
### Requirement: Lyrebird controller

The system SHALL provide `hylyre.drivers.lyrebird` implementing lifecycle and mock group control against Lyrebird HTTP API (P2).

#### Scenario: Optional extra

- GIVEN install without `[mock]` extra
- WHEN outer facade is imported
- THEN `lyrebird` is not required (P2 enforces)

