"""Unit tests for hylyre.api.selector_resolve (no device)."""

from __future__ import annotations

import pytest

from hylyre.api.exceptions import SelectorResolutionError
from hylyre.api.selector_resolve import (
    finalize_tap_hit,
    pick_best_tap_hit,
    resolve_first_hit_match_center_in_container,
    resolve_one,
    resolve_targets,
)


def _attrs(**kw: str) -> dict:
    return {"attributes": kw, "children": []}


def _node(attrs: dict, *children: dict) -> dict:
    return {"attributes": attrs, "children": list(children)}


def test_overlay_same_text_prefers_top_sheet() -> None:
    page_btn = _node(
        {
            "type": "Button",
            "text": "下一步",
            "bounds": "[0,800][200,900]",
            "clickable": "true",
        },
        _node({"type": "Text", "text": "下一步", "bounds": "[0,800][200,900]"}),
    )
    sheet = _node(
        {
            "type": "Sheet",
            "text": "",
            "bounds": "[0,400][1080,1200]",
        },
        _node(
            {
                "type": "Button",
                "text": "下一步",
                "bounds": "[0,1000][200,1100]",
                "clickable": "true",
            },
            _node({"type": "Text", "text": "下一步", "bounds": "[0,1000][200,1100]"}),
        ),
    )
    tree = _node({"type": "Root", "bounds": "[0,0][1080,2400]"}, page_btn, sheet)
    hits = resolve_targets(tree, {"by_text": "下一步"})
    assert len(hits) == 2
    hit = hits[0]
    assert hit.center == (100, 1050)
    assert hit.overlay_rank >= 1


def test_all_lifts_text_to_button_parent() -> None:
    tree = _node(
        {"type": "Root", "bounds": "[0,0][500,500]"},
        _node(
            {
                "type": "Button",
                "text": "",
                "bounds": "[10,10][110,60]",
                "clickable": "true",
            },
            _node({"type": "Text", "text": "下一步", "bounds": "[20,20][100,50]"}),
        ),
    )
    hit = resolve_one(
        tree,
        {"all": [{"by_text": "下一步"}, {"by_type": "Button"}]},
    )
    assert hit.type == "Button"
    assert hit.center == (60, 35)


def test_index_selects_second_match() -> None:
    tree = _node(
        {"type": "Root", "bounds": "[0,0][500,500]"},
        _node(
            {
                "type": "Button",
                "text": "下一步",
                "bounds": "[0,0][100,50]",
                "clickable": "true",
            }
        ),
        _node(
            {
                "type": "Button",
                "text": "下一步",
                "bounds": "[0,100][100,150]",
                "clickable": "true",
            }
        ),
    )
    hits = resolve_targets(tree, {"by_text": "下一步", "index": 1})
    assert len(hits) == 1
    assert hits[0].center == (50, 125)


def test_zero_match_raises() -> None:
    tree = _node({"type": "Root", "bounds": "[0,0][100,100]"})
    with pytest.raises(SelectorResolutionError):
        resolve_one(tree, {"by_text": "不存在"})


def test_scope_top_overlay() -> None:
    page_btn = _node(
        {"type": "Button", "text": "下一步", "bounds": "[0,0][100,50]", "clickable": "true"}
    )
    sheet = _node(
        {"type": "Sheet", "bounds": "[0,200][500,500]"},
        _node(
            {
                "type": "Button",
                "text": "下一步",
                "bounds": "[0,300][100,350]",
                "clickable": "true",
            }
        ),
    )
    tree = _node({"type": "Root", "bounds": "[0,0][500,600]"}, page_btn, sheet)
    hit = resolve_one(tree, {"by_text": "下一步", "scope": "top_overlay"})
    assert hit.center == (50, 325)


def test_below_uses_y_not_tree_order() -> None:
    btn = _node(
        {
            "type": "Button",
            "text": "提交",
            "bounds": "[0,100][200,160]",
            "clickable": "true",
        }
    )
    title = _node({"type": "Text", "text": "标题", "bounds": "[0,0][200,40]"})
    tree = _node({"type": "Root", "bounds": "[0,0][500,500]"}, btn, title)
    hit = resolve_one(tree, {"by_text": "提交", "below": {"by_text": "标题"}})
    assert hit.center == (100, 130)


def test_after_still_uses_tree_order() -> None:
    btn = _node(
        {
            "type": "Button",
            "text": "提交",
            "bounds": "[0,100][200,160]",
            "clickable": "true",
        }
    )
    title = _node({"type": "Text", "text": "标题", "bounds": "[0,0][200,40]"})
    tree = _node({"type": "Root", "bounds": "[0,0][500,500]"}, btn, title)
    assert resolve_targets(tree, {"by_text": "提交", "after": {"by_text": "标题"}}) == []


def test_finalize_tap_hit_remediates_zero_area_clickable() -> None:
    row = _node(
        {
            "type": "Row",
            "clickable": "true",
            "enabled": "true",
            "bounds": "[0,0][0,0]",
        },
        _node({"type": "Text", "text": "目标", "bounds": "[50,50][150,80]"}),
    )
    tree = _node({"type": "Root", "bounds": "[0,0][500,800]"}, row)
    raw = resolve_one(tree, {"by_text": "目标"})
    assert raw.center == (0, 0)
    safe = finalize_tap_hit(tree, {"by_text": "目标"}, raw)
    assert safe.center == (100, 65)


def test_pick_best_tap_hit_skips_degenerate() -> None:
    bad = resolve_one(
        _node(
            {"type": "Root", "bounds": "[0,0][500,800]"},
            _node(
                {
                    "type": "Row",
                    "clickable": "true",
                    "enabled": "true",
                    "bounds": "[0,0][0,0]",
                },
                _node({"type": "Text", "text": "x", "bounds": "[10,10][30,30]"}),
            ),
        ),
        {"by_text": "x"},
    )
    good = resolve_one(
        _node(
            {"type": "Root", "bounds": "[0,0][500,800]"},
            _node({"type": "Text", "text": "y", "bounds": "[100,100][200,140]"}),
        ),
        {"by_text": "y"},
    )
    assert pick_best_tap_hit([bad, good]) is good


def test_pre_lift_in_container_sorts_clickable() -> None:
    scroll = _node(
        {"type": "Scroll", "scrollable": "false", "bounds": "[0,100][500,600]"}
    )
    plain = _node({"type": "Text", "text": "项", "bounds": "[50,150][80,180]"})
    clickable = _node(
        {
            "type": "Row",
            "clickable": "true",
            "enabled": "true",
            "bounds": "[50,300][200,340]",
        },
        _node({"type": "Text", "text": "项", "bounds": "[60,310][90,330]"}),
    )
    tree = _node({"type": "Root", "bounds": "[0,0][500,800]"}, scroll, plain, clickable)
    with pytest.raises(SelectorResolutionError, match="ambiguous"):
        resolve_first_hit_match_center_in_container(
            tree, {"by_text": "项"}, "[0,100][500,600]"
        )
