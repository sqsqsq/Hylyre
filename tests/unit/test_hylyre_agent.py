"""L1/L2: HylyreAgent with fakes (no device, no HTTP)."""

from __future__ import annotations

import pytest

from hylyre.api.agent import HylyreAgent
from tests.contract.fakes.fake_ui_driver import FakeUiDriver
from tests.contract.fakes.fake_vlm_client import FakeVlmClient


@pytest.mark.asyncio
async def test_ai_tap_structured() -> None:
    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui)
    try:
        await ag.ai_tap(by_text="OK")
    finally:
        await ag.aclose()
    assert ui.events[-2][0] == "touch"
    assert ui.events[-2][1]["by_text"] == "OK"


@pytest.mark.asyncio
async def test_ai_tap_instruction_uses_vlm() -> None:
    ui = FakeUiDriver()
    vlm = FakeVlmClient(
        responses=[{"touch": {"x": 10, "y": 20}}],
    )
    ag = HylyreAgent(ui=ui, vlm=vlm)
    try:
        await ag.ai_tap(instruction='tap the "go" control')
    finally:
        await ag.aclose()
    assert any(e[0] == "touch" and e[1].get("x") == 10 for e in ui.events)


@pytest.mark.asyncio
async def test_ai_action_touch() -> None:
    ui = FakeUiDriver()
    vlm = FakeVlmClient(
        responses=[
            {"action": {"type": "touch", "by_id": "btn_login"}},
        ],
    )
    ag = HylyreAgent(ui=ui, vlm=vlm)
    try:
        await ag.ai_action("log in")
    finally:
        await ag.aclose()
    touches = [e for e in ui.events if e[0] == "touch"]
    assert touches[-1][1]["by_id"] == "btn_login"


@pytest.mark.asyncio
async def test_ai_input_instruction() -> None:
    ui = FakeUiDriver()
    vlm = FakeVlmClient(responses=[{"input": {"text": "hi", "by_id": "f", "by_text": None}}])
    ag = HylyreAgent(ui=ui, vlm=vlm)
    try:
        await ag.ai_input(instruction="fill field")
    finally:
        await ag.aclose()
    ins = [e for e in ui.events if e[0] == "input_text"]
    assert ins[-1][1]["text"] == "hi"
    assert ins[-1][1]["by_id"] == "f"


@pytest.mark.asyncio
async def test_ai_action_input_type() -> None:
    ui = FakeUiDriver()
    vlm = FakeVlmClient(
        responses=[{"action": {"type": "input", "text": "pwd", "by_id": "p"}}],
    )
    ag = HylyreAgent(ui=ui, vlm=vlm)
    try:
        await ag.ai_action("enter password")
    finally:
        await ag.aclose()
    ins = [e for e in ui.events if e[0] == "input_text"]
    assert ins[-1][1]["text"] == "pwd"


@pytest.mark.asyncio
async def test_mock_activate_requires_controller() -> None:
    ag = HylyreAgent(ui=FakeUiDriver(), mock=None)
    with pytest.raises(ValueError, match="mock"):
        await ag.mock_activate_group("g")


@pytest.mark.asyncio
async def test_mock_activate_delegates() -> None:
    from tests.contract.fakes.fake_mock_controller import FakeMockController

    m = FakeMockController()
    ag = HylyreAgent(ui=FakeUiDriver(), mock=m)
    await ag.mock_activate_group("uuid-1")
    assert any(ev[0] == "activate_group" for ev in m.events)


@pytest.mark.asyncio
async def test_ai_input_structured() -> None:
    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui)
    try:
        await ag.ai_input("hello", by_id="field")
    finally:
        await ag.aclose()
    assert ("input_text", {"text": "hello", "by_text": None, "by_id": "field", "mode": None}) in ui.events


@pytest.mark.asyncio
async def test_ai_query_coerce() -> None:
    ui = FakeUiDriver()
    vlm = FakeVlmClient(responses=[{"answer": "3.14", "dtype": "number"}])
    ag = HylyreAgent(ui=ui, vlm=vlm)
    try:
        v = await ag.ai_query("balance?", schema=float)
    finally:
        await ag.aclose()
    assert v == 3.14


@pytest.mark.asyncio
async def test_ai_assert_ok() -> None:
    ui = FakeUiDriver()
    vlm = FakeVlmClient(responses=[{"ok": True, "reason": ""}])
    ag = HylyreAgent(ui=ui, vlm=vlm)
    try:
        await ag.ai_assert("see home")
    finally:
        await ag.aclose()


@pytest.mark.asyncio
async def test_ai_assert_fails() -> None:
    ui = FakeUiDriver()
    vlm = FakeVlmClient(responses=[{"ok": False, "reason": "missing"}])
    ag = HylyreAgent(ui=ui, vlm=vlm)
    with pytest.raises(AssertionError, match="missing"):
        try:
            await ag.ai_assert("see home")
        finally:
            await ag.aclose()


@pytest.mark.asyncio
async def test_ai_wait_for_succeeds() -> None:
    ui = FakeUiDriver()
    vlm = FakeVlmClient(
        responses=[
            {"ok": False, "reason": "no"},
            {"ok": True, "reason": ""},
        ],
    )
    ag = HylyreAgent(ui=ui, vlm=vlm)
    try:
        await ag.ai_wait_for("ready", timeout=2.0, interval=0.01)
    finally:
        await ag.aclose()


@pytest.mark.asyncio
async def test_ai_locate() -> None:
    ui = FakeUiDriver()
    loc = {
        "region": {"x": 0, "y": 0, "width": 10, "height": 10},
        "center": {"x": 5, "y": 5},
    }
    vlm = FakeVlmClient(responses=[loc])
    ag = HylyreAgent(ui=ui, vlm=vlm)
    try:
        out = await ag.ai_locate("login button")
    finally:
        await ag.aclose()
    assert out == loc


@pytest.mark.asyncio
async def test_natural_language_requires_vlm() -> None:
    ui = FakeUiDriver()
    ag = HylyreAgent(ui=ui, vlm=None)
    with pytest.raises(ValueError, match="VLM"):
        try:
            await ag.ai_tap(instruction="tap x")
        finally:
            await ag.aclose()


@pytest.mark.asyncio
async def test_import_hylyre_package_exports_agent() -> None:
    import hylyre

    assert hylyre.HylyreAgent is HylyreAgent
