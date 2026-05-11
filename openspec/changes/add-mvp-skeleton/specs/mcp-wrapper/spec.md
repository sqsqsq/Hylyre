## ADDED Requirements

### Requirement: MCP thin wrapper

The system SHALL expose `hylyre mcp serve` wiring a small curated tool set (≤8) mirroring CLI subsets (P5).

#### Scenario: P0 placeholder

- GIVEN `hylyre mcp serve` in P0
- WHEN invoked
- THEN command prints not-implemented placeholder without crashing Typer
