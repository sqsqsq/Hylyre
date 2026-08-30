## Context

The current result chain is structurally unified, but its verdict and selector metadata still allow evidence to describe a condition that the result accepts as verified. Rich-text detection also relied on a marker not present in the source incident, and scroll-to used a validated hit only as a count check before a separate DFS lookup.

## Goals / Non-Goals

**Goals:**

- Treat Toast observation without a pre-action listener as non-verifying evidence.
- Apply one effective match to the actual target subpredicate and serialize that mode.
- Return the exact resolved container node for scroll-to execution.
- Preserve the causal failure kind/code for blocked suffixes and report actual execution count.

**Non-Goals:**

- No new match mode, failure-code enum, OCR, glyph layout, selector ledger, or evidence sidecar.
- No Maison or real-device changes.

## Decisions

1. **Toast gate in the verdict model.** A passing `assert_toast` step must carry `trigger_window_covered=true`; otherwise it is not an eligible passing assertion. The step remains observable, but the case becomes inconclusive rather than silently upgrading evidence.

2. **Conservative aggregate-text inference.** A Text node with a contains submatch that is a strict substring of its full text is treated as potentially addressing an inline fragment. This preserves the original incident shape without a synthetic marker. Exact full-node text remains an ordinary Text target; explicit valid fragment metadata still wins.

3. **Nested match inheritance.** The resolver derives match from the `by_text` subpredicate inside `all[]` when present. If that subpredicate omits match, the top-level effective mode is inherited; evidence records the requested/effective pair actually used for text matching.

4. **Container node identity.** Add a pure resolver helper that maps a unique hit back to its node, then pass that node into scroll-to's existing in-container loop. The old `find_container_root` first-DFS path is retained only for unrelated collection utilities.

5. **Separate actual count from ledger count.** Batch output `executed` increments only after an operation is dispatched; blocked rows are appended for audit but do not increment it. The full `results` array remains the complete ledger projection.

## Risks / Trade-offs

- [Risk] Ordinary substring Text actions may become conservative when the dump lacks fragment metadata. → Require a real clickable ancestor and make the behavior explicit; callers can use an exact full-node selector or a real fragment target.
- [Risk] Existing reports relying on assertion-only Toast pass will change verdict. → Keep the step and evidence, mark the case inconclusive, and document the required adjacent trigger+assert batch.
- [Risk] Resolver node mapping could be invalid for a malformed tree. → Validate tree index and raise the existing selector failure instead of falling back to DFS.

## Migration Plan

Keep trace schema `0.3-p0` and the frozen failure codes. Consumers must treat `assert_toast` evidence with `trigger_window_covered=false` as non-verifying. Existing legacy schemas remain legacy and are not rewritten.
