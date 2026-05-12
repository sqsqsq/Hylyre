"""L1: hylyre run entry smoke (no real device)."""

from __future__ import annotations

from pathlib import Path

from hylyre.cli.commands import run_cmd

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "e2e" / "fixtures" / "mock-test-plan.md"


def test_run_scenario_use_fakes_writes_artifacts(tmp_path: Path) -> None:
    report = tmp_path / "r.md"
    trace = tmp_path / "t.json"
    run_cmd.run_scenario(
        plan=FIXTURE,
        feature="cli-entry",
        report_out=report,
        trace_out=trace,
        use_fakes=True,
    )
    assert report.is_file()
    assert trace.is_file()
    assert "测试概览" in report.read_text(encoding="utf-8")
