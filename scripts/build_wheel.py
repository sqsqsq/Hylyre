#!/usr/bin/env python3
"""Build downstream framework vendor releases for hylyre.

Two coexisting modes:

- default: single ``py3-none-any`` wheel + ``release.manifest.json`` (schema 1);
- ``--source``: plain-source tree under ``src/`` + manifest schema 2, for
  downstream repos that forbid committing binary archives (``.whl``/``.tar.gz``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


SOURCE_ROOT_NAME = "src"
SOURCE_EXCLUDED_DIR_NAMES = {"__pycache__", "build", "tests"}
SOURCE_EXCLUDED_DIR_SUFFIXES = (".egg-info",)
SOURCE_EXCLUDED_FILE_SUFFIXES = (".pyc",)
# Everything shipped in the plain-source release is text; unknown suffixes are
# copied byte-for-byte so a future binary asset cannot be corrupted silently.
TEXT_FILE_SUFFIXES = {
    ".py", ".pyi", ".json", ".yaml", ".yml", ".md", ".toml", ".txt", ".cfg", ".ini",
}


def normalize_to_lf(data: bytes) -> bytes:
    """CRLF -> LF; release files and their sha256 use LF bytes (see R4/EOL note)."""
    return data.replace(b"\r\n", b"\n")


def iter_package_source_files(root: Path) -> list[tuple[Path, str]]:
    """(abs_path, posix_rel_path) for the plain-source release, path-byte-sorted.

    ``README.md`` ships alongside ``pyproject.toml`` because the latter declares
    ``readme = "README.md"``; without it PEP 517 metadata preparation fails.
    """
    entries: list[tuple[Path, str]] = []
    for name in ("pyproject.toml", "README.md"):
        p = root / name
        if p.is_file():
            entries.append((p, name))
    for p in (root / "hylyre").rglob("*"):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(root).parts
        if any(
            part in SOURCE_EXCLUDED_DIR_NAMES or part.endswith(SOURCE_EXCLUDED_DIR_SUFFIXES)
            for part in rel_parts[:-1]
        ):
            continue
        if p.name.endswith(SOURCE_EXCLUDED_FILE_SUFFIXES):
            continue
        entries.append((p, "/".join(rel_parts)))
    entries.sort(key=lambda e: e[1].encode("utf-8"))
    return entries


def stage_source_tree(root: Path, src_dir: Path) -> list[dict[str, object]]:
    """Copy package sources into ``src_dir`` (LF-normalized) and hash the written bytes.

    Guard: no staged file may contain CRLF. A downstream LF-normalizing git
    checkout would rewrite such a file and break its manifest sha — only there.
    A file with a suffix outside TEXT_FILE_SUFFIXES trips this at build time;
    extend the whitelist (text) or the release policy (binary) deliberately.
    """
    files: list[dict[str, object]] = []
    crlf_offenders: list[str] = []
    for abs_path, rel in iter_package_source_files(root):
        data = abs_path.read_bytes()
        if Path(rel).suffix.lower() in TEXT_FILE_SUFFIXES:
            data = normalize_to_lf(data)
        if b"\r\n" in data:
            crlf_offenders.append(rel)
        dst = src_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        files.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
        )
    if crlf_offenders:
        raise RuntimeError(
            "staged files contain CRLF (suffix not in TEXT_FILE_SUFFIXES? "
            "extend the whitelist or handle the file explicitly): "
            + ", ".join(crlf_offenders)
        )
    return files


def compute_tree_sha256(files: list[dict[str, object]]) -> str:
    """sha256 over concatenated ``"<path>\\n<sha256>\\n"``, files sorted by path bytes."""
    ordered = sorted(files, key=lambda f: str(f["path"]).encode("utf-8"))
    joined = "".join(f"{f['path']}\n{f['sha256']}\n" for f in ordered)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def build_source_manifest(
    files: list[dict[str, object]],
    hylyre_version: str,
    generator_python: str,
    generator_pip: str,
    platform_desc: str,
    *,
    integration_docs: list[dict[str, object]] | None = None,
) -> dict:
    ordered = sorted(files, key=lambda f: str(f["path"]).encode("utf-8"))
    manifest: dict[str, object] = {
        "schema": 2,
        "hylyre_version": hylyre_version,
        "source": {
            "root": SOURCE_ROOT_NAME,
            "file_count": len(ordered),
            "total_bytes": sum(int(f["size_bytes"]) for f in ordered),  # type: ignore[arg-type]
            "tree_sha256": compute_tree_sha256(ordered),
            "files": ordered,
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": {
            "python": generator_python,
            "pip": generator_pip,
            "platform": platform_desc,
        },
        "note": (
            'Plain-source release. Install with: pip install <src-dir> "hylyre[device,mcp]"; '
            "pip will fetch transitive deps (hypium/fastmcp/etc.) from PyPI. "
            "All text files are LF-normalized; tree_sha256 = sha256 over the concatenation "
            'of "<path>\\n<sha256>\\n" for all files under source.root sorted by POSIX '
            "relative path byte order. "
            "Framework harness integration (cold-restart, page save, personal-setup): see "
            "downstream-harness-requests.md in this directory."
        ),
    }
    if integration_docs:
        manifest["integration_docs"] = integration_docs
    return manifest


def get_pip_version() -> str:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        return (r.stdout or r.stderr or "").strip() or "(unknown)"
    except (OSError, subprocess.CalledProcessError):
        return "(unknown)"


def find_hylyre_wheel(out_dir: Path) -> Path:
    wheels = sorted(out_dir.glob("hylyre-*-py3-none-any.whl"))
    if len(wheels) != 1:
        names = [p.name for p in sorted(out_dir.glob("*.whl"))]
        raise RuntimeError(
            "expected exactly one hylyre-*-py3-none-any.whl in "
            f"{out_dir}, got {len(wheels)}; wheels present: {names}"
        )
    return wheels[0]


def read_version_from_pyproject(root: Path) -> str:
    path = root / "pyproject.toml"
    if sys.version_info >= (3, 11):
        import tomllib

        with path.open("rb") as f:
            data = tomllib.load(f)
        ver = data.get("project", {}).get("version")
        if not ver or not isinstance(ver, str):
            raise RuntimeError("could not read project.version from pyproject.toml")
        return ver
    import re

    text = path.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        raise RuntimeError("could not parse version from pyproject.toml (regex)")
    return m.group(1)


def build_manifest(
    wheel: Path,
    hylyre_version: str,
    generator_python: str,
    generator_pip: str,
    platform_desc: str,
    *,
    integration_docs: list[dict[str, object]] | None = None,
) -> dict:
    st = wheel.stat()
    manifest: dict[str, object] = {
        "schema": 1,
        "hylyre_version": hylyre_version,
        "wheel": {
            "filename": wheel.name,
            "sha256": compute_sha256(wheel),
            "size_bytes": st.st_size,
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": {
            "python": generator_python,
            "pip": generator_pip,
            "platform": platform_desc,
        },
        "note": (
            "Pure-Python wheel (py3-none-any). Install with: pip install <wheel-path>; "
            "pip will fetch transitive deps (hypium/fastmcp/etc.) from PyPI. "
            "Framework harness integration (cold-restart, page save, personal-setup): see "
            "downstream-harness-requests.md in this directory."
        ),
    }
    if integration_docs:
        manifest["integration_docs"] = integration_docs
    return manifest


def stage_integration_docs(
    root: Path, out_dir: Path, *, normalize_lf: bool = False
) -> list[dict[str, object]]:
    """Copy handoff docs beside the release; listed in release.manifest.json.

    Source mode passes ``normalize_lf=True`` so the doc's sha256 stays valid after
    a downstream LF-normalizing git checkout (same EOL policy as ``src/``).
    """
    staged: list[dict[str, object]] = []
    for rel_src, dst_name, purpose in (
        (
            "docs/downstream-harness-requests.md",
            "downstream-harness-requests.md",
            "Framework harness integration (cold-restart, page save, personal-setup)",
        ),
    ):
        src = root / rel_src
        if not src.is_file():
            continue
        dst = out_dir / dst_name
        if normalize_lf:
            dst.write_bytes(normalize_to_lf(src.read_bytes()))
        else:
            shutil.copy2(src, dst)
        st = dst.stat()
        staged.append(
            {
                "filename": dst_name,
                "sha256": compute_sha256(dst),
                "size_bytes": st.st_size,
                "purpose": purpose,
            }
        )
    return staged


def format_cp_hints(
    wheel: Path, manifest_path: Path, integration_docs: list[dict[str, object]] | None = None
) -> str:
    """Human-oriented snippets to copy wheel + manifest into a framework vendor tree."""
    root = repo_root_from_script()
    build_script = (root / "scripts" / "build_wheel.py").resolve()
    verify_cmd = f'{sys.executable} "{build_script}" --verify $dst'
    w_abs = wheel.resolve()
    m_abs = manifest_path.resolve()
    lines = [
        "---",
        "Next: copy into your framework vendor/ (edit $dst), then verify:",
        "# PowerShell example:",
        r'$dst = "<YourFramework>\framework\profiles\hmos-app\vendor\hylyre"',
        "New-Item -ItemType Directory -Force -Path $dst | Out-Null",
        f'Copy-Item -Force "{w_abs}" $dst',
        f'Copy-Item -Force "{m_abs}" $dst',
    ]
    if integration_docs:
        for doc in integration_docs:
            name = doc.get("filename")
            if isinstance(name, str):
                doc_abs = (manifest_path.parent / name).resolve()
                lines.append(f'Copy-Item -Force "{doc_abs}" $dst')
        lines.append(
            "# Read downstream-harness-requests.md for harness integration "
            "(cold-restart, page save, personal-setup / F3)."
        )
    lines.extend(
        [
            verify_cmd,
            "# Details: docs/framework-vendor-bundle.md",
        ]
    )
    return "\n".join(lines)


def format_source_cp_hints(
    src_dir: Path, manifest_path: Path, integration_docs: list[dict[str, object]] | None = None
) -> str:
    """Human-oriented snippets to copy the source tree into a framework vendor tree."""
    root = repo_root_from_script()
    build_script = (root / "scripts" / "build_wheel.py").resolve()
    s_abs = src_dir.resolve()
    m_abs = manifest_path.resolve()
    lines = [
        "---",
        "Next: copy into your framework vendor/ (edit $dst), then verify:",
        "# PowerShell example:",
        r'$dst = "<YourFramework>\framework\profiles\hmos-app\vendor\hylyre"',
        "New-Item -ItemType Directory -Force -Path $dst | Out-Null",
        f'Remove-Item -Recurse -Force "$dst\\{SOURCE_ROOT_NAME}" -ErrorAction Ignore',
        f'Copy-Item -Recurse -Force "{s_abs}" "$dst\\{SOURCE_ROOT_NAME}"',
        f'Copy-Item -Force "{m_abs}" $dst',
    ]
    if integration_docs:
        for doc in integration_docs:
            name = doc.get("filename")
            if isinstance(name, str):
                doc_abs = (manifest_path.parent / name).resolve()
                lines.append(f'Copy-Item -Force "{doc_abs}" $dst')
    lines.extend(
        [
            f'{sys.executable} "{build_script}" --verify $dst',
            "# Details: docs/framework-vendor-bundle.md",
        ]
    )
    return "\n".join(lines)


def cmd_build_source(args: argparse.Namespace) -> int:
    root = repo_root_from_script()
    out_dir = Path(args.out_dir).resolve()
    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)
    src_dir = out_dir / SOURCE_ROOT_NAME
    if src_dir.exists():
        # Stale files from a previous run would fail the undeclared-file check.
        shutil.rmtree(src_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    import platform as platmod

    version = read_version_from_pyproject(root)
    try:
        files = stage_source_tree(root, src_dir)
    except RuntimeError as e:
        print(f"build: {e}", file=sys.stderr)
        return 1
    staged_version = read_version_from_pyproject(src_dir)
    if staged_version != version:
        print(
            f"build: staged pyproject version {staged_version!r} != repo version {version!r}",
            file=sys.stderr,
        )
        return 1
    integration_docs = stage_integration_docs(root, out_dir, normalize_lf=True)
    manifest = build_source_manifest(
        files,
        version,
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        get_pip_version(),
        platmod.platform(),
        integration_docs=integration_docs or None,
    )
    manifest_path = out_dir / "release.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(str(src_dir.resolve()))
    print(str(manifest_path.resolve()))
    for doc in integration_docs:
        name = doc.get("filename")
        if isinstance(name, str):
            print(str((out_dir / name).resolve()))
    print(format_source_cp_hints(src_dir, manifest_path, integration_docs or None))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    root = repo_root_from_script()
    out_dir = Path(args.out_dir).resolve()
    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(out_dir)]
    r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        if r.stdout:
            print(r.stdout, end="", file=sys.stderr)
        if r.stderr:
            print(r.stderr, end="", file=sys.stderr)
        return 1

    try:
        wheel = find_hylyre_wheel(out_dir)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    import platform as platmod

    version = read_version_from_pyproject(root)
    integration_docs = stage_integration_docs(root, out_dir)
    manifest = build_manifest(
        wheel,
        version,
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        get_pip_version(),
        platmod.platform(),
        integration_docs=integration_docs or None,
    )
    manifest_path = out_dir / "release.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(str(wheel.resolve()))
    print(str(manifest_path.resolve()))
    for doc in integration_docs:
        name = doc.get("filename")
        if isinstance(name, str):
            print(str((out_dir / name).resolve()))
    print(format_cp_hints(wheel, manifest_path, integration_docs or None))
    return 0


def cmd_verify(directory: Path) -> int:
    d = directory.resolve()
    if not d.is_dir():
        print(f"verify: not a directory: {d}", file=sys.stderr)
        return 3

    mf_path = d / "release.manifest.json"
    if not mf_path.is_file():
        print(f"verify: missing {mf_path}", file=sys.stderr)
        return 3

    try:
        # utf-8-sig: tolerate a BOM added by Windows editors/tools downstream.
        manifest = json.loads(mf_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        print(f"verify: invalid JSON: {e}", file=sys.stderr)
        return 3

    if manifest.get("schema") == 2:
        return verify_source_release(d, manifest)

    wheel_info = manifest.get("wheel")
    if not isinstance(wheel_info, dict):
        print("verify: manifest missing wheel object", file=sys.stderr)
        return 3

    wheel_name = wheel_info.get("filename")
    expected = wheel_info.get("sha256")
    if not wheel_name or not expected:
        print("verify: manifest missing wheel.filename or wheel.sha256", file=sys.stderr)
        return 3

    wheel_path = d / str(wheel_name)
    if not wheel_path.is_file():
        print(f"verify: missing wheel file {wheel_path}", file=sys.stderr)
        return 3

    actual = compute_sha256(wheel_path)
    if actual != expected:
        print(
            "verify: sha256 mismatch\n"
            f"  manifest: {expected}\n"
            f"  actual:   {actual}",
            file=sys.stderr,
        )
        return 2

    return 0


def _is_safe_rel_path(path_str: str) -> bool:
    if not path_str or path_str.startswith("/") or "\\" in path_str or ":" in path_str:
        return False
    return ".." not in path_str.split("/")


def verify_source_release(d: Path, manifest: dict) -> int:
    """Verify a schema-2 (plain-source tree) release directory.

    Strict inside ``source.root`` (per-file sha/size, aggregates, no undeclared
    files); everything outside it belongs to the downstream repo and is ignored.
    ``integration_docs``: a present file must match its sha; a missing file — or
    the whole field being absent — passes (source-repo vs downstream layouts).
    """
    src_info = manifest.get("source")
    if not isinstance(src_info, dict):
        print("verify: manifest missing source object", file=sys.stderr)
        return 3

    root_name = src_info.get("root", SOURCE_ROOT_NAME)
    if not isinstance(root_name, str) or not _is_safe_rel_path(root_name):
        print(f"verify: invalid source.root {root_name!r}", file=sys.stderr)
        return 3
    src_root = d / root_name
    if not src_root.is_dir():
        print(f"verify: missing source root {src_root}", file=sys.stderr)
        return 3

    entries = src_info.get("files")
    if not isinstance(entries, list) or not entries:
        print("verify: manifest missing source.files", file=sys.stderr)
        return 3
    declared: dict[str, dict] = {}
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("sha256"), str)
        ):
            print("verify: malformed source.files entry", file=sys.stderr)
            return 3
        path_str = entry["path"]
        if not _is_safe_rel_path(path_str):
            print(f"verify: unsafe source.files path {path_str!r}", file=sys.stderr)
            return 3
        if path_str in declared:
            print(f"verify: duplicate source.files path {path_str!r}", file=sys.stderr)
            return 3
        declared[path_str] = entry

    rc = 0
    actual_files: list[dict[str, object]] = []
    for path_str, entry in declared.items():
        f = src_root / path_str
        if not f.is_file():
            print(f"verify: missing source file {f}", file=sys.stderr)
            return 3
        digest = compute_sha256(f)
        size = f.stat().st_size
        expected_size = entry.get("size_bytes")
        if digest != entry["sha256"] or (
            isinstance(expected_size, int) and size != expected_size
        ):
            print(
                f"verify: mismatch for {path_str}\n"
                f"  manifest: sha256={entry['sha256']} size={expected_size}\n"
                f"  actual:   sha256={digest} size={size}",
                file=sys.stderr,
            )
            rc = 2

    undeclared: list[str] = []
    for p in src_root.rglob("*"):
        if not p.is_file():
            continue
        rel = "/".join(p.relative_to(src_root).parts)
        actual_files.append(
            {"path": rel, "sha256": compute_sha256(p), "size_bytes": p.stat().st_size}
        )
        if rel not in declared:
            undeclared.append(rel)
    if undeclared:
        print(
            f"verify: undeclared files under {root_name}/ "
            "(stale in-tree build artifacts?):",
            file=sys.stderr,
        )
        for rel in sorted(undeclared):
            print(f"  {rel}", file=sys.stderr)
        rc = 2

    checks = (
        ("tree_sha256", src_info.get("tree_sha256"), compute_tree_sha256(actual_files)),
        ("file_count", src_info.get("file_count"), len(actual_files)),
        (
            "total_bytes",
            src_info.get("total_bytes"),
            sum(int(f["size_bytes"]) for f in actual_files),  # type: ignore[arg-type]
        ),
    )
    for label, expected, actual in checks:
        if expected != actual:
            print(
                f"verify: source.{label} mismatch\n"
                f"  manifest: {expected}\n"
                f"  actual:   {actual}",
                file=sys.stderr,
            )
            rc = 2

    try:
        staged_version = read_version_from_pyproject(src_root)
    except (OSError, RuntimeError) as e:
        print(f"verify: cannot read version from {src_root / 'pyproject.toml'}: {e}", file=sys.stderr)
        return 3
    if staged_version != manifest.get("hylyre_version"):
        print(
            "verify: hylyre_version mismatch\n"
            f"  manifest:  {manifest.get('hylyre_version')}\n"
            f"  pyproject: {staged_version}",
            file=sys.stderr,
        )
        rc = 2

    docs = manifest.get("integration_docs")
    if isinstance(docs, list):
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            name = doc.get("filename")
            expected_sha = doc.get("sha256")
            if not isinstance(name, str) or not isinstance(expected_sha, str):
                continue
            if not _is_safe_rel_path(name):
                print(f"verify: unsafe integration_docs filename {name!r}", file=sys.stderr)
                return 3
            f = d / name
            if not f.is_file():
                continue  # downstream layouts may legitimately omit handoff docs
            digest = compute_sha256(f)
            if digest != expected_sha:
                print(
                    f"verify: integration doc sha256 mismatch: {name}\n"
                    f"  manifest: {expected_sha}\n"
                    f"  actual:   {digest}",
                    file=sys.stderr,
                )
                rc = 2

    return rc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build hylyre vendor release (wheel or plain-source tree) for framework integration."
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="output directory (default: dist/release; dist/release-src with --source)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove out-dir before building",
    )
    parser.add_argument(
        "--source",
        action="store_true",
        help="build plain-source tree release (manifest schema 2) instead of a wheel",
    )
    parser.add_argument(
        "--verify",
        metavar="DIR",
        help=(
            "verify release.manifest.json matches files on disk "
            "(schema auto-detected: 1 = wheel, 2 = source tree)"
        ),
    )
    args = parser.parse_args()

    if args.verify:
        return cmd_verify(Path(args.verify))

    if args.out_dir is None:
        args.out_dir = "dist/release-src" if args.source else "dist/release"

    if args.source:
        return cmd_build_source(args)
    return cmd_build(args)


if __name__ == "__main__":
    raise SystemExit(main())
