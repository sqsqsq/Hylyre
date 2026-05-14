"""Page snapshot store CRUD and index maintenance."""

from __future__ import annotations

import json
from pathlib import Path

from hylyre.app_store.page_store import (
    INDEX_SCHEMA,
    PAGE_SCHEMA,
    delete_page_snapshot,
    extract_key_elements,
    load_index,
    load_page_snapshot,
    merge_index_for_page,
    save_page_snapshot,
    search_index,
)


def _minimal_tree_payload() -> dict:
    tree = {
        "attributes": {"type": "root"},
        "children": [
            {
                "attributes": {
                    "type": "Button",
                    "id": "btn_ok",
                    "key": "",
                    "text": "OK",
                    "bounds": "[0,0,1,1]",
                    "clickable": "true",
                    "scrollable": "false",
                },
                "children": [],
            },
            {
                "attributes": {
                    "type": "Text",
                    "id": "",
                    "key": "k1",
                    "text": "Hello",
                    "bounds": "",
                    "clickable": "false",
                    "scrollable": "false",
                },
                "children": [],
            },
        ],
    }
    return {"tree": tree, "_hylyre_hints": {"scrollable_containers": [], "scrollable_container_count": 0}}


def test_save_load_list_delete_roundtrip(tmp_path: Path) -> None:
    bundle = "com.example.app"
    payload = _minimal_tree_payload()
    path = save_page_snapshot(
        store_dir=tmp_path,
        bundle=bundle,
        page_name="home",
        tree_payload=payload,
        ability_name="MainAbility",
        app_version="1",
        auto_fingerprint=True,
    )
    assert path.is_file()
    snap = load_page_snapshot(tmp_path, bundle, "home")
    assert snap["schema_version"] == PAGE_SCHEMA
    assert snap["bundle"] == bundle
    assert snap["page_name"] == "home"
    assert snap["ability_name"] == "MainAbility"
    assert snap["fingerprint"]
    assert isinstance(snap["key_elements"], list)
    assert len(snap["key_elements"]) >= 2

    idx = load_index(tmp_path, bundle)
    assert idx["schema_version"] == INDEX_SCHEMA
    assert "btn_ok" in json.dumps(idx["elements"])

    delete_page_snapshot(tmp_path, bundle, "home")
    assert not path.is_file()
    idx2 = load_index(tmp_path, bundle)
    assert idx2["elements"] == {}


def test_merge_index_updates_pages(tmp_path: Path) -> None:
    bundle = "b"
    idx = load_index(tmp_path, bundle)
    els = extract_key_elements(_minimal_tree_payload()["tree"])  # type: ignore[index]
    merge_index_for_page(idx, bundle=bundle, page_name="p1", elements=els)
    merge_index_for_page(idx, bundle=bundle, page_name="p2", elements=els)
    sk = next(iter(idx["elements"]))
    pages = idx["elements"][sk]["pages"]
    assert "p1" in pages and "p2" in pages


def test_search_index_by_text_and_id(tmp_path: Path) -> None:
    bundle = "b"
    idx = load_index(tmp_path, bundle)
    els = extract_key_elements(_minimal_tree_payload()["tree"])  # type: ignore[index]
    merge_index_for_page(idx, bundle=bundle, page_name="home", elements=els)
    hits = search_index(idx, by_text="OK")
    assert hits and hits[0]["text"] == "OK"
    hits2 = search_index(idx, by_id_pattern=r"btn_")
    assert any("btn_ok" in str(h["selector"]) for h in hits2)


def test_diff_snapshots_detects_change(tmp_path: Path) -> None:
    from hylyre.app_store.page_store import diff_snapshots

    p1 = _minimal_tree_payload()
    save_page_snapshot(
        store_dir=tmp_path,
        bundle="x",
        page_name="home",
        tree_payload=p1,
        auto_fingerprint=True,
    )
    snap = load_page_snapshot(tmp_path, "x", "home")
    p2 = json.loads(json.dumps(p1))
    p2["tree"]["children"][0]["attributes"]["id"] = "btn_changed"
    out = diff_snapshots(snap, p2)
    assert out["fingerprint_saved"]
    assert out["fingerprint_current"]
    assert out["same_fingerprint"] is False

