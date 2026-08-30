## Why

The remaining review blocker exposes an information-theoretic ambiguity: a normal clickable Row containing dynamic Text and a flattened rich-text Row can have the same UI dump shape. A Row-type heuristic therefore either permits unsafe rich-text clicks or changes valid `contains` intent. The resolver needs an explicit inline-target contract signal or a real independent fragment/semantic anchor.

## What Changes

- Remove ancestor-type/Row heuristics from inline-target detection.
- Treat ordinary dynamic Text/Row `contains` as the existing normal selector behavior.
- Define `inline_target=true` as an explicit host-provided dump contract signal; real fragment bounds or semantic actions remain valid independent signals.
- Keep aggregate inline targets fail-closed when the explicit signal exists but no independently clickable fragment is available.
- Update the deterministic fixture, tests, canonical selector/API specs, migration docs, and release artifacts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `selector-resolution`: replace unreliable Row heuristics with an explicit inline-target contract signal.
- `api-agent`: preserve normal dynamic Row contains and fail closed only for explicit inline targets.
- `scenario-runner`: retain the same selector/evidence behavior through the planned-step ledger.

## Impact

Only Hylyre resolver/API tests, fixture, documentation, canonical OpenSpec, and release-src change. The host producing UI dumps must provide `inline_target=true` or independent fragment/semantic target data when it knows a substring is an inline target. Maison and real-device state are unchanged.
