"""L2: FakeUiDriver implements UiDriverBase."""

from __future__ import annotations

import pytest

from hylyre.drivers.base import UiDriverBase
from tests.contract.fakes.fake_ui_driver import FakeUiDriver


def test_fake_ui_driver_is_ui_driver_base() -> None:
    d = FakeUiDriver()
    assert isinstance(d, UiDriverBase)


@pytest.mark.asyncio
async def test_fake_ui_driver_touch_validation() -> None:
    d = FakeUiDriver()
    with pytest.raises(ValueError):
        await d.touch(x=1, y=None)
    with pytest.raises(ValueError):
        await d.touch(by_text="a", by_id="b")


@pytest.mark.asyncio
async def test_fake_ui_driver_records_events() -> None:
    d = FakeUiDriver()
    await d.connect()
    await d.start_app("com.example.app", page_name="MainAbility")
    await d.touch(x=10, y=20)
    await d.input_text("hello", by_text="field")
    png = await d.screenshot()
    await d.close()
    assert png.startswith(b"\x89PNG")
    kinds = [e[0] for e in d.events]
    assert kinds == [
        "connect",
        "start_app",
        "touch",
        "input_text",
        "screenshot",
        "close",
    ]
