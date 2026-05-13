"""Planned swipe / scroll JSON on FakeUiDriver (no Hypium)."""

from __future__ import annotations

import pytest

from hylyre.api.agent import HylyreAgent
from tests.contract.fakes.fake_ui_driver import FakeUiDriver


@pytest.mark.asyncio
async def test_run_planned_swipe_records_event() -> None:
    d = FakeUiDriver()
    a = HylyreAgent(ui=d)
    await a.run_planned_swipe(
        {
            "swipe": {
                "direction": "DOWN",
                "distance": 40,
                "area": {"by_type": "Scroll"},
                "side": "LEFT",
                "start_point": [0.5, 0.6],
            }
        }
    )
    await a.aclose()
    kinds = [e[0] for e in d.events]
    assert kinds == ["connect", "swipe", "close"]
    _name, payload = d.events[1]
    assert payload["direction"] == "DOWN"
    assert payload["distance"] == 40
    assert payload["area_by_type"] == "Scroll"
    assert payload["side"] == "LEFT"
    assert payload["start_point"] == (0.5, 0.6)


@pytest.mark.asyncio
async def test_run_planned_scroll_default_center() -> None:
    d = FakeUiDriver()
    a = HylyreAgent(ui=d)
    await a.run_planned_scroll({"scroll": {"direction": "down", "steps": 3}})
    await a.aclose()
    _name, payload = d.events[1]
    assert payload["direction"] == "down"
    assert payload["steps"] == 3
    assert payload["x"] is None and payload["y"] is None
    assert payload["at_by_type"] is None


@pytest.mark.asyncio
async def test_run_planned_action_swipe_and_scroll() -> None:
    d = FakeUiDriver()
    a = HylyreAgent(ui=d)
    await a.run_planned_action(
        {"action": {"type": "swipe", "direction": "LEFT", "distance": 50}}
    )
    await a.run_planned_action(
        {
            "action": {
                "type": "scroll",
                "direction": "up",
                "steps": 2,
                "at": {"by_text": "List"},
            }
        }
    )
    await a.aclose()
    assert [e[0] for e in d.events] == [
        "connect",
        "swipe",
        "mouse_scroll",
        "close",
    ]


def test_swipe_area_two_selectors_errors() -> None:
    with pytest.raises(ValueError, match="at most one"):
        HylyreAgent._swipe_area_kwargs({"by_text": "a", "by_id": "b"})


def test_scroll_conflicting_coords_errors() -> None:
    with pytest.raises(ValueError, match="not both"):
        HylyreAgent._scroll_xy_or_none(
            at={"by_text": "x"}, block={"x": 1, "y": 2}
        )
