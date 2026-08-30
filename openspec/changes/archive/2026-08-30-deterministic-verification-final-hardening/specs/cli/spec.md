## ADDED Requirements

### Requirement: Batch execution count excludes blocked ledger rows

The CLI batch result SHALL retain blocked suffix rows in `results[]` but SHALL report `executed` as the number of planned operations actually dispatched before the abort.

#### Scenario: Abort count remains actual

- **WHEN** the first of two steps fails and the second is only represented as blocked
- **THEN** the result reports `executed=1` and contains two result rows
