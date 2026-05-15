"""Unit tests for collect-list scroll-merge helper."""

from __future__ import annotations

from typing import Any

import pytest

from hylyre.cli.commands import collect_cmd


def _scroll_tree(text: str, nid: str) -> dict[str, Any]:
    return {
        "attributes": {"type": "Scroll", "scrollable": "true", "id": "sc1"},
        "children": [
            {
                "attributes": {
                    "type": "Text",
                    "id": nid,
                    "key": "",
                    "text": text,
                    "bounds": "",
                },
                "children": [],
            }
        ],
    }


class _FakeAgent:
    """Minimal async agent stub for collect_list_on_agent."""

    def __init__(self, tree: dict[str, Any]) -> None:
        self._tree = tree
        self.swipe_directions: list[str] = []

    async def dump_ui(self) -> dict[str, Any]:
        return {"tree": self._tree}

    async def run_planned_swipe(self, payload: dict[str, Any]) -> None:
        self.swipe_directions.append(str(payload["swipe"]["direction"]))


@pytest.mark.asyncio
async def test_collect_list_default_early_bounce_exits_fast() -> None:
    """Static tree: after first UP swipe the next dump matches checkpoint → stop."""
    agent = _FakeAgent(_scroll_tree("only", "r1"))
    result = await collect_cmd.collect_list_on_agent(
        agent,
        {
            "scroll_area": {"by_type": "Scroll"},
            "max_scrolls": 10,
            "swipe_distance": 60,
            "max_stable_rounds": 2,
            "reset_to_top": False,
            "bidirectional": False,
            "early_bounce_break": True,
        },
    )
    assert result["iterations_reset"] == 0
    assert result["iterations_up"] == 2
    assert result["iterations_down"] == 0
    assert result["iterations"] == 2
    assert result["unique_count"] == 1
    assert len(agent.swipe_directions) == 1
    assert all(d == "UP" for d in agent.swipe_directions)
    assert result["early_bounce_break"] is True


@pytest.mark.asyncio
async def test_collect_list_stable_without_early_bounce_legacy_iterations() -> None:
    """Disable early bounce → require two stable rounds (legacy behavior)."""
    agent = _FakeAgent(_scroll_tree("only", "r1"))
    result = await collect_cmd.collect_list_on_agent(
        agent,
        {
            "scroll_area": {"by_type": "Scroll"},
            "max_scrolls": 10,
            "swipe_distance": 60,
            "max_stable_rounds": 2,
            "reset_to_top": False,
            "bidirectional": False,
            "early_bounce_break": False,
        },
    )
    assert result["iterations_reset"] == 0
    assert result["iterations_up"] == 3
    assert result["iterations_down"] == 0
    assert result["iterations"] == 3
    assert result["unique_count"] == 1
    assert len(agent.swipe_directions) == 2
    assert all(d == "UP" for d in agent.swipe_directions)


