"""L2: FakeMockController vs MockControllerBase."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hylyre.drivers.base import MockControllerBase
from tests.contract.fakes.fake_mock_controller import FakeMockController


def test_fake_is_mock_base() -> None:
    m = FakeMockController()
    assert isinstance(m, MockControllerBase)


@pytest.mark.asyncio
async def test_fake_records_flow(tmp_path: Path) -> None:
    m = FakeMockController()
    await m.start_local(data_root=tmp_path, mock_port=9999)
    await m.activate_group("checkout")
    m.seed_flow({"id": "1"})
    out = tmp_path / "o.json"
    await m.export_flows(out)
    await m.deactivate_all()
    await m.stop_local()
    names = [e[0] for e in m.events]
    assert "start_local" in names and "export_flows" in names
    assert json.loads(out.read_text(encoding="utf-8"))[0]["id"] == "1"
