"""In-memory UiDriver for L2/L3 tests (no device, no Hypium)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hylyre.drivers.base import UiDriverBase

FakeEvent = tuple[str, dict[str, Any]]


@dataclass
class FakeUiDriver(UiDriverBase):
    """Records operations for assertions; screenshot returns a tiny synthetic PNG."""

    connected: bool = False
    events: list[FakeEvent] = field(default_factory=list)
    dump_tree: dict[str, Any] | None = None
    fail_touch_by_text: set[str] = field(default_factory=set)
    native_locate_by_text: dict[str, tuple[int, int]] = field(default_factory=dict)
    toast_results: list[bool] = field(default_factory=list)
    toast_unsupported: bool = False
    toast_listening: bool = False

    async def connect(self) -> None:
        self.connected = True
        self.events.append(("connect", {}))

    async def close(self) -> None:
        self.connected = False
        self.events.append(("close", {}))

    async def start_app(
        self,
        bundle: str,
        *,
        page_name: str | None = None,
        params: str = "",
        wait_time: float = 1.0,
    ) -> None:
        self.events.append(
            (
                "start_app",
                {
                    "bundle": bundle,
                    "page_name": page_name,
                    "params": params,
                    "wait_time": wait_time,
                },
            )
        )

    async def touch(
        self,
        *,
        x: int | None = None,
        y: int | None = None,
        by_text: str | None = None,
        by_id: str | None = None,
        match: str | None = None,
        wait_time: float = 0.1,
        mode: str = "normal",
        press_time: float | None = None,
    ) -> None:
        from hylyre.api.selector_contract import normalize_match

        normalize_match(match)
        self._validate_touch_kwargs(
            x=x, y=y, by_text=by_text, by_id=by_id
        )
        resolved_center: tuple[int, int] | None = None
        if self.dump_tree is not None and (by_text is not None or by_id is not None):
            from hylyre.api.selector_resolve import resolve_action_one

            payload = await self.dump_ui()
            hit = resolve_action_one(
                payload["tree"],
                {
                    key: value
                    for key, value in {
                        "by_text": by_text,
                        "by_id": by_id,
                        "match": match,
                    }.items()
                    if value is not None
                },
            )
            resolved_center = hit.center
        if by_text is not None and by_text in self.fail_touch_by_text:
            raise RuntimeError(f"Can't find component with [BY.text('{by_text}')]")
        event = {
            "x": x,
            "y": y,
            "by_text": by_text,
            "by_id": by_id,
            "wait_time": wait_time,
        }
        if mode != "normal":
            event["mode"] = mode
        if press_time is not None:
            event["press_time"] = press_time
        if match is not None:
            event["match"] = match
        if resolved_center is not None:
            event["resolved_center"] = list(resolved_center)
        self.events.append(("touch", event))

    async def locate_by_text(
        self, *, by_text: str, match: str | None = None
    ) -> tuple[int, int] | None:
        text = str(by_text)
        if text in self.native_locate_by_text:
            return self.native_locate_by_text[text]
        payload = await self.dump_ui()
        tree = payload.get("tree")
        if not isinstance(tree, dict):
            return None
        from hylyre.api.exceptions import SelectorResolutionError
        from hylyre.api.selector_resolve import resolve_one

        try:
            hit = resolve_one(tree, {"by_text": text, "match": match})
        except SelectorResolutionError:
            return None
        return hit.center

    async def input_text(
        self,
        text: str,
        *,
        by_text: str | None = None,
        by_id: str | None = None,
        match: str | None = None,
        mode: Any | None = None,
    ) -> None:
        from hylyre.api.selector_contract import normalize_match

        normalize_match(match)
        if by_text is not None and by_id is not None:
            raise ValueError("pass at most one of by_text or by_id")
        if self.dump_tree is not None and (by_text is not None or by_id is not None):
            from hylyre.api.selector_resolve import resolve_action_one

            payload = await self.dump_ui()
            resolve_action_one(
                payload["tree"],
                {
                    key: value
                    for key, value in {
                        "by_text": by_text,
                        "by_id": by_id,
                        "match": match,
                    }.items()
                    if value is not None
                },
            )
        event = {
            "text": text,
            "by_text": by_text,
            "by_id": by_id,
            "mode": mode,
        }
        if match is not None:
            event["match"] = match
        self.events.append(("input_text", event))

    async def screenshot(self) -> bytes:
        self.events.append(("screenshot", {}))
        from tests.image_samples import png_bytes

        return png_bytes()

    async def dump_ui(self) -> dict[str, Any]:
        self.events.append(("dump_ui", {}))
        tree = self.dump_tree if self.dump_tree is not None else {
            "type": "fake_root",
            "attributes": {"type": "Root", "bounds": "[0,0][500,500]"},
            "children": [],
        }
        if "attributes" not in tree and "children" in tree:
            pass
        if "attributes" not in tree:
            tree = {
                "attributes": {"type": "Root", "bounds": "[0,0][500,500]"},
                "children": [tree] if tree else [],
            }
        return {
            "schema_version": "hylyre-fake-ui-dump-v1",
            "source": "fake",
            "tree": tree,
        }

    async def swipe(
        self,
        *,
        direction: str,
        distance: int = 60,
        area_by_text: str | None = None,
        area_by_id: str | None = None,
        area_by_type: str | None = None,
        area_by_key: str | None = None,
        area_match: str | None = None,
        area_scrollable: bool | None = None,
        side: str | None = None,
        start_point: tuple[float | int, float | int] | None = None,
        swipe_time: float = 0.3,
        speed: int | None = None,
    ) -> None:
        from hylyre.api.selector_contract import normalize_match

        normalize_match(area_match)
        self.events.append(
            (
                "swipe",
                {
                    "direction": direction,
                    "distance": distance,
                    "area_by_text": area_by_text,
                    "area_by_id": area_by_id,
                    "area_by_type": area_by_type,
                    "area_by_key": area_by_key,
                    "area_match": area_match,
                    "area_scrollable": area_scrollable,
                    "side": side,
                    "start_point": start_point,
                    "swipe_time": swipe_time,
                    "speed": speed,
                },
            )
        )

    async def mouse_scroll(
        self,
        *,
        direction: str,
        steps: int,
        x: int | None = None,
        y: int | None = None,
        at_by_text: str | None = None,
        at_by_id: str | None = None,
        at_by_type: str | None = None,
        at_by_key: str | None = None,
        at_match: str | None = None,
        at_scrollable: bool | None = None,
        key1: int | None = None,
        key2: int | None = None,
    ) -> None:
        from hylyre.api.selector_contract import normalize_match

        normalize_match(at_match)
        self.events.append(
            (
                "mouse_scroll",
                {
                    "direction": direction,
                    "steps": steps,
                    "x": x,
                    "y": y,
                    "at_by_text": at_by_text,
                    "at_by_id": at_by_id,
                    "at_by_type": at_by_type,
                    "at_by_key": at_by_key,
                    "at_match": at_match,
                    "at_scrollable": at_scrollable,
                    "key1": key1,
                    "key2": key2,
                },
            )
        )

    async def press_back(
        self,
        *,
        times: int = 1,
        mode: str = "key",
        side: str = "RIGHT",
        height: float = 0.5,
    ) -> None:
        self.events.append(
            (
                "press_back",
                {
                    "times": times,
                    "mode": mode,
                    "side": side,
                    "height": height,
                },
            )
        )

    async def press_home(self) -> None:
        self.events.append(("press_home", {}))

    async def stop_app(self, bundle: str, *, wait_time: float = 0.5) -> None:
        self.events.append(
            ("stop_app", {"bundle": bundle, "wait_time": wait_time})
        )

    async def clear_app_data(self, bundle: str) -> None:
        self.events.append(("clear_app_data", {"bundle": bundle}))

    async def wait_seconds(self, seconds: float) -> None:
        self.events.append(("wait_seconds", {"seconds": seconds}))

    async def wait_for_selector(
        self,
        *,
        by_text: str | None = None,
        by_id: str | None = None,
        by_type: str | None = None,
        by_key: str | None = None,
        match: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.events.append(
            (
                "wait_for_selector",
                {
                    "by_text": by_text,
                    "by_id": by_id,
                    "by_type": by_type,
                    "by_key": by_key,
                    "match": match,
                    "timeout": timeout,
                },
            )
        )
        if self.dump_tree is not None:
            from hylyre.api.selector_resolve import resolve_targets
            from hylyre.api.selector_contract import selector_evidence

            pred = {
                k: v
                for k, v in {
                    "by_text": by_text,
                    "by_id": by_id,
                    "by_type": by_type,
                    "by_key": by_key,
                    "match": match,
                }.items()
                if v is not None
            }
            payload = await self.dump_ui()
            hits = resolve_targets(payload["tree"], pred)
            if not hits:
                from hylyre.api.exceptions import SelectorResolutionError

                raise SelectorResolutionError(
                    f"wait_for timeout for selector {pred!r} after {timeout}s",
                    selector=selector_evidence(
                        pred, engine="fake", candidate_count=0
                    ),
                )
            return {
                "selector": selector_evidence(
                    pred,
                    engine="fake",
                    candidate_count=len(hits),
                    selected_id=hits[0].id or None,
                    bounds=hits[0].tap_bounds,
                ),
                "evidence": {"assertion": "presence", "observed_present": True},
            }

    async def wait_for_selector_gone(
        self,
        *,
        by_text: str | None = None,
        by_id: str | None = None,
        by_type: str | None = None,
        by_key: str | None = None,
        match: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.events.append(
            (
                "wait_for_selector_gone",
                {
                    "by_text": by_text,
                    "by_id": by_id,
                    "by_type": by_type,
                    "by_key": by_key,
                    "match": match,
                    "timeout": timeout,
                },
            )
        )
        if self.dump_tree is not None:
            from hylyre.api.selector_resolve import resolve_targets
            from hylyre.api.selector_contract import selector_evidence
            from hylyre.api.exceptions import AssertionMismatch

            pred = {
                k: v
                for k, v in {
                    "by_text": by_text,
                    "by_id": by_id,
                    "by_type": by_type,
                    "by_key": by_key,
                    "match": match,
                }.items()
                if v is not None
            }
            payload = await self.dump_ui()
            hits = resolve_targets(payload["tree"], pred)
            if hits:
                raise AssertionMismatch(
                    f"wait_gone timeout for selector {pred!r} after {timeout}s",
                    selector=selector_evidence(
                        pred, engine="fake", candidate_count=len(hits)
                    ),
                    evidence={
                        "assertion": "absence",
                        "observed_present": True,
                        "candidate_count": len(hits),
                    },
                )
            return {
                "selector": selector_evidence(
                    pred, engine="fake", candidate_count=0
                ),
                "evidence": {
                    "assertion": "absence",
                    "observed_present": False,
                    "candidate_count": 0,
                },
            }

    async def wait_for_idle(
        self,
        *,
        idle_time: float = 0.7,
        timeout: float = 10.0,
    ) -> None:
        self.events.append(
            (
                "wait_for_idle",
                {"idle_time": idle_time, "timeout": timeout},
            )
        )

    async def assert_toast(
        self,
        text: str,
        *,
        timeout: float = 3.0,
        fuzzy: str = "equal",
        poll_interval: float = 0.3,
        on_unsupported: str = "error",
    ) -> dict[str, Any]:
        self.events.append(
            (
                "assert_toast",
                {
                    "text": text,
                    "timeout": timeout,
                    "fuzzy": fuzzy,
                    "poll_interval": poll_interval,
                    "on_unsupported": on_unsupported,
                },
            )
        )
        if self.toast_unsupported:
            from hylyre.api.exceptions import CapabilityUnsupported, StepSkipped

            if on_unsupported == "skip":
                raise StepSkipped("fake Toast capability unsupported")
            raise CapabilityUnsupported("fake Toast capability unsupported")
        result = self.toast_results.pop(0) if self.toast_results else True
        return {
            "channel": "fake.toast",
            "listener_started": self.toast_listening,
            "expected_text": text,
            "result": result,
        }

    async def start_toast_listening(self) -> dict[str, Any]:
        if self.toast_unsupported:
            from hylyre.api.exceptions import CapabilityUnsupported

            raise CapabilityUnsupported(
                "fake Toast capability unsupported",
                evidence={
                    "channel": "fake.toast",
                    "listener_started": False,
                },
            )
        self.toast_listening = True
        self.events.append(("start_toast_listening", {}))
        return {"channel": "fake.toast", "listener_started": True}

    async def drag(self, **kwargs: Any) -> None:
        self.events.append(("drag", kwargs))

    async def slide(self, **kwargs: Any) -> None:
        self.events.append(("slide", kwargs))

    async def fling(self, **kwargs: Any) -> None:
        self.events.append(("fling", kwargs))

    async def pinch_in(self, **kwargs: Any) -> None:
        self.events.append(("pinch_in", kwargs))

    async def pinch_out(self, **kwargs: Any) -> None:
        self.events.append(("pinch_out", kwargs))

    async def two_finger_swipe(self, **kwargs: Any) -> None:
        self.events.append(("two_finger_swipe", kwargs))

    async def multi_finger_touch(self, **kwargs: Any) -> None:
        self.events.append(("multi_finger_touch", kwargs))

    async def gesture(self, **kwargs: Any) -> None:
        self.events.append(("gesture", kwargs))

    async def press_key(self, **kwargs: Any) -> None:
        self.events.append(("press_key", kwargs))

    async def press_combination_key(self, **kwargs: Any) -> None:
        self.events.append(("press_combination_key", kwargs))

    async def clear_text(self, **kwargs: Any) -> None:
        self.events.append(("clear_text", kwargs))

    async def move_cursor(self, **kwargs: Any) -> None:
        self.events.append(("move_cursor", kwargs))

    async def recent_tasks(self, **kwargs: Any) -> None:
        self.events.append(("recent_tasks", kwargs))
