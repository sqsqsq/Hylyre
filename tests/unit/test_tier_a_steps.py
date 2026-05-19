"""Unit tests for Tier A planned JSON steps."""

from __future__ import annotations

import pytest

from hylyre.api.agent import HylyreAgent
from hylyre.api.step_dispatch import dispatch_planned_step

from tests.contract.fakes.fake_ui_driver import FakeUiDriver


@pytest.mark.asyncio
async def test_dispatch_back_default() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(agent, {"back": {}})
    assert ui.events[-1][0] == "press_back"
    assert ui.events[-1][1]["times"] == 1


@pytest.mark.asyncio
async def test_dispatch_back_times_and_mode() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(
        agent,
        {"back": {"times": 2, "mode": "swipe", "side": "LEFT"}},
    )
    assert ui.events[-1][1]["times"] == 2
    assert ui.events[-1][1]["mode"] == "swipe"


@pytest.mark.asyncio
async def test_dispatch_wait_for_requires_selector() -> None:
    agent = HylyreAgent(ui=FakeUiDriver(), vlm=None)
    with pytest.raises(ValueError, match="wait_for"):
        await dispatch_planned_step(agent, {"wait_for": {"timeout": 5}})


@pytest.mark.asyncio
async def test_dispatch_stop_app() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(
        agent, {"stop_app": {"bundle": "com.example.app"}}
    )
    assert ui.events[-1] == (
        "stop_app",
        {"bundle": "com.example.app", "wait_time": 0.5},
    )


@pytest.mark.asyncio
async def test_dispatch_assert_toast() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(
        agent, {"assert_toast": {"text": "ok", "timeout": 2}}
    )
    assert ui.events[-1][0] == "assert_toast"


@pytest.mark.asyncio
async def test_dispatch_start_app_in_plan() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(
        agent,
        {"start_app": {"bundle": "com.example.app", "page_name": "EntryAbility"}},
    )
    assert ui.events[-1][0] == "start_app"


@pytest.mark.asyncio
async def test_dispatch_rejects_multiple_roots() -> None:
    agent = HylyreAgent(ui=FakeUiDriver(), vlm=None)
    with pytest.raises(ValueError, match="multiple root"):
        await dispatch_planned_step(agent, {"back": {}, "home": {}})


@pytest.mark.asyncio
async def test_action_type_back() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(agent, {"action": {"type": "back", "times": 1}})
    assert ui.events[-1][0] == "press_back"


@pytest.mark.asyncio
async def test_dispatch_home() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(agent, {"home": {}})
    assert ui.events[-1][0] == "press_home"


@pytest.mark.asyncio
async def test_dispatch_clear_app() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(
        agent, {"clear_app": {"bundle": "com.example.app"}}
    )
    assert ui.events[-1] == ("clear_app_data", {"bundle": "com.example.app"})


@pytest.mark.asyncio
async def test_dispatch_wait_seconds() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(agent, {"wait": {"seconds": 2.5}})
    assert ui.events[-1] == ("wait_seconds", {"seconds": 2.5})


@pytest.mark.asyncio
async def test_dispatch_wait_gone() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(
        agent,
        {"wait_gone": {"by_id": "loading", "timeout": 8}},
    )
    assert ui.events[-1][0] == "wait_for_selector_gone"
    assert ui.events[-1][1]["by_id"] == "loading"


@pytest.mark.asyncio
async def test_dispatch_wait_idle() -> None:
    ui = FakeUiDriver()
    agent = HylyreAgent(ui=ui, vlm=None)
    await dispatch_planned_step(agent, {"wait_idle": {"timeout": 15}})
    assert ui.events[-1] == (
        "wait_for_idle",
        {"idle_time": 0.7, "timeout": 15.0},
    )
