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
        wait_time: float = 0.1,
    ) -> None:
        self._validate_touch_kwargs(
            x=x, y=y, by_text=by_text, by_id=by_id
        )
        self.events.append(
            (
                "touch",
                {
                    "x": x,
                    "y": y,
                    "by_text": by_text,
                    "by_id": by_id,
                    "wait_time": wait_time,
                },
            )
        )

    async def input_text(
        self,
        text: str,
        *,
        by_text: str | None = None,
        by_id: str | None = None,
        mode: Any | None = None,
    ) -> None:
        if by_text is not None and by_id is not None:
            raise ValueError("pass at most one of by_text or by_id")
        self.events.append(
            (
                "input_text",
                {
                    "text": text,
                    "by_text": by_text,
                    "by_id": by_id,
                    "mode": mode,
                },
            )
        )

    async def screenshot(self) -> bytes:
        self.events.append(("screenshot", {}))
        # 1×1 transparent PNG (valid minimal payload for tests)
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    async def dump_ui(self) -> dict[str, Any]:
        self.events.append(("dump_ui", {}))
        return {
            "schema_version": "hylyre-fake-ui-dump-v1",
            "source": "fake",
            "tree": {"type": "fake_root", "children": []},
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
        area_scrollable: bool | None = None,
        side: str | None = None,
        start_point: tuple[float | int, float | int] | None = None,
        swipe_time: float = 0.3,
        speed: int | None = None,
    ) -> None:
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
        at_scrollable: bool | None = None,
        key1: int | None = None,
        key2: int | None = None,
    ) -> None:
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
                    "timeout": timeout,
                },
            )
        )

    async def wait_for_selector_gone(
        self,
        *,
        by_text: str | None = None,
        by_id: str | None = None,
        by_type: str | None = None,
        by_key: str | None = None,
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
                    "timeout": timeout,
                },
            )
        )

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
    ) -> None:
        self.events.append(
            (
                "assert_toast",
                {"text": text, "timeout": timeout, "fuzzy": fuzzy},
            )
        )
