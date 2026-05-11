## ADDED Requirements

### Requirement: Output contracts SSOT

The system SHALL version output shapes under `hylyre/contracts/`:

- `output-schema.json` validating minimal `trace.json` fields in P0; expanded in P4.
- `report-sections.yaml` enumerating required Markdown report sections and status/verdict enums.

#### Scenario: Schema load test

- GIVEN CI runs `tests/schema/test_contracts_loadable.py`
- WHEN contracts are present
- THEN JSON Schema draft 2020-12 validates and YAML parses
