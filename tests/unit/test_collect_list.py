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
async def test_collect_list_default_stable_exits_with_expected_iterations() -> None:
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
        *,
        scroll_area: dict[str, str],
        direction: str,
        swipe_distance: int,
        stable_need: int,
        max_swipes: int,
        pattern_re: Any,
    ) -> int:
        assert direction == "DOWN"
        return 2

    async def fake_merge(
        agent: Any,
        *,
        scroll_area: dict[str, str],
        pattern_re: Any,
        direction: str,
        swipe_distance: int,
        stable_need: int,
        max_scrolls: int,
        items: list,
        seen: set,
    ) -> int:
        assert direction == "UP"
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
