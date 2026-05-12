"""Hypium-backed UiDriver (optional dependency: pip install 'hylyre[device]')."""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from types import ModuleType
from typing import Any, Callable, TypeVar

from hylyre.drivers.base.ui_driver import UiDriverBase

_T = TypeVar("_T")


@dataclass(frozen=True)
class _HypiumShim:
    """Resolved Hypium imports (lazy)."""

    hypium_mod: ModuleType
    UiDriver: Any
    BY: Any


_hypium_singleton: _HypiumShim | None = None


def load_hypium_shim() -> _HypiumShim:
    """Import Hypium lazily so `hylyre` installs without the device extra."""
    global _hypium_singleton
    if _hypium_singleton is None:
        try:
            hypium_mod = importlib.import_module("hypium")
        except ImportError as e:  # pragma: no cover - message only
            raise ImportError(
                "Hypium is not installed. Install the device extra: "
                "pip install 'hylyre[device]'"
            ) from e
        UiDriver = getattr(hypium_mod, "UiDriver")
        BY = getattr(hypium_mod, "BY")
        _hypium_singleton = _HypiumShim(
            hypium_mod=hypium_mod, UiDriver=UiDriver, BY=BY
        )
    return _hypium_singleton


def reset_hypium_shim_for_tests() -> None:
    """Test hook: clear lazy Hypium singleton."""
    global _hypium_singleton
    _hypium_singleton = None


async def _to_thread(fn: Callable[..., _T], /, *args: Any, **kwargs: Any) -> _T:
    return await asyncio.to_thread(fn, *args, **kwargs)


class HypiumDriver(UiDriverBase):
    def __init__(
        self,
        *,
        device_sn: str | None = None,
        log_level: str = "info",
        connect_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._device_sn = device_sn
        self._log_level = log_level
        self._extra_connect = connect_kwargs or {}
        self._raw: Any | None = None

    @property
    def raw(self) -> Any | None:
        """Underlying hypium.UiDriver instance (set after connect)."""
        return self._raw

    async def connect(self) -> None:
        shim = load_hypium_shim()
        if self._raw is not None:
            return

        def _connect() -> Any:
            kwargs: dict[str, Any] = {
                "log_level": self._log_level,
                **self._extra_connect,
            }
            if self._device_sn is not None:
                kwargs["device_sn"] = self._device_sn
            return shim.UiDriver.connect(connector="hdc", **kwargs)

        self._raw = await _to_thread(_connect)

    async def close(self) -> None:
        if self._raw is None:
            return
        raw = self._raw
        self._raw = None
        await _to_thread(raw.close)

    async def start_app(
        self,
        bundle: str,
        *,
        page_name: str | None = None,
        params: str = "",
        wait_time: float = 1.0,
    ) -> None:
        await self._require_raw()
        raw = self._raw
        await _to_thread(
            lambda: raw.start_app(
                bundle, page_name, params, wait_time
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
        await self._require_raw()
        shim = load_hypium_shim()
        raw = self._raw
        if x is not None and y is not None:
            target = (int(x), int(y))
        elif by_text is not None:
            target = shim.BY.text(by_text)
        else:
            target = shim.BY.id(by_id)
        wt = float(wait_time)
        await _to_thread(
            lambda: raw.touch(
                target,
                mode="normal",
                scroll_target=None,
                wait_time=wt,
                offset=None,
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
        await self._require_raw()
        raw = self._raw
        if by_text is None and by_id is None:
            await _to_thread(lambda: raw.input_text_on_current_cursor(text))
            return
        shim = load_hypium_shim()
        if by_text is not None and by_id is not None:
            raise ValueError("pass at most one of by_text or by_id")
        selector = shim.BY.text(by_text) if by_text is not None else shim.BY.id(by_id)
        component = await _to_thread(
            lambda: raw.find_component(selector)
        )
        await _to_thread(
            lambda: raw.input_text(component, text, mode)
        )

    async def screenshot(self) -> bytes:
        await self._require_raw()
        raw = self._raw
        with NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            path = Path(tmp.name)
        try:
            await _to_thread(
                lambda: raw.capture_screen(str(path), True, None)
            )
            return await _to_thread(path.read_bytes)
        finally:
            path.unlink(missing_ok=True)

    async def install_app(self, hap_path: str | Path, **kwargs: Any) -> None:
        """Install a .hap from the host via Hypium (uses hdc under the hood)."""
        await self._require_raw()
        raw = self._raw
        hap = str(hap_path)
        await _to_thread(lambda: raw.install_app(hap, "", **kwargs))

    async def _require_raw(self) -> None:
        if self._raw is None:
            raise RuntimeError("UiDriver is not connected; call connect() first")
