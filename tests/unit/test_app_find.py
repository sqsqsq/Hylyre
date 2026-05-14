"""Cross-page index search."""

from __future__ import annotations

from pathlib import Path

from hylyre.app_store.cross_find import search_all_indexes
from hylyre.app_store.page_store import save_page_snapshot


def _tree(txt: str, nid: str) -> dict:
    tree = {
        "attributes": {"type": "Text", "id": nid, "text": txt},
        "children": [],
    }
    return {"tree": tree}


def _text_only_tree(txt: str) -> dict:
    tree = {
        "attributes": {"type": "Text", "id": "", "text": txt},
        "children": [],
    }
    return {"tree": tree}


def test_search_all_indexes_merges_dirs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    cwd_apps = tmp_path / ".hylyre" / "apps"
    cwd_apps.mkdir(parents=True)
    extra = tmp_path / "extra_store"
    extra.mkdir()
    monkeypatch.setenv("HYLYRE_APP_STORE_DIR", str(extra))
    bundle = "com.merge.test"

    save_page_snapshot(
        store_dir=cwd_apps,
        bundle=bundle,
        page_name="one",
        tree_payload=_tree("Alpha", "id_a"),
    )
    save_page_snapshot(
        store_dir=extra,
        bundle=bundle,
        page_name="two",
        tree_payload=_text_only_tree("Beta"),
    )

    hits_alpha = search_all_indexes(bundle, by_text="Alpha")
    assert any(h["text"] == "Alpha" for h in hits_alpha)

    hits_beta = search_all_indexes(bundle, by_text="Beta")
    assert any(h["text"] == "Beta" for h in hits_beta)

    # CLI store_dir prepends one root but later dirs still include cwd index
    hits_alpha_pref = search_all_indexes(bundle, by_text="Alpha", store_dir=str(extra))
    assert any(h["text"] == "Alpha" for h in hits_alpha_pref)
