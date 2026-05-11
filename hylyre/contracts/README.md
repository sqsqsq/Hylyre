# Hylyre output contracts (SSOT)

This directory defines **Hylyre-owned** constraints for generated artifacts (`test-report.md`, `trace.json`).  
Consumer repos (e.g. SimulatedWalletForHmos `framework/`) may have their own harness rules; Hylyre uses **compatibility mirroring** in CI (soft warning) without importing their code.

## Files

- `output-schema.json` — JSON Schema for `trace.json` (expand toward full harness schema in P4).
- `report-sections.yaml` — Required Markdown sections and allowed status/verdict enums.

## Change process

1. Propose via OpenSpec change under `openspec/changes/*/specs/contracts/`.
2. Update this directory and `tests/schema/` together.
3. Run `pytest` and `hylyre report verify` (P4+) before merging.
