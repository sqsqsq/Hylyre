"""L3: orchestrate a fake UI session (no Hypium, no hdc)."""

from __future__ import annotations

import pytest

from hylyre.drivers.base import UiDriverBase
from tests.contract.fakes.fake_ui_driver import FakeUiDriver


async def _smoke_session(driver: UiDriverBase) -> None:
    await driver.connect()
    await driver.start_app("com.example.demo")
    await driver.touch(by_text="允许")
    await driver.input_text("demo@example.com", by_id="email")
    assert len(await driver.screenshot()) > 10
    await driver.close()


@pytest.mark.asyncio
async def test_fake_driver_workflow() -> None:
    d = FakeUiDriver()
    await _smoke_session(d)
    assert d.events[0][0] == "connect"
    assert d.events[-1][0] == "close"
