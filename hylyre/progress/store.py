"""Locate Hylyre repo ``docs/progress.md`` and append timestamped notes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def find_hylyre_repo_root(start: Path | None = None) -> Path:
    """Walk upward for a ``pyproject.toml`` that declares the hylyre package."""
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        manifest = p / "pyproject.toml"
        if not manifest.is_file():
            continue
        try:
            text = manifest.read_text(encoding="utf-8")
        except OSError:
            continue
        if 'name = "hylyre"' in text or 'name="hylyre"' in text:
            return p
    return cur


def default_progress_path(start: Path | None = None) -> Path:
    return find_hylyre_repo_root(start) / "docs" / "progress.md"


def read_progress_text(*, path: Path | None = None) -> str:
    p = path or default_progress_path()
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


def append_progress_section(
    message: str,
    *,
    path: Path | None = None,
    title: str | None = None,
) -> Path:
    """Append a dated markdown section. Creates parent dirs; creates file if missing."""
    p = path or default_progress_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    head = title or f"## {stamp} · hylyre progress"
    block = f"\n\n{head}\n\n{message.rstrip()}\n"
    prev = p.read_text(encoding="utf-8") if p.is_file() else ""
    p.write_text(prev.rstrip() + block, encoding="utf-8")
    return p
