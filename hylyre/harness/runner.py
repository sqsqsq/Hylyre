"""Report/trace verification harness (P4)."""

from __future__ import annotations

from pathlib import Path


def verify_report(report: Path | str, trace: Path | str, plan: Path | str) -> bool:
    """Verify artifacts against Hylyre contracts. P0: stub returns False."""
    _ = (report, trace, plan)
    raise NotImplementedError("L5 verify_report is implemented in P4")
