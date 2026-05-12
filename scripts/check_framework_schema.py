#!/usr/bin/env python3
"""Soft-compat check: compare local trace-related schema hints vs consumer trace.schema.json.

Exits 0 always; prints warnings on missing keys or fetch errors. Intended for warn-only CI.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

TRACE_URL = (
    "https://raw.githubusercontent.com/sqsqsq/SimulatedWalletForHmos/main/"
    "framework/harness/trace/trace.schema.json"
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    local_path = root / "hylyre" / "contracts" / "output-schema.json"
    if not local_path.is_file():
        print("compat: missing hylyre/contracts/output-schema.json", file=sys.stderr)
        return
    local = json.loads(local_path.read_text(encoding="utf-8"))
    local_props = set((local.get("properties") or {}).keys())
    try:
        with urllib.request.urlopen(TRACE_URL, timeout=45) as resp:
            remote = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"compat: could not fetch remote trace schema: {e}", file=sys.stderr)
        return
    remote_props = set((remote.get("properties") or {}).keys())
    required_remote = {"phase", "outcome", "schema_version"}.intersection(remote_props)
    missing = sorted(required_remote - local_props)
    if missing:
        print(
            "compat: local output-schema.json lacks keys present on consumer trace "
            f"schema: {missing}. See docs/progress.md → framework schema drift.",
            file=sys.stderr,
        )
    else:
        print("compat: core trace keys aligned (soft check).")


if __name__ == "__main__":
    main()
