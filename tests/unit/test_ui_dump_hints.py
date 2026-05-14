"""Pure helpers for UI dump hints."""

from __future__ import annotations

from hylyre.ui_dump_hints import augment_ui_dump_payload, parse_bounds_rect


def test_parse_bounds_rect() -> None:
    assert parse_bounds_rect("[0,100][200,300]") == (0, 100, 200, 300)
    assert parse_bounds_rect(None) is None
    assert parse_bounds_rect("bad") is None


def test_augment_ui_dump_hints_scrollable() -> None:
    payload = {
        "tree": {
            "attributes": {"type": "Column"},
            "children": [
                {
                    "attributes": {
                        "type": "Scroll",
                        "scrollable": "true",
                        "bounds": "[0,100][400,800]",
                        "origBounds": "[0,100][400,1200]",
                        "id": "s1",
                    },
                    "children": [],
                }
            ],
        }
    }
    out = augment_ui_dump_payload(payload)
    hints = out.get("_hylyre_hints") or {}
    assert hints.get("scrollable_container_count") == 1
    rows = hints.get("scrollable_containers") or []
    assert rows[0].get("likely_more_content_below") is True
