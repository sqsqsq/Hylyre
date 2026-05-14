"""Structural fingerprint stability."""

from __future__ import annotations

from hylyre.app_store.fingerprint import compute_ui_fingerprint


def _tree() -> dict:
    return {
        "attributes": {"type": "Column"},
        "children": [
            {
                "attributes": {
                    "type": "Button",
                    "id": "b1",
                    "key": "k1",
                    "text": "Ignore me",
                },
                "children": [],
            },
            {
                "attributes": {
                    "type": "Text",
                    "id": "",
                    "key": "k2",
                    "text": "Also ignored for fp",
                },
                "children": [],
            },
        ],
    }


def test_fingerprint_stable_across_text_change() -> None:
    t1 = _tree()
    fp1, lines1 = compute_ui_fingerprint(t1)
    t2 = _tree()
    t2["children"][0]["attributes"]["text"] = "different label"
    fp2, _lines2 = compute_ui_fingerprint(t2)
    assert fp1 == fp2
    assert lines1


def test_fingerprint_changes_when_id_changes() -> None:
    t1 = _tree()
    fp1, _ = compute_ui_fingerprint(t1)
    t2 = _tree()
    t2["children"][0]["attributes"]["id"] = "b2"
    fp2, _ = compute_ui_fingerprint(t2)
    assert fp1 != fp2
