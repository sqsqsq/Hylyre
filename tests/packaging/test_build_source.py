"""Tests for scripts/build_wheel.py --source (plain-source tree release, schema 2)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "build_wheel.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_hylyre_build_source", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bw = _load_module()


def _write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _verify(directory: Path) -> int:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--verify", str(directory)],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    return r.returncode


@pytest.fixture(scope="module")
def release_src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One real --source build shared by the module; tests copy before mutating."""
    out = tmp_path_factory.mktemp("release") / "release-src"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--source", "--out-dir", str(out), "--clean"],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    return out


@pytest.fixture()
def release_copy(release_src: Path, tmp_path: Path) -> Path:
    dst = tmp_path / "release-src"
    shutil.copytree(release_src, dst)
    return dst


def test_normalize_to_lf() -> None:
    assert bw.normalize_to_lf(b"a\r\nb\r\n") == b"a\nb\n"
    assert bw.normalize_to_lf(b"a\nb") == b"a\nb"
    assert bw.normalize_to_lf(b"") == b""


def test_compute_tree_sha256_known_vector_and_order_insensitive() -> None:
    files = [
        {"path": "b.py", "sha256": "b" * 64, "size_bytes": 1},
        {"path": "a.py", "sha256": "a" * 64, "size_bytes": 1},
    ]
    joined = f"a.py\n{'a' * 64}\nb.py\n{'b' * 64}\n"
    expected = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    assert bw.compute_tree_sha256(files) == expected
    assert bw.compute_tree_sha256(list(reversed(files))) == expected


