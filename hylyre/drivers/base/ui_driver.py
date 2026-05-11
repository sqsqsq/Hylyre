"""Abstract UI driver (HarmonyOS / Hypium facade)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


def _exactly_one_touch_target(
    *,
    x: int | None,
    y: int | None,
    by_text: str | None,
    by_id: str | None,
) -> None:
    has_coord = x is not None and y is not None
    has_partial_coord = (x is not None) ^ (y is not None)
    if has_partial_coord:
        raise ValueError("touch coordinates require both x and y")
    n = sum([has_coord, by_text is not None, by_id is not None])
    if n != 1:
        raise ValueError(
            "touch requires exactly one of: (x and y), by_text, or by_id"
        )


class UiDriverBase(ABC):
    """Minimal async surface for P1 (Hypium-backed + fakes)."""

    @abstractmethod
    async def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def start_app(
        self,
        bundle: str,
        *,
        page_name: str | None = None,
        params: str = "",
        wait_time: float = 1.0,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def touch(
        self,
        *,
        x: int | None = None,
        y: int | None = None,
        by_text: str | None = None,
        by_id: str | None = None,
        wait_time: float = 0.1,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def input_text(
        self,
        text: str,
        *,
        by_text: str | None = None,
        by_id: str | None = None,
        mode: Any | None = None,
    ) -> None:
        """If both selectors are omitted, implementations may use current cursor / focused field."""
        raise NotImplementedError

    @abstractmethod
    async def screenshot(self) -> bytes:
        """PNG bytes (or another raster format) for screenshots."""
        raise NotImplementedError

    def _validate_touch_kwargs(
        self,
        *,
        x: int | None,
        y: int | None,
        by_text: str | None,
        by_id: str | None,
    ) -> None:
        _exactly_one_touch_target(x=x, y=y, by_text=by_text, by_id=by_id)
