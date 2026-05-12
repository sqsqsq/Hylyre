"""L1: compat-framework drift append dedupe."""

from __future__ import annotations

from pathlib import Path

from hylyre.progress import store


def test_append_compat_drift_writes_and_dedupes(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "hylyre"\n', encoding="utf-8"
    )
    (tmp_path / "docs").mkdir()
    p = tmp_path / "docs" / "progress.md"
    p.write_text("# base\n", encoding="utf-8")
    assert store.append_compat_framework_drift_note(["phase"], path=p, start=tmp_path)
    t1 = p.read_text(encoding="utf-8")
    assert "phase" in t1
    assert "compat-framework 自动" in t1
    assert not store.append_compat_framework_drift_note(["phase"], path=p, start=tmp_path)
    t2 = p.read_text(encoding="utf-8")
    assert t2.count("compat-framework 自动") == 1
