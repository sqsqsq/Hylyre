#!/usr/bin/env python3
"""Build a single hylyre ``py3-none-any`` wheel for downstream framework vendor."""

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
            "Framework harness integration (#3 cold-restart, #6 page save): see "
            "downstream-harness-requests.md in this directory."
        ),
    }
    if integration_docs:
        manifest["integration_docs"] = integration_docs
    return manifest


def stage_integration_docs(root: Path, out_dir: Path) -> list[dict[str, object]]:
    """Copy handoff docs beside wheel; listed in release.manifest.json for downstream."""
    staged: list[dict[str, object]] = []
    for rel_src, dst_name, purpose in (
        (
            "docs/downstream-harness-requests.md",
            "downstream-harness-requests.md",
            "Framework harness integration (#3 cold-restart, #6 app page save)",
        ),
    ):
        src = root / rel_src
        if not src.is_file():
            continue
        dst = out_dir / dst_name
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
            "# Read downstream-harness-requests.md for harness changes (#3/#6)."
        )
    lines.extend(
        [
            verify_cmd,
            "# Details: docs/framework-vendor-bundle.md",
        ]
    )
    return "\n".join(lines)


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
        manifest = json.loads(mf_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"verify: invalid JSON: {e}", file=sys.stderr)
        return 3

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build hylyre vendor wheel for framework integration."
    )
    parser.add_argument(
        "--out-dir",
        default="dist/release",
        help="output directory (default: dist/release)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove out-dir before building",
    )
    parser.add_argument(
        "--verify",
        metavar="DIR",
        help="verify release.manifest.json matches wheel on disk",
    )
    args = parser.parse_args()

    if args.verify:
        return cmd_verify(Path(args.verify))

    return cmd_build(args)


if __name__ == "__main__":
    raise SystemExit(main())
