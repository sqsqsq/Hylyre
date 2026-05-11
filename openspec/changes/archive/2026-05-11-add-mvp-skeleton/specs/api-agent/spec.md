## ADDED Requirements

### Requirement: HylyreAgent public surface

The system SHALL expose a Midscene-aligned Python API (`ai_action`, `ai_query`, `ai_assert`, `ai_tap`, `ai_input`, `ai_wait_for`, `ai_locate`) on a single entry type `HylyreAgent`.

#### Scenario: Import path stable

- GIVEN a consumer imports `hylyre.api` after install
- WHEN the package is at version 0.1.x
- THEN `HylyreAgent` symbol is available without importing vendor SDKs from outer layer
