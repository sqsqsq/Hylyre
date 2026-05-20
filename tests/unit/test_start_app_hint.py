"""Unit tests for start_app failure hints."""

from __future__ import annotations

import pytest

from hylyre.api.agent import HylyreAgent, _start_app_failure_hint
from tests.contract.fakes.fake_ui_driver import FakeUiDriver


class _FailingStartAppDriver(FakeUiDriver):
    async def start_app(
        self,
        bundle: str,
        *,
        page_name: str | None = None,
        params: str = "",
        wait_time: float = 1.0,
    ) -> None:
        raise RuntimeError("hypium refused")


def test_start_app_failure_hint_without_page_name() -> None:
    msg = _start_app_failure_hint("com.example.app", None)
    assert "--page-name" in msg
    assert "hdc shell aa start" in msg


@pytest.mark.asyncio
async def test_agent_start_app_wraps_driver_error() -> None:
    ag = HylyreAgent(ui=_FailingStartAppDriver())
    try:
        with pytest.raises(RuntimeError, match="start_app failed"):
            await ag.start_app("com.example.app")
    finally:
        await ag.aclose()
