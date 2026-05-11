"""L3: orchestrate fake mock controller."""

from __future__ import annotations

import pytest

from hylyre.drivers.base import MockControllerBase
from tests.contract.fakes.fake_mock_controller import FakeMockController


async def _workflow(ctrl: MockControllerBase) -> None:
    await ctrl.start_local(mock_port=1)
    await ctrl.activate_group("g")
    assert await ctrl.list_activated_groups()
    await ctrl.deactivate_all()
    await ctrl.stop_local()


@pytest.mark.asyncio
async def test_fake_mock_workflow() -> None:
    m = FakeMockController()
    await _workflow(m)
    assert m.events[-1][0] == "stop_local"