@pytest.mark.asyncio
async def test_reset_to_top_swipes_down_first(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_reset(
        agent: Any,
        **kwargs: Any,
    ) -> int:
        assert kwargs["direction"] == "DOWN"
        return 2

    async def fake_merge(
        agent: Any,
        **kwargs: Any,
    ) -> int:
        assert kwargs["direction"] == "UP"
        return 1

    monkeypatch.setattr(collect_cmd, "_swipe_until_viewport_stable", fake_reset)
    monkeypatch.setattr(collect_cmd, "_collect_merge_direction", fake_merge)

    class _Dummy:
        pass

    result = await collect_cmd.collect_list_on_agent(
        _Dummy(),
        {
            "scroll_area": {"by_type": "Scroll"},
            "max_scrolls": 5,
            "swipe_distance": 60,
            "max_stable_rounds": 2,
            "reset_to_top": True,
            "bidirectional": False,
        },
    )
    assert result["iterations_reset"] == 2
    assert result["iterations_up"] == 1
    assert result["iterations_down"] == 0
    assert result["reset_to_top"] is True
    assert result["bidirectional"] is False


def test_build_swipe_payload_adds_scrollable_when_root_found() -> None:
    root = {"attributes": {"bounds": "[0,333][1320,1688]", "scrollable": "true", "type": "Scroll"}}
    payload = collect_cmd._build_swipe_payload("UP", 60, {"by_type": "Scroll"}, root)
    swipe = payload["swipe"]
    assert swipe["area"] == {"by_type": "Scroll", "scrollable": True}


def test_build_swipe_payload_no_scrollable_when_no_root() -> None:
    payload = collect_cmd._build_swipe_payload("UP", 60, {"by_type": "Scroll"}, None)
    swipe = payload["swipe"]
    assert swipe["area"] == {"by_type": "Scroll"}
    assert "scrollable" not in swipe["area"]


def _nested_sheet_tree() -> dict[str, Any]:
    """Simulates wallet half-sheet: outer Scroll (non-scrollable) wrapping inner Scroll (scrollable)."""
    return {
        "attributes": {"type": "root"},
        "children": [{
            "attributes": {"type": "Scroll", "scrollable": "false", "bounds": "[0,141][1320,2120]"},
            "children": [{
                "attributes": {"type": "Scroll", "scrollable": "true", "bounds": "[0,333][1320,1688]"},
                "children": [{
                    "attributes": {"type": "Text", "text": "card1", "id": "c1", "key": "", "bounds": "[0,400][100,500]"},
                    "children": [],
                }],
            }],
        }],
    }


def test_find_scroll_root_skips_non_scrollable_outer() -> None:
    tree = _nested_sheet_tree()
    root = collect_cmd.find_scroll_root(tree, {"by_type": "Scroll"})
    assert root is not None
    assert root["attributes"]["scrollable"] == "true"
    assert root["attributes"]["bounds"] == "[0,333][1320,1688]"


@pytest.mark.asyncio
async def test_collect_swipe_adds_scrollable_to_area() -> None:
    """Verify swipe payload includes scrollable:true so Hypium finds the inner container."""
    tree = _nested_sheet_tree()
    payloads: list[dict[str, Any]] = []

    class _Agent:
        async def dump_ui(self) -> dict[str, Any]:
            return {"tree": tree}

        async def run_planned_swipe(self, payload: dict[str, Any]) -> None:
            payloads.append(payload)

    result = await collect_cmd.collect_list_on_agent(
        _Agent(),
        {
            "scroll_area": {"by_type": "Scroll"},
            "max_scrolls": 3,
            "swipe_distance": 60,
            "max_stable_rounds": 2,
            "reset_to_top": False,
            "bidirectional": False,
            "early_bounce_break": True,
        },
    )
    assert len(payloads) >= 1
    for p in payloads:
        area = p["swipe"]["area"]
        assert area.get("scrollable") is True, "swipe area must include scrollable:true"
        assert area["by_type"] == "Scroll"


@pytest.mark.asyncio
async def test_bidirectional_runs_second_down_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    directions: list[str] = []

    async def fake_reset(*args: Any, **kwargs: Any) -> int:
        return 0

    async def fake_merge(
        agent: Any,
        *,
        direction: str,
        **kwargs: Any,
    ) -> int:
        directions.append(direction)
        return 1

    monkeypatch.setattr(collect_cmd, "_swipe_until_viewport_stable", fake_reset)
    monkeypatch.setattr(collect_cmd, "_collect_merge_direction", fake_merge)

    class _Dummy:
        pass

    await collect_cmd.collect_list_on_agent(
        _Dummy(),
        {
            "scroll_area": {"by_type": "Scroll"},
            "max_scrolls": 4,
            "swipe_distance": 60,
            "max_stable_rounds": 2,
            "reset_to_top": False,
            "bidirectional": True,
        },
    )
    assert directions == ["UP", "DOWN"]
