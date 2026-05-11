"""L1: LyrebirdController HTTP behaviour (respx, no Lyrebird process)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from unittest.mock import AsyncMock, MagicMock, patch

from hylyre.drivers.lyrebird.controller import LyrebirdController
from hylyre.drivers.lyrebird.exceptions import LyrebirdApiError

BASE = "http://127.0.0.1:9090"


@pytest.mark.asyncio
@respx.mock
async def test_status() -> None:
    respx.get(f"{BASE}/api/status").mock(
        return_value=httpx.Response(200, json={"code": 1000, "version": "x"})
    )
    c = LyrebirdController(BASE)
    try:
        st = await c.status()
        assert st["code"] == 1000
    finally:
        await c.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_activate_group_success() -> None:
    gid = "5a73de9c-cfae-4535-abfd-bb220d2239c4"
    respx.put(f"{BASE}/api/mock/{gid}/activate").mock(
        return_value=httpx.Response(200, json={"code": 1000, "message": "success"})
    )
    c = LyrebirdController(BASE)
    try:
        await c.activate_group(gid)
    finally:
        await c.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_activate_group_api_code_failure() -> None:
    gid = "g1"
    respx.put(f"{BASE}/api/mock/{gid}/activate").mock(
        return_value=httpx.Response(200, json={"code": 1001, "message": "nope"})
    )
    c = LyrebirdController(BASE)
    try:
        with pytest.raises(LyrebirdApiError):
            await c.activate_group(gid)
    finally:
        await c.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_list_flows_raw_array() -> None:
    respx.get(f"{BASE}/api/flow").mock(
        return_value=httpx.Response(200, json=[{"id": "a", "size": 1}])
    )
    c = LyrebirdController(BASE)
    try:
        flows = await c.list_flows()
        assert len(flows) == 1 and flows[0]["id"] == "a"
    finally:
        await c.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_export_flows_summary(tmp_path: Path) -> None:
    respx.get(f"{BASE}/api/flow").mock(
        return_value=httpx.Response(200, json=[{"id": "f1", "n": 1}])
    )
    out = tmp_path / "flows.json"
    c = LyrebirdController(BASE)
    try:
        await c.export_flows(out, full_detail=False)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data[0]["id"] == "f1"
    finally:
        await c.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_export_flows_full_detail(tmp_path: Path) -> None:
    respx.get(f"{BASE}/api/flow").mock(
        return_value=httpx.Response(200, json=[{"id": "f1"}])
    )
    respx.get(f"{BASE}/api/flow/f1").mock(
        return_value=httpx.Response(
            200, json={"code": 1000, "data": {"id": "f1", "request": {}}}
        )
    )
    out = tmp_path / "full.json"
    c = LyrebirdController(BASE)
    try:
        await c.export_flows(out, full_detail=True)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["id"] == "f1"
    finally:
        await c.aclose()


@pytest.mark.asyncio
@patch("hylyre.drivers.lyrebird.controller.require_lyrebird_distribution")
async def test_start_local_requires_own_client(_req: MagicMock) -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    client = httpx.AsyncClient(base_url=BASE, transport=transport)
    c = LyrebirdController(BASE, client=client)
    try:
        with pytest.raises(LyrebirdApiError, match="owns"):
            await c.start_local(mock_port=9090)
    finally:
        await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_deactivate_all() -> None:
    respx.put(f"{BASE}/api/mock/group/deactivate").mock(
        return_value=httpx.Response(200, json={"code": 1000, "message": "ok"})
    )
    c = LyrebirdController(BASE)
    try:
        await c.deactivate_all()
    finally:
        await c.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_list_activated_groups() -> None:
    respx.get(f"{BASE}/api/mock/activated").mock(
        return_value=httpx.Response(
            200, json={"code": 1000, "data": {"grp": {"id": "grp"}}}
        )
    )
    c = LyrebirdController(BASE)
    try:
        d = await c.list_activated_groups()
        assert "grp" in d
    finally:
        await c.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_activate_http_status_error() -> None:
    respx.put(f"{BASE}/api/mock/bad/activate").mock(
        return_value=httpx.Response(502, json={})
    )
    c = LyrebirdController(BASE)
    try:
        with pytest.raises(LyrebirdApiError):
            await c.activate_group("bad")
    finally:
        await c.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_list_flows_wrapped_payload() -> None:
    respx.get(f"{BASE}/api/flow").mock(
        return_value=httpx.Response(
            200, json={"code": 1000, "data": [{"id": "z"}]}
        )
    )
    c = LyrebirdController(BASE)
    try:
        flows = await c.list_flows()
        assert flows and flows[0]["id"] == "z"
    finally:
        await c.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_list_activated_groups_code_failure() -> None:
    respx.get(f"{BASE}/api/mock/activated").mock(
        return_value=httpx.Response(200, json={"code": 1002, "message": "x"})
    )
    c = LyrebirdController(BASE)
    try:
        with pytest.raises(LyrebirdApiError):
            await c.list_activated_groups()
    finally:
        await c.aclose()


@pytest.mark.asyncio
@patch("hylyre.drivers.lyrebird.controller.subprocess.Popen")
@patch("hylyre.drivers.lyrebird.controller.require_lyrebird_distribution")
async def test_start_stop_local_subprocess(
    _req: MagicMock, mock_popen: MagicMock
) -> None:
    proc = MagicMock()
    proc.poll.return_value = None
    proc.pid = 7
    proc.terminate = MagicMock()
    proc.wait = MagicMock(return_value=0)
    mock_popen.return_value = proc
    c = LyrebirdController()
    try:
        with patch.object(LyrebirdController, "_wait_until_ready", new_callable=AsyncMock):
            await c.start_local(mock_port=8881)
        assert c.subprocess_pid == 7
        await c.stop_local()
    finally:
        await c.aclose()
    proc.terminate.assert_called_once()


@pytest.mark.asyncio
@patch("hylyre.drivers.lyrebird.controller.require_lyrebird_distribution")
async def test_start_local_requires_own_client(_req: MagicMock) -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    client = httpx.AsyncClient(base_url=BASE, transport=transport)
    c = LyrebirdController(BASE, client=client)
    try:
        with pytest.raises(LyrebirdApiError, match="owns"):
            await c.start_local(mock_port=9090)
    finally:
        await client.aclose()
