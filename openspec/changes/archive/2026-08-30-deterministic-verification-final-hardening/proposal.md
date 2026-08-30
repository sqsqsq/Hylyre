## Why

The final review found four remaining semantic holes in the deterministic evidence contract: standalone Toast assertions could pass without trigger-window coverage, aggregate rich text depended on an artificial dump marker, nested `all` selectors lost their match mode, and `scroll_to.in` validated one container but executed another. A compatibility regression also made `executed` count ledger rows rather than operations that actually ran.

## What Changes

- **BREAKING** Require Toast trigger-window coverage for a Toast assertion to qualify a case for verified pass; an assertion-only Toast result is blocked/inconclusive.
- Detect aggregate rich-text ambiguity from the original single-Text concatenated form without requiring synthetic metadata, including when `by_text` is nested inside `all[]`.
- Resolve and record the effective match from the actual text subpredicate in `all[]`, with top-level match acting only when no text subpredicate supplies one.
- Carry the unique `scroll_to.in` resolver hit into execution so rich scope/within/all constraints cannot be replaced by first-DFS container lookup.
- Preserve the root failure classification on blocked suffix rows and keep `executed` equal to the number of operations actually attempted.
- Add targeted review regressions and update the canonical specs and migration notes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-agent`: require Toast coverage and preserve nested selector semantics.
- `selector-resolution`: infer aggregate rich text conservatively, propagate nested match, and expose selected container nodes.
- `scenario-runner`: gate Toast verification and preserve blocked-root classification.
- `cli`: keep actual execution count separate from complete ledger row count.
- `contracts`: document Toast coverage as a verification prerequisite.

## Impact

Changes are limited to Hylyre API/resolver/runner/CLI contracts, tests, docs, and canonical OpenSpec. No Maison files or Hypium package are modified. The release remains unpublished and real-device acceptance remains separately pending.
