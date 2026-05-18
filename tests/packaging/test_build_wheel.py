"""Tests for scripts/build_wheel.py (framework vendor wheel)."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "build_wheel.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_hylyre_build_wheel", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bw = _load_module()


def test_compute_sha256_known_empty(tmp_path: Path) -> None:
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    assert bw.compute_sha256(f) == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_compute_sha256_small_file(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_bytes(b"hello")
    assert (
        bw.compute_sha256(f)
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_read_version_from_pyproject_matches_pyproject_toml() -> None:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m
    expected = m.group(1)
    assert bw.read_version_from_pyproject(REPO_ROOT) == expected


def test_format_cp_hints_contains_paths_and_verify(tmp_path: Path) -> None:
    w = tmp_path / "hylyre-0.1.0-py3-none-any.whl"
    w.write_bytes(b"x")
    m = tmp_path / "release.manifest.json"
    m.write_text("{}", encoding="utf-8")
    s = bw.format_cp_hints(w, m)
    assert str(w.resolve()) in s
    assert str(m.resolve()) in s
    assert "Copy-Item" in s
    assert "--verify" in s
    assert "framework-vendor-bundle.md" in s


def test_build_manifest_fields(tmp_path: Path) -> None:
    w = tmp_path / "hylyre-9.9.9-py3-none-any.whl"
    w.write_bytes(b"abc")
    d = bw.build_manifest(w, "9.9.9", "3.12.0", "pip 24", "test-platform")
    assert d["schema"] == 1
    assert d["hylyre_version"] == "9.9.9"
    assert d["wheel"]["filename"] == w.name
    assert len(d["wheel"]["sha256"]) == 64
    assert d["wheel"]["size_bytes"] == 3


def test_cmd_verify_missing_manifest(tmp_path: Path) -> None:
    assert bw.cmd_verify(tmp_path) == 3


def test_cmd_verify_corrupt_sha256(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    w = tmp_path / "hylyre-0.0.0-py3-none-any.whl"
    w.write_bytes(b"x")
    mf = {
        "schema": 1,
        "hylyre_version": "0.0.0",
        "wheel": {"filename": w.name, "sha256": "0" * 64, "size_bytes": 1},
    }
    (tmp_path / "release.manifest.json").write_text(
        json.dumps(mf), encoding="utf-8"
    )
    assert bw.cmd_verify(tmp_path) == 2


@pytest.mark.slow
def test_build_wheel_integration(tmp_path: Path) -> None:
    out = tmp_path / "release"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-dir", str(out), "--clean"],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    head = r.stdout.strip().splitlines()
    assert len(head) >= 3
    assert Path(head[0]).is_file()
    assert Path(head[1]).name == "release.manifest.json"
    assert "---" in r.stdout
    assert "Copy-Item" in r.stdout
    wheels = list(out.glob("hylyre-*-py3-none-any.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as zf:
        names = set(zf.namelist())
    assert "hylyre/contracts/output-schema.json" in names
    assert "hylyre/contracts/report-sections.yaml" in names
    mf_path = out / "release.manifest.json"
    assert mf_path.is_file()
    data = json.loads(mf_path.read_text(encoding="utf-8"))
    assert data.get("schema") == 1
    wname = data["wheel"]["filename"]
    digest = data["wheel"]["sha256"]
    assert digest == bw.compute_sha256(out / wname)
    v = subprocess.run(
        [sys.executable, str(SCRIPT), "--verify", str(out)],
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert v.returncode == 0

    # corruption → verify fails
    bad = out / wname
    bad.write_bytes(bad.read_bytes() + b"!")
    v2 = subprocess.run(
        [sys.executable, str(SCRIPT), "--verify", str(out)],
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert v2.returncode == 2