def test_source_build_layout_and_manifest(release_src: Path) -> None:
    src = release_src / "src"
    assert (src / "pyproject.toml").is_file()
    assert (src / "README.md").is_file()  # pyproject readme reference; install needs it
    assert (src / "hylyre" / "__init__.py").is_file()
    assert (src / "hylyre" / "api" / "planned_step_keys.py").is_file()  # downstream SSOT
    assert (src / "hylyre" / "contracts" / "output-schema.json").is_file()
    assert (src / "hylyre" / "contracts" / "report-sections.yaml").is_file()
    assert (src / "hylyre" / "contracts" / "README.md").is_file()
    assert (release_src / "downstream-harness-requests.md").is_file()

    on_disk = [p for p in src.rglob("*") if p.is_file()]
    assert not [p for p in on_disk if "__pycache__" in p.parts or p.suffix == ".pyc"]

    manifest = json.loads((release_src / "release.manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == 2
    assert manifest["hylyre_version"] == bw.read_version_from_pyproject(REPO_ROOT)
    assert "wheel" not in manifest
    source = manifest["source"]
    assert source["root"] == "src"
    files = source["files"]
    assert source["file_count"] == len(files) == len(on_disk)
    assert source["total_bytes"] == sum(f["size_bytes"] for f in files)
    assert source["tree_sha256"] == bw.compute_tree_sha256(files)
    paths = [f["path"] for f in files]
    assert all("\\" not in p for p in paths)
    assert paths == sorted(paths, key=lambda p: p.encode("utf-8"))
    docs = manifest["integration_docs"]
    assert docs and docs[0]["filename"] == "downstream-harness-requests.md"
    assert manifest["note"].startswith("Plain-source release.")


def test_stage_source_tree_rejects_unnormalized_crlf(tmp_path: Path) -> None:
    """A CRLF file whose suffix escapes the LF whitelist must fail the build."""
    root = tmp_path / "repo"
    (root / "hylyre").mkdir(parents=True)
    (root / "pyproject.toml").write_bytes(b'[project]\nversion = "0.0.0"\n')
    (root / "hylyre" / "data.csv").write_bytes(b"a,b\r\n1,2\r\n")
    with pytest.raises(RuntimeError, match=r"CRLF.*hylyre/data\.csv"):
        bw.stage_source_tree(root, tmp_path / "src")


def test_stage_source_tree_normalizes_whitelisted_crlf(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "hylyre").mkdir(parents=True)
    (root / "pyproject.toml").write_bytes(b'[project]\r\nversion = "0.0.0"\r\n')
    (root / "hylyre" / "__init__.py").write_bytes(b"x = 1\r\n")
    files = bw.stage_source_tree(root, tmp_path / "src")
    assert (tmp_path / "src" / "hylyre" / "__init__.py").read_bytes() == b"x = 1\n"
    entry = next(f for f in files if f["path"] == "hylyre/__init__.py")
    assert entry["sha256"] == hashlib.sha256(b"x = 1\n").hexdigest()


def test_source_files_are_lf_normalized(release_src: Path) -> None:
    for p in (release_src / "src").rglob("*"):
        if p.is_file():
            assert b"\r\n" not in p.read_bytes(), f"CRLF in staged file: {p}"
    assert b"\r\n" not in (release_src / "downstream-harness-requests.md").read_bytes()


def test_source_verify_clean_release_ok(release_src: Path) -> None:
    assert _verify(release_src) == 0


def test_source_verify_detects_tampered_file(release_copy: Path) -> None:
    target = release_copy / "src" / "hylyre" / "__init__.py"
    target.write_bytes(target.read_bytes() + b"# tampered\n")
    assert _verify(release_copy) == 2


def test_source_verify_detects_undeclared_files(release_copy: Path) -> None:
    egg = release_copy / "src" / "hylyre.egg-info"
    egg.mkdir()
    (egg / "PKG-INFO").write_bytes(b"in-tree build pollution")
    assert _verify(release_copy) == 2


def test_source_verify_missing_declared_file(release_copy: Path) -> None:
    (release_copy / "src" / "hylyre" / "__main__.py").unlink()
    assert _verify(release_copy) == 3


def test_source_verify_version_mismatch(release_copy: Path) -> None:
    mf_path = release_copy / "release.manifest.json"
    manifest = json.loads(mf_path.read_text(encoding="utf-8"))
    manifest["hylyre_version"] = "0.0.0"
    _write_manifest(mf_path, manifest)
    assert _verify(release_copy) == 2


def test_source_verify_downstream_layout(release_copy: Path) -> None:
    """src/ + manifest only; vendor-root extras untracked; handoff doc absent."""
    (release_copy / "downstream-harness-requests.md").unlink()
    (release_copy / "README.md").write_bytes(b"downstream vendor readme\n")
    (release_copy / "hylyre-0.0.0-py3-none-any.whl").write_bytes(b"stale wheel")
    assert _verify(release_copy) == 0

    # manifest with integration_docs stripped by the downstream pipeline
    mf_path = release_copy / "release.manifest.json"
    manifest = json.loads(mf_path.read_text(encoding="utf-8"))
    manifest.pop("integration_docs", None)
    _write_manifest(mf_path, manifest)
    assert _verify(release_copy) == 0


def test_source_verify_integration_doc_present_must_match(release_copy: Path) -> None:
    (release_copy / "downstream-harness-requests.md").write_bytes(b"corrupted\n")
    assert _verify(release_copy) == 2


def test_wheel_schema1_verify_unaffected(tmp_path: Path) -> None:
    w = tmp_path / "hylyre-0.0.0-py3-none-any.whl"
    w.write_bytes(b"x")
    mf = {
        "schema": 1,
        "hylyre_version": "0.0.0",
        "wheel": {
            "filename": w.name,
            "sha256": bw.compute_sha256(w),
            "size_bytes": 1,
        },
    }
    (tmp_path / "release.manifest.json").write_text(json.dumps(mf), encoding="utf-8")
    assert _verify(tmp_path) == 0


@pytest.mark.slow
def test_source_tree_pip_installable_with_package_data(
    release_src: Path, tmp_path: Path
) -> None:
    """PEP 517 install from a copy of src/ (copy avoids in-tree build pollution)."""
    src_copy = tmp_path / "src"
    shutil.copytree(release_src / "src", src_copy)
    target = tmp_path / "site"
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(target),
            str(src_copy),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert (target / "hylyre" / "contracts" / "report-sections.yaml").is_file()
    assert (target / "hylyre" / "contracts" / "output-schema.json").is_file()
    assert (target / "hylyre" / "api" / "planned_step_keys.py").is_file()
