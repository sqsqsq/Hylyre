## Context

A dump containing `Row(clickable=true) → Text("账户余额 100 元")` is indistinguishable from a dump containing flattened ordinary and clickable spans unless the producer supplies more information. The previous implementation used generic ancestor type as a proxy and consequently rejected valid dynamic Row `contains` actions.

## Goals / Non-Goals

**Goals:**

- Restore normal Text/Row contains semantics.
- Keep fail-closed behavior for a host-declared inline target with no fragment-level target.
- Keep the fixture representative of a dump with only an aggregate Text node while making the contract signal explicit and documented.

**Non-Goals:**

- No OCR, character-coordinate estimation, new public selector match mode, or Maison-side changes.

## Decisions

1. Remove the ancestor-type heuristic entirely. It cannot distinguish the two shapes and is not an evidence source.
2. Use the existing resolver metadata mechanism with a documented `inline_target=true` node attribute as the host contract signal. This is not a selector ledger or a second result state; it only tells the resolver that the Text node represents an inline-target intent.
3. Preserve independent `inline_fragments`/`spans` bounds and semantic-action paths. If `inline_target=true` is present and no valid fragment resolves, action resolution returns `inline_target_unresolvable`.
4. Keep unmarked Text as ordinary Text. If a host does not provide the signal or independent target, Hylyre cannot infer rich-text semantics and the host must add the signal/anchor to request fail-closed inline behavior.

## Risks / Trade-offs

- [Risk] An unmarked real rich-text dump may be treated as ordinary Text. → Document the host contract and require `inline_target=true` or an independent target for deterministic protection; do not guess from Row/Button type.
- [Risk] Existing fixtures using synthetic `rich_text` metadata become ambiguous. → Replace it with the explicitly named host contract signal and add the normal dynamic Row counterexample.

## Migration Plan

Keep trace schema `0.3-p0` and failure enums unchanged. Hosts emitting flattened rich text should add `inline_target=true` to the aggregate Text node or expose independent fragment bounds/semantic action. Normal dynamic Text/Row contains plans require no change.
