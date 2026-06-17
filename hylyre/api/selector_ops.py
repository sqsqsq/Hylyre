"""Agent helpers: rich selector touch, wait, scroll-until-visible."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from hylyre.api.exceptions import SelectorResolutionError
from hylyre.api.selector_resolve import (
    ResolvedHit,
    candidates_summary,
    has_rich_selector_fields,
    resolve_one,
    resolve_targets,
)
from hylyre.diagnostic_log import diagnostic_log
from hylyre.ui_dump_hints import parse_bounds_rect

if False:  # TYPE_CHECKING
    from hylyre.api.agent import HylyreAgent

_INPUT_SKIP_KEYS = frozenset(
    {
        "text",
        "into",
        "mode",
        "value",
        "prefer_native_text",
        "focus_wait",
    }
)


def tree_from_dump(payload: dict[str, Any]) -> dict[str, Any]:
    tree = payload.get("tree")
    if not isinstance(tree, dict):
        raise SelectorResolutionError("dump_ui payload missing tree dict")
    return tree


def pred_from_touch_block(touch: dict[str, Any]) -> dict[str, Any]:
    """Build resolver predicate from a touch block (strip touch-only keys)."""
    skip = frozenset({"x", "y", "wait_time", "scroll_into_view", "prefer_native_text"})
    return {k: v for k, v in touch.items() if k not in skip and v is not None}


def uses_resolver(touch: dict[str, Any]) -> bool:
    if touch.get("prefer_native_text") is True:
        return False
    if touch.get("by_key") is not None:
        return True
    if touch.get("by_text") is not None:
        return True
    if has_rich_selector_fields(touch):
        return True
    return False


def uses_native_only(touch: dict[str, Any]) -> bool:
    if touch.get("x") is not None and touch.get("y") is not None:
        return True
    if touch.get("by_id") is not None and not has_rich_selector_fields(touch):
        if touch.get("by_text") is None and touch.get("by_key") is None:
            return True
    if touch.get("prefer_native_text") is True and touch.get("by_text") is not None:
        return True
    return False


def pred_from_input_block(block: dict[str, Any]) -> dict[str, Any]:
    """Build resolver predicate from an input block (``into`` or top-level selectors)."""
    into = block.get("into")
    if isinstance(into, dict):
        return {k: v for k, v in into.items() if v is not None}
    return {
        k: v
        for k, v in block.items()
        if k not in _INPUT_SKIP_KEYS and v is not None
    }


def uses_resolver_for_input(block: dict[str, Any]) -> bool:
    if block.get("prefer_native_text") is True:
        return False
    if isinstance(block.get("into"), dict):
        return True
    if block.get("by_key") is not None:
        return True
    if block.get("by_type") is not None:
        return True
    if has_rich_selector_fields(block):
        return True
    return False


def uses_native_input_only(block: dict[str, Any]) -> bool:
    if uses_resolver_for_input(block):
        return False
    bt = block.get("by_text")
    bid = block.get("by_id")
    if bt is not None and bid is None:
        return True
    if bid is not None and bt is None:
        return True
    return False


async def resolve_input_hit(agent: Any, block: dict[str, Any]) -> ResolvedHit:
    payload = await agent.dump_ui()
    tree = tree_from_dump(payload)
    pred = pred_from_input_block(block)
    try:
        hit = resolve_one(tree, pred)
    except SelectorResolutionError as e:
        summary = e.candidates_summary or candidates_summary(
            resolve_targets(tree, pred)
        )
        diagnostic_log(
            f"input selector_resolve miss pred={pred!r} candidates={summary!r}"
        )
        raise
    if len(resolve_targets(tree, pred)) > 1:
        diagnostic_log(
            f"input selector_resolve multi-hit using first of "
            f"{candidates_summary(resolve_targets(tree, pred))!r}"
        )
    return hit


def _scroll_root_bounds(scroll_root: dict[str, Any]) -> str:
    attrs = scroll_root.get("attributes")
    if isinstance(attrs, dict):
        return str(attrs.get("bounds") or "")
    return ""


def _center_in_bounds(center: tuple[int, int], bounds_s: str) -> bool:
    rect = parse_bounds_rect(bounds_s if bounds_s else None)
    if rect is None:
        return False
    x, y = center
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2


def _first_hit_in_bounds(
    tree: dict[str, Any],
    pred: dict[str, Any],
    bounds_s: str,
) -> ResolvedHit | None:
    for hit in resolve_targets(tree, pred):
        if _center_in_bounds(hit.center, bounds_s):
            return hit
    return None


async def resolve_touch_hit(agent: Any, touch: dict[str, Any]) -> ResolvedHit:
    payload = await agent.dump_ui()
    tree = tree_from_dump(payload)
    pred = pred_from_touch_block(touch)
    if touch.get("by_text") is not None and not has_rich_selector_fields(touch):
        pred.setdefault("visible", True)
    try:
        hit = resolve_one(tree, pred)
    except SelectorResolutionError as e:
        summary = e.candidates_summary or candidates_summary(
            resolve_targets(tree, pred)
        )
        diagnostic_log(
            f"selector_resolve miss pred={pred!r} candidates={summary!r}"
        )
        raise
    if len(resolve_targets(tree, pred)) > 1:
        diagnostic_log(
            f"selector_resolve multi-hit using first of "
            f"{candidates_summary(resolve_targets(tree, pred))!r}"
        )
    return hit


async def wait_rich_selector(
    agent: Any,
    block: dict[str, Any],
    *,
    timeout: float,
    want_gone: bool,
    poll_interval: float = 0.4,
) -> None:
    pred = {
        k: v
        for k, v in block.items()
        if k not in ("timeout",) and v is not None
    }
    deadline = time.monotonic() + float(timeout)
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        payload = await agent.dump_ui()
        tree = tree_from_dump(payload)
        hits = resolve_targets(tree, pred)
        present = len(hits) > 0
        if want_gone and not present:
            return
        if not want_gone and present:
            return
        last_err = SelectorResolutionError(
            f"wait {'gone' if want_gone else 'for'}: target not in desired state"
        )
        await asyncio.sleep(poll_interval)
    msg = str(last_err) if last_err else f"timeout after {timeout}s"
    raise TimeoutError(msg)


async def scroll_until_visible(
    agent: Any,
    *,
    target_pred: dict[str, Any],
    container: dict[str, Any] | None,
    max_scrolls: int = 15,
    swipe_distance: int = 60,
) -> ResolvedHit:
    from hylyre.cli.commands.collect_cmd import (
        _build_swipe_payload,
        _visible_rows_fingerprint,
        find_scroll_root,
    )

    scroll_area = dict(container) if container else {"by_type": "List"}
    for i in range(max_scrolls):
        payload = await agent.dump_ui()
        tree = tree_from_dump(payload)
        scroll_root = find_scroll_root(tree, scroll_area)
        if scroll_root is None and i == 0:
            scroll_area = {"scrollable": True}  # type: ignore[assignment]
            scroll_root = find_scroll_root(tree, {"by_type": "Scroll"})
        if scroll_root is not None:
            hits = resolve_targets(scroll_root, target_pred)
            if hits:
                return hits[0]
            if i == 0:
                bounds = _scroll_root_bounds(scroll_root)
                if bounds:
                    bounded = _first_hit_in_bounds(tree, target_pred, bounds)
                    if bounded is not None:
                        return bounded
        elif i == 0 and container is None:
            # No container constraint: allow whole-tree match before first scroll.
            hits = resolve_targets(tree, target_pred)
            if hits:
                return hits[0]
        if scroll_root is None:
            break
        swipe_payload = _build_swipe_payload(
            "UP", swipe_distance, scroll_area, scroll_root
        )
        await agent.run_planned_swipe(swipe_payload)
        await asyncio.sleep(0.2)
        payload2 = await agent.dump_ui()
        tree2 = tree_from_dump(payload2)
        fp = _visible_rows_fingerprint(tree2, scroll_area, None)
        _ = fp  # bounce detection optional
    raise SelectorResolutionError(
        f"scroll_until_visible: target not found after {max_scrolls} scrolls",
        candidates_summary=[],
    )
