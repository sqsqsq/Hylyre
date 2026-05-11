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
