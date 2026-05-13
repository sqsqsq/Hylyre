"""CLI merge helpers for swipe.area / scroll.at overrides."""

from __future__ import annotations

import pytest

from hylyre.cli.commands.loop_cmd import (
    apply_cli_scroll_at_overrides,
    apply_cli_swipe_area_overrides,
)


def test_apply_swipe_area_by_type() -> None:
    payload = {"swipe": {"direction": "DOWN", "distance": 40}}
    out = apply_cli_swipe_area_overrides(payload, area_by_type="Scroll")
    assert out["swipe"]["direction"] == "DOWN"
    assert out["swipe"]["area"] == {"by_type": "Scroll"}
    assert "area" not in payload["swipe"]


def test_apply_swipe_area_cli_overwrites_json() -> None:
    payload = {"swipe": {"direction": "DOWN", "area": {"by_text": "old"}}}
    out = apply_cli_swipe_area_overrides(payload, area_by_type="Scroll")
    assert out["swipe"]["area"] == {"by_type": "Scroll"}


def test_apply_swipe_area_exclusive() -> None:
    with pytest.raises(ValueError, match="at most one"):
        apply_cli_swipe_area_overrides(
            {"swipe": {}},
            area_by_type="Scroll",
            area_by_text="x",
        )


def test_apply_scroll_at_by_type() -> None:
    payload = {"scroll": {"direction": "down", "steps": 3}}
    out = apply_cli_scroll_at_overrides(payload, at_by_type="Scroll")
    assert out["scroll"]["at"] == {"by_type": "Scroll"}
