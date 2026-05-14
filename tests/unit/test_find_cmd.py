"""Flat finder over dump payloads."""

from __future__ import annotations

from hylyre.cli.commands.find_cmd import find_in_payload


def test_find_in_payload_by_substrings() -> None:
    payload = {
        "tree": {
            "attributes": {"type": "root"},
            "children": [
                {
                    "attributes": {
                        "type": "Button",
                        "id": "AddCardBtn",
                        "key": "",
                        "text": "添加卡片",
                        "bounds": "",
                        "clickable": "true",
                        "scrollable": "false",
                    },
                    "children": [],
                },
            ],
        },
    }
    out = find_in_payload(payload, by_text="卡片", limit=10)
    assert out["hits"][0]["id"] == "AddCardBtn"
    assert out["_hylyre_hints"] == {}
    assert out["truncated"] is False
    assert out["limit"] == 10


def test_find_in_payload_passes_hylyre_hints() -> None:
    hints = {
        "scrollable_containers": [
            {"control_type": "Scroll", "id": "s1", "likely_more_content_below": True}
        ],
        "scrollable_container_count": 1,
    }
    payload = {
        "_hylyre_hints": hints,
        "tree": {
            "attributes": {"type": "root"},
            "children": [
                {
                    "attributes": {
                        "type": "Text",
                        "id": "t1",
                        "key": "",
                        "text": "visible",
                        "bounds": "",
                        "clickable": "false",
                        "scrollable": "false",
                    },
                    "children": [],
                },
            ],
        },
    }
    out = find_in_payload(payload, by_text="visible", limit=5)
    assert out["_hylyre_hints"]["scrollable_container_count"] == 1
    assert out["_hylyre_hints"]["scrollable_containers"][0]["id"] == "s1"
    assert len(out["hits"]) == 1
