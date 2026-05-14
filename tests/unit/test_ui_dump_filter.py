"""Unit tests for ``hylyre.ui_dump_filter``."""

from __future__ import annotations

from hylyre.ui_dump_filter import DumpFilterSpec, apply_ui_dump_filter, default_dump_postprocess


def _sample_tree() -> dict:
    return {
        "schema_version": "x",
        "tree": {
            "attributes": {
                "type": "Column",
                "text": "",
                "id": "root",
                "bounds": "[0,0][100,200]",
            },
            "children": [
                {
                    "attributes": {
                        "type": "Text",
                        "text": "Alpha",
                        "id": "t1",
                        "key": "k1",
                        "bounds": "[1,1][10,10]",
                        "clickable": "false",
                        "scrollable": "false",
                        "hint": "x",
                    },
                    "children": [],
                },
                {
                    "attributes": {
                        "type": "Button",
                        "text": "登录",
                        "id": "btn",
                        "key": "",
                        "bounds": "[1,20][50,40]",
                        "clickable": "true",
                        "scrollable": "false",
                    },
                    "children": [],
                },
            ],
        },
        "_hylyre_hints": {"scrollable_containers": []},
    }


def test_default_postprocess_trims_extra_attrs() -> None:
    p = _sample_tree()
    out = default_dump_postprocess(p)
    attrs = out["tree"]["children"][0]["attributes"]
    assert "hint" not in attrs
    assert attrs["text"] == "Alpha"


def test_filter_text_keeps_ancestors() -> None:
    p = _sample_tree()
    spec = DumpFilterSpec(filter_text="登录")
    out = apply_ui_dump_filter(p, spec)

    texts = []

    def walk(n: dict) -> None:
        a = n.get("attributes") or {}
        if a.get("text"):
            texts.append(a["text"])
        for c in n.get("children") or []:
            walk(c)

    walk(out["tree"])
    assert "登录" in texts
    assert "Alpha" not in texts


def test_keep_clickable_branch() -> None:
    p = _sample_tree()
    spec = DumpFilterSpec(keep_clickable=True)
    out = apply_ui_dump_filter(p, spec)
    assert out["tree"]["attributes"]["id"] == "root"


def test_max_depth_clip_without_regex() -> None:
    deep = {
        "tree": {
            "attributes": {"type": "Root", "id": "r"},
            "children": [
                {
                    "attributes": {"type": "A", "id": "a"},
                    "children": [
                        {
                            "attributes": {"type": "B", "id": "b"},
                            "children": [],
                        }
                    ],
                }
            ],
        }
    }
    spec = DumpFilterSpec(full=False, max_depth=1)
    out = apply_ui_dump_filter(deep, spec)
    ch = out["tree"]["children"]
    assert len(ch) == 1
    assert ch[0]["children"] == []


def test_summary_replaces_tree() -> None:
    p = _sample_tree()
    spec = DumpFilterSpec(full=False, summary=True)
    out = apply_ui_dump_filter(p, spec)
    assert "tree" not in out
    assert "summary" in out
    assert any(row["text"] == "Alpha" for row in out["summary"])
