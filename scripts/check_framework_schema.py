#!/usr/bin/env python3
"""Soft-compat: compare local ``output-schema.json`` vs consumer ``trace.schema.json``.

On drift: stderr warning + optional append to ``docs/progress.md`` (requires Hylyre import:
``pip install -e .`` from repo root, as in CI). Exit code 0 always.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

TRACE_URL = (
    "https://raw.githubusercontent.com/sqsqsq/SimulatedWalletForHmos/main/"
    "framework/harness/trace/trace.schema.json"
)


def _compare(root: Path) -> tuple[list[str], bool]:
    local_path = root / "hylyre" / "contracts" / "output-schema.json"
    if not local_path.is_file():
        print("compat: missing hylyre/contracts/output-schema.json", file=sys.stderr)
        return [], False
    local = json.loads(local_path.read_text(encoding="utf-8"))
    local_props = set((local.get("properties") or {}).keys())
    try:
        with urllib.request.urlopen(TRACE_URL, timeout=45) as resp:
            remote = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"compat: could not fetch remote trace schema: {e}", file=sys.stderr)
        return [], False
    remote_props = set((remote.get("properties") or {}).keys())
    required_remote = {"phase", "outcome", "schema_version"}.intersection(remote_props)
    missing = sorted(required_remote - local_props)
    return missing, True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-append-progress",
        action="store_true",
        help="Only print warnings; do not write docs/progress.md",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    missing, compared = _compare(root)
    if not compared:
        return
    if not missing:
        print("compat: core trace keys aligned (soft check).")
        return
    print(
        "compat: local output-schema.json lacks keys present on consumer trace "
        f"schema: {missing}.",
        file=sys.stderr,
    )
    if args.no_append_progress:
        print("compat: skipping progress append (--no-append-progress).", file=sys.stderr)
        return
    try:
        from hylyre.progress.store import append_compat_framework_drift_note
    except ImportError:
        print(
            "compat: cannot import hylyre (install with: pip install -e .); "
            "progress.md not updated.",
            file=sys.stderr,
        )
        return
    did = append_compat_framework_drift_note(missing, start=root)
    if did:
        print(
            f"compat: appended drift note to docs/progress.md (missing={missing}).",
            file=sys.stderr,
        )
    else:
        print(
            "compat: drift note skipped (duplicate signature in progress tail).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
